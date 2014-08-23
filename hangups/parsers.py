"""Parser for long-polling responses from the talkgadget API."""

import logging
import re
from collections import namedtuple
import datetime

from hangups import javascript, exceptions


logger = logging.getLogger(__name__)
LEN_REGEX = re.compile(r'([0-9]+)\n', re.MULTILINE)


User = namedtuple('User', ['id_', 'full_name', 'first_name', 'is_self'])


UserID = namedtuple('UserID', ['chat_id', 'gaia_id'])


def _best_effort_decode(data_bytes):
    """Decode data_bytes into a string using UTF-8.

    If data_bytes cannot be decoded, pop the last byte until it can be or
    return an empty string.
    """
    for end in reversed(range(1, len(data_bytes) + 1)):
        try:
            return data_bytes[0:end].decode()
        except UnicodeDecodeError:
            pass
    return ''


class PushDataParser(object):
    """Parse data from the long-polling endpoint."""

    def __init__(self):
        # Buffer for bytes containing utf-8 text:
        self._buf = b''

    def get_submissions(self, new_data_bytes):
        """Yield submissions generated from received data.

        Responses from the push endpoint consist of a sequence of submissions.
        Each submission is prefixed with its length followed by a newline.

        The buffer may not be decodable as UTF-8 if there's a split multi-byte
        character at the end. To handle this, do a "best effort" decode of the
        buffer to decode as much of it as possible.

        The length is actually the length of the string as reported by
        JavaScript. JavaScript's string length function returns the number of
        code units in the string, represented in UTF-16. We can emulate this by
        encoding everything in UTF-16 and multipling the reported length by 2.

        Note that when encoding a string in UTF-16, Python will prepend a
        byte-order character, so we need to remove the first two bytes.
        """
        self._buf += new_data_bytes

        while True:

            buf_decoded = _best_effort_decode(self._buf)
            buf_utf16 = buf_decoded.encode('utf-16')[2:]

            lengths = LEN_REGEX.findall(buf_decoded)
            if len(lengths) == 0:
                break
            else:
                # Both lengths are in number of bytes in UTF-16 encoding.
                # The length of the submission:
                length = int(lengths[0]) * 2
                # The length of the submission length and newline:
                length_length = len((lengths[0] + '\n').encode('utf-16')[2:])
                if len(buf_utf16) - length_length < length:
                    break

                submission = buf_utf16[length_length:length_length + length]
                yield submission.decode('utf-16')
                # Drop the length and the submission itself from the beginning
                # of the buffer.
                drop_length = (len((lengths[0] + '\n').encode()) +
                               len(submission.decode('utf-16').encode()))
                self._buf = self._buf[drop_length:]

    def get_messages(self, new_data_bytes):
        """Yield (message_type, message) tuples from received data."""
        # One submission may contain multiple messages.
        for submission in self.get_submissions(new_data_bytes):
            # For each submission payload, yield its messages
            for payload in _get_submission_payloads(submission):
                if payload is not None:
                    yield from _parse_payload(payload)


def _get_submission_payloads(submission):
    """Yield a submission's payloads.

    Most submissions only contain one payload, but if the long-polling
    connection was closed while something happened, there can be multiple
    payloads.
    """
    for sub in javascript.loads(submission):

        # the submission number, increments with each payload
        # sub_num = sub[0]
        # the submission type
        sub_type = sub[1][0]

        if sub_type == 'c':

            # session ID, should be the same for every request
            # session_id = sub[1][1][0]
            # payload type
            payload_type = sub[1][1][1][0]

            if payload_type == 'bfo':
                # Payload is submessages in the list format. These are the
                # payloads we care about.
                yield javascript.loads(sub[1][1][1][1])
            elif payload_type == 'tm':
                # Payload is object format. I'm not sure what these are for,
                # but they don't seem very important.
                pass
            elif payload_type == 'wh':
                # Payload is null. These messages don't contain any information
                # other than the session_id, and appear to be just heartbeats.
                pass
            elif payload_type == 'otr':
                # Not sure what this is for, might be something to do with
                # XMPP.
                pass
            elif payload_type == 'ho:hin':
                # Sent when a video call starts/stops.
                pass
            else:
                logger.warning(
                    'Got submission with unknown payload type {}:\n{}'
                    .format(payload_type, sub)
                )
        elif sub_type == 'noop':
            # These contain no information and only seem to appear once as the
            # first message when a channel is opened.
            pass
        else:
            logger.warning('Got submission with unknown submission type: {}\n{}'
                           .format(sub_type, sub))


def _parse_payload(payload):
    """Parse the list payload format into messages."""
    # the payload begins with a constant header
    if payload[0] != 'cbu':
        raise ValueError('Invalid list payload header: {}'.format(payload[0]))

    # The first submessage is always present, so let's treat it like a header.
    # It doesn't have anything we need so ignore it.
    # first_submsg = payload[1][0][0]

    # The type of a submessage is determined by its position in the array
    yield from ((msg_type, msg) for msg_type, msg in
                enumerate(payload[1][0][1:]) if msg is not None)


def parse_message(message_type, message):
    """Parse any type of message.

    Returns message instance, or None if the message could not be parsed.
    """
    def parse_not_implemented_message(message_type, message):
        """Parser for known but not implemented messages."""
        raise exceptions.ParseNotImplementedError(
            'Unimplemented message type: {}'.format(message_type)
        )
    def parse_unknown_message(message_type, message):
        """Parser for unknown messages."""
        raise exceptions.ParseError(
            'Unknown message type: {}'.format(message_type)
        )

    # Message types have been observed to range from 1 to 14.
    # TODO: Implement the unimplemented message parsers.
    MESSAGE_PARSERS = {
        1: parse_chat_message,
        2: parse_focus_status_message,
        3: parse_typing_status_message,
        # read state change
        6: lambda msg: parse_not_implemented_message(6, msg),
        11: parse_conversation_status_message,
        # notification snooze / set mood
        12: lambda msg: parse_not_implemented_message(12, msg),
        # ??? (a user ID and some properties)
        14: lambda msg: parse_not_implemented_message(14, msg),
    }

    parsed_message = None

    try:
        parser = MESSAGE_PARSERS.get(
            message_type, lambda msg: parse_unknown_message(message_type, msg)
        )
        parsed_message = parser(message)
    except exceptions.ParseError as e:
        logger.warning('Failed to parse message: {}'.format(e))
    except exceptions.ParseNotImplementedError as e:
        logger.info('Failed to parse message: {}'.format(e))

    logger.debug('Parsed message: {}'.format(parsed_message))
    return parsed_message


##############################################################################
# Message parsing utils
##############################################################################


def from_timestamp(timestamp):
    """Convert a microsecond timestamp to a UTC datetime instance."""
    return datetime.datetime.fromtimestamp(timestamp / 1000000,
                                           datetime.timezone.utc)


##############################################################################
# Message types and parsers
##############################################################################


ChatMessage = namedtuple(
    'ChatMessage', ['conv_id', 'user_id', 'timestamp', 'text']
)


def parse_chat_message(message):
    """Return ChatMessage from parsing raw message.

    Raises ParseError if the message cannot be parsed.
    """
    # The message content is a list of message segments, which have a
    # type. For now, let's ignore the types and just use the textual
    # representation, appending all the segments into one string.
    message_text = ''

    # Find the message type:
    type_int = message[0][22]
    try:
        type_ = {
            # message[0][6] will contain message content.
            1: 'REGULAR_CHAT_MESSAGE',
            # message[0][8] will contain ???.
            4: 'UNKNOWN_4',
            # message[0][8] will contain ???.
            5: 'UNKNOWN_5',
            # message[0][9] will contain conversation rename.
            6: 'RENAME_CONVERSATION',
            # message[0][10] will contain hangout event.
            7: 'HANGOUT_EVENT',
            # message[0][13] will contain OTR modification.
            9: 'OTR_MODIFICATION',
        }[type_int]
    except KeyError:
        logger.debug(message)
        raise exceptions.ParseError('Unknown chat message type: {}'
                                    .format(type_int))

    if type_ != 'REGULAR_CHAT_MESSAGE':
        raise exceptions.ParseNotImplementedError(
            'Unimplemented chat message type: {}'.format(type_)
        )

    message_content = message[0][6][2][0]
    if len(message_content) > 0:
        for segment in message_content:
            # known types: 0: text, 1: linebreak, 2: link
            # Hangouts for Android (unlike the Chrome extension) doesn't set
            # the message text for linebreaks, so we have to handle that case
            # separately.
            if segment[0] == 1:
                message_text += '\n'
            else:
                message_text += segment[1]
    else:
        # Try to parse an image message. Image messages contain no message
        # segments, and thus have no automatic textual fallback.
        try:
            # set the message text to the image URL
            message_text = list(message[0][6][2][1][0][0][1].values())[0][0][3]
        except (TypeError, IndexError, ValueError) as e:
            raise exceptions.ParseError('Failed to parse image message: {}'
                                        .format(e))
    return ChatMessage(
        conv_id=message[0][0][0],
        user_id=UserID(chat_id=message[0][1][0], gaia_id=message[0][1][0]),
        timestamp=from_timestamp(message[0][2]),
        text=message_text,
    )


ConversationStatusMessage = namedtuple(
    'ConversationStatusMessage', ['conv_id', 'user_id_list']
)


def parse_conversation_status_message(message):
    """Return ConversationStatusMessage from parsing raw message.

    Raises ParseError if the message cannot be parsed.
    """
    # TODO: This is far from a complete parse.
    return ConversationStatusMessage(
        conv_id=message[0][0],
        user_id_list=[UserID(chat_id=item[0][0], gaia_id=item[0][1])
                      for item in message[13]],
    )


FocusStatusMessage = namedtuple(
    'FocusStatusMessage',
    ['conv_id', 'user_id', 'timestamp', 'status', 'device']
)


def parse_focus_status_message(message):
    """Return FocusStatusMessage from parsing raw message.

    Raises ParseError if the message cannot be parsed.
    """
    FOCUS_STATUSES = {
        1: 'focused',
        2: 'unfocused',
    }
    try:
        focus_status = FOCUS_STATUSES[message[3]]
    except KeyError:
        raise exceptions.ParseError('Unknown focus status: {}'
                                    .format(message[3]))

    FOCUS_DEVICES = {
        20: 'desktop',
        300: 'mobile',
        None: 'unspecified',
    }
    try:
        # sometimes the device is unspecified so the message is shorter
        focus_device = FOCUS_DEVICES[message[4] if len(message) > 4 else None]
    except KeyError:
        raise exceptions.ParseError('Unknown focus device: {}'
                                    .format(message[4]))

    return FocusStatusMessage(
        conv_id=message[0][0],
        user_id=UserID(chat_id=message[1][0], gaia_id=message[1][1]),
        timestamp=from_timestamp(message[2]),
        status=focus_status,
        device=focus_device,
    )


TypingStatusMessage = namedtuple(
    'TypingStatusMessage', ['conv_id', 'user_id', 'timestamp', 'status']
)


def parse_typing_status_message(message):
    """Return TypingStatusMessage from parsing raw message.

    The same status may be sent multiple times consecutively, and when a
    message is sent the typing status will not change to stopped.

    Raises ParseError if the message cannot be parsed.
    """
    TYPING_STATUSES = {
        1: 'typing', # the user is typing
        2: 'paused', # the user stopped typing with inputted text
        3: 'stopped', # the user stopped typing with no inputted text
    }
    try:
        typing_status = TYPING_STATUSES[message[3]]
    except KeyError:
        raise exceptions.ParseError('Unknown typing status: {}'
                                    .format(message[3]))
    return TypingStatusMessage(
        conv_id=message[0][0],
        user_id=UserID(chat_id=message[1][0], gaia_id=message[1][1]),
        timestamp=from_timestamp(message[2]),
        status=typing_status,
    )
