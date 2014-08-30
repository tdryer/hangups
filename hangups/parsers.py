"""Parser for long-polling responses from the talkgadget API."""

import logging
from collections import namedtuple
import datetime

from hangups import javascript, exceptions, schemas


logger = logging.getLogger(__name__)


User = namedtuple('User', ['id_', 'full_name', 'first_name', 'is_self'])


UserID = namedtuple('UserID', ['chat_id', 'gaia_id'])


def parse_submission(submission):
    """Yield ClientStateUpdate instances from a channel submission."""
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
