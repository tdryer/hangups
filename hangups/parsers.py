"""Parser for long-polling responses from the talkgadget API."""

import logging
import re
from collections import namedtuple
import datetime

from hangups import javascript, exceptions, schemas


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
        """Yield ClientStateUpdate instances from received data."""
        # One submission may contain multiple messages.
        for submission in self.get_submissions(new_data_bytes):
            # For each submission payload, yield its messages
            for payload in _get_submission_payloads(submission):
                if payload is not None:
                    state_update = _parse_payload(payload)
                    if state_update is not None:
                        yield state_update


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
    """Return a ClientStateUpdate from a payload, or None."""
    state_update = None
    if payload[0] == 'cbu':
        try:
            state_update = schemas.CLIENT_STATE_UPDATE.parse(payload[1][0])
        except ValueError as e:
            logger.warning('Failed to parse ClientStateUpdate: {}'.format(e))
    else:
        logger.warning('Invalid payload header: {}'.format(payload[0]))
    logger.info('Parsed ClientStateUpdate: {}'.format(state_update))
    return state_update


def parse_client_state_update(state_update):
    """Parse a ClientStateUpdate, yielding specific message instances.

    TODO: Restore logging for notifications we can't handle yet.
    """
    HANDLERS = [
        (state_update.event_notification, parse_chat_message),
        (state_update.focus_notification, parse_focus_status_message),
        (state_update.typing_notification, parse_typing_status_message),
        (state_update.client_conversation, parse_conversation_status_message),
    ]
    for notification, handler in HANDLERS:
        try:
            if notification is not None:
                yield handler(notification)
        except exceptions.ParseError as e:
            logger.warning('Failed to parse message: {}'.format(e))
        except exceptions.ParseNotImplementedError as e:
            logger.info('Failed to parse message: {}'.format(e))


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


def parse_chat_message(p):
    """Return ChatMessage from parsing ClientEventNotification.

    Raises ParseError if it cannot be parsed.
    """
    # ClientEvent contains any of 5 possible types of events:
    if p.event.chat_message is not None:
        text = ''
        for segment in p.event.chat_message.message_content.segment:
            if segment.type_ == schemas.SegmentType.TEXT:
                text += segment.text
            elif segment.type_ == schemas.SegmentType.LINK:
                text += segment.text
            elif segment.type_ == schemas.SegmentType.LINE_BREAK:
                # Can't use segment.text because Hangouts for Android doesn't
                # set it for linebreaks.
                text += '\n'
            else:
                raise exceptions.ParseError('Unknown segment type: {}'
                                            .format(segment.type_))
        for attachment in p.event.chat_message.message_content.attachment:
            if attachment.embed_item.type_ == [249]: # PLUS_PHOTO
                # Try to parse an image message. Image messages contain no
                # message segments, and thus have no automatic textual
                # fallback.
                try:
                    text += attachment.embed_item.data['27639957'][0][3]
                except (KeyError, TypeError, IndexError):
                    raise exceptions.ParseError(
                        'Failed to parse PLUS_PHOTO attachment: {}'
                        .format(attachment)
                    )
            elif attachment.embed_item.type_ == [340, 335, 0]:
                pass # Google Maps URL that's already in the text.
            else:
                logger.warning('Ignoring unknown attachment: {}'
                               .format(attachment))
        return ChatMessage(
            conv_id=p.event.conversation_id.id_,
            user_id=UserID(chat_id=p.event.sender_id.chat_id,
                           gaia_id=p.event.sender_id.gaia_id),
            timestamp=from_timestamp(p.event.timestamp),
            text=text,
        )
    if p.event.membership_change is not None:
        raise exceptions.ParseNotImplementedError(
            'Unimplemented membership change: {}'
            .format(p.event.membership_change)
        )
    if p.event.conversation_rename is not None:
        raise exceptions.ParseNotImplementedError(
            'Unimplemented conversation rename: {}'
            .format(p.event.conversation_rename)
        )
    if p.event.hangout_event is not None:
        raise exceptions.ParseNotImplementedError(
            'Unimplemented hangout event: {}'
            .format(p.event.hangout_event)
        )
    if p.event.otr_modification is not None:
        raise exceptions.ParseNotImplementedError(
            'Unimplemented OTR modification: {}'
            .format(p.event.otr_modification)
        )


ConversationStatusMessage = namedtuple(
    'ConversationStatusMessage', ['conv_id', 'user_id_list']
)


def parse_conversation_status_message(p):
    """Return ConversationStatusMessage from ClientConversation

    Raises ParseError if it cannot be parsed.
    """
    # TODO: Parse out more of the useful data.
    return ConversationStatusMessage(
        conv_id=p.conversation_id.id_,
        user_id_list=[
            UserID(chat_id=item.id_.chat_id, gaia_id=item.id_.gaia_id)
            for item in p.participant_data
        ],
    )


FocusStatusMessage = namedtuple(
    'FocusStatusMessage',
    ['conv_id', 'user_id', 'timestamp', 'status', 'device']
)


def parse_focus_status_message(p):
    """Return FocusStatusMessage from ClientSetFocusNotification.

    Raises ParseError if it cannot be parsed.
    """
    return FocusStatusMessage(
        conv_id=p.conversation_id.id_,
        user_id=UserID(chat_id=p.user_id.chat_id, gaia_id=p.user_id.gaia_id),
        timestamp=from_timestamp(p.timestamp),
        status=p.status,
        device=p.device,
    )


TypingStatusMessage = namedtuple(
    'TypingStatusMessage', ['conv_id', 'user_id', 'timestamp', 'status']
)


def parse_typing_status_message(p):
    """Return TypingStatusMessage from ClientSetTypingNotification.

    The same status may be sent multiple times consecutively, and when a
    message is sent the typing status will not change to stopped.

    Raises ParseError if it cannot be parsed.
    """
    return TypingStatusMessage(
        conv_id=p.conversation_id.id_,
        user_id=UserID(chat_id=p.user_id.chat_id, gaia_id=p.user_id.gaia_id),
        timestamp=from_timestamp(p.timestamp),
        status=p.status,
    )
