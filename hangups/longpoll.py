"""Parser for long-polling responses from the talkgadget API."""

import pprint
import logging
import re
from collections import namedtuple
import datetime

from hangups import javascript


logger = logging.getLogger(__name__)
PP = pprint.PrettyPrinter(indent=4)
LEN_REGEX = re.compile(r'([0-9]+)\n', re.MULTILINE)


User = namedtuple('User', ['id_', 'full_name', 'first_name', 'is_self'])


UserID = namedtuple('UserID', ['chat_id', 'gaia_id'])


class PushDataParser(object):
    """Parse data from the long-polling endpoint."""

    def __init__(self):
        self._buf = b'' # utf-16 encoded text

    def get_submissions(self, new_data):
        """Yield submissions generated from received data.

        Responses from the push endpoint consist of a sequence of submissions.
        Each submission is prefixed with its length followed by a newline.

        The length is actually the length of the string as reported by
        JavaScript. JavaScript's string length function returns the number of
        code units in the string, represented in UTF-16. We can emulate this by
        encoding everything in UTF-16 and multipling the reported length by 2.

        Note that when encoding a string in UTF-16, Python will prepend a
        byte-order character, so we need to remove the first two bytes.
        """
        # append any new data to the buffer
        self._buf += new_data.encode('utf-16')[2:]

        while True:
            lengths = LEN_REGEX.findall(self._buf.decode('utf-16'))
            if len(lengths) == 0:
                break
            else:
                # both lengths are in number of bytes in UTF-16 encoding
                # the length of the submission
                length = int(lengths[0]) * 2
                # the length of the submission length and newline
                length_length = len((lengths[0] + '\n').encode('utf-16')[2:])
                if len(self._buf) - length_length < length:
                    break
                submission = self._buf[length_length:length_length + length]
                yield submission.decode('utf-16')
                self._buf = self._buf[length_length + length:]

    def get_messages(self, new_data):
        """Yield tuples containing message type and message from received data.

        One submission may contain multiple messages.
        """
        for submission in self.get_submissions(new_data):
            # For each submission payload, yield its messages
            for payload in _get_submission_payloads(submission):
                if payload is not None:
                    yield from _parse_payload(payload)


    def get_events(self, new_data):
        """Yield events generated from received data."""
        for msg_type, msg in self.get_messages(new_data):
            logger.debug('Received message of type {}:\n{}'
                         .format(msg_type, PP.pformat(msg)))
            if msg_type in MESSAGE_PARSERS:
                event_tuple = MESSAGE_PARSERS[msg_type](msg)
                # Message parsers may fail by returning None, so don't yield
                # their result in this case.
                if event_tuple:
                    yield event_tuple


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


def from_timestamp(timestamp):
    """Convert a microsecond timestamp to a UTC datetime instance."""
    return datetime.datetime.fromtimestamp(timestamp / 1000000,
                                           datetime.timezone.utc)


def _parse_chat_message(message):
    """Parse chat message message."""
    # The message content is a list of message segments, which have a
    # type. For now, let's ignore the types and just use the textual
    # representation, appending all the segments into one string.
    message_text = ''
    try:
        message_content = message[0][6][2][0]
    except (TypeError, IndexError):
        # Sometimes there aren't actually chat messages (conversation name
        # changes, and video call initiations).
        # TODO: handle these cases
        logger.warning('Failed to parse chat message')
        return None
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
            logger.warning('Failed to parse image message: {}'.format(e))
            return None
    return (
        'on_message',
        message[0][0][0],
        UserID(chat_id=message[0][1][0], gaia_id=message[0][1][0]),
        from_timestamp(message[0][2]),
        message_text
    )


def _parse_conversation_status(message):
    """Parse conversation status message."""
    # TODO: there's a lot more info here
    return (
        'on_conversation',
        message[0][0],
        # participant list items sometimes can be length 2 or 3
        # ids, name, ?
        {tuple(item[0]): item[1] for item in message[13]}
    )


def _parse_focus_status(message):
    """Parse focus status message."""
    FOCUS_STATUSES = {
        1: 'focused',
        2: 'unfocused',
    }
    try:
        focus_status = FOCUS_STATUSES[message[3]]
    except KeyError:
        # TODO: should probably just discard the event in this case
        focus_status = None
        logger.warning('Unknown focus status: {}'.format(message[3]))

    FOCUS_DEVICES = {
        20: 'desktop',
        300: 'mobile',
        None: 'unspecified',
    }
    try:
        # sometimes the device is unspecified so the message is shorter
        focus_device = FOCUS_DEVICES[message[4] if len(message) > 4 else None]
    except KeyError:
        focus_device = None
        logger.warning('Unknown focus device: {}'.format(message[4]))

    return (
        'on_focus',
        message[0][0],
        UserID(chat_id=message[1][0], gaia_id=message[1][1]),
        from_timestamp(message[2]),
        focus_status,
        focus_device,
    )


def _parse_typing_status(message):
    """Parse typing status message."""
    # Note that the same status may be sent multiple times
    # consecutively, and that when a message is sent the typing status
    # will not change to stopped.
    TYPING_STATUSES = {
        1: 'typing', # the user is typing
        2: 'paused', # the user stopped typing with inputted text
        3: 'stopped', # the user stopped typing with no inputted text
    }
    try:
        typing_status = TYPING_STATUSES[message[3]]
    except KeyError:
        typing_status = None # TODO should probably discard event in this case
        logger.warning('Unknown typing status: {}'.format(message[3]))

    return (
        'on_typing',
        message[0][0],
        UserID(chat_id=message[1][0], gaia_id=message[1][1]),
        from_timestamp(message[2]),
        typing_status,
    )

# message types have been observed to range from 1 to 14
MESSAGE_PARSERS = {
    1: _parse_chat_message,
    2: _parse_focus_status,
    3: _parse_typing_status,
    11: _parse_conversation_status,
}
