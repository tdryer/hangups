"""Parser for long-polling responses from the talkgadget API."""

import logging
from collections import namedtuple
import datetime

from hangups import javascript, schemas, user


logger = logging.getLogger(__name__)


def parse_submission(submission):
    """Yield ClientStateUpdate instances from a channel submission."""
    # For each submission payload, yield its messages
    for payload in _get_submission_payloads(submission):
        if payload is not None:
            if isinstance(payload, dict) and 'client_id' in payload:
                # Hack to pass the client ID back to Client
                yield payload
            else:
                yield from _parse_payload(payload)


def _get_submission_payloads(submission):
    """Yield a submission's payloads.

    Most submissions only contain one payload, but if the long-polling
    connection was closed while something happened, there can be multiple
    payloads.
    """
    for sub in javascript.loads(submission):

        if sub[1][0] != 'noop':
            wrapper = javascript.loads(sub[1][0]['p'])
            # pylint: disable=invalid-sequence-index
            if '3' in wrapper and '2' in wrapper['3']:
                client_id = wrapper['3']['2']
                # Hack to pass the client ID back to Client
                yield {'client_id': client_id}
            if '2' in wrapper:
                yield javascript.loads(wrapper['2']['2'])


def _parse_payload(payload):
    """Yield a list of ClientStateUpdates."""
    if payload[0] == 'cbu':
        # payload[1] is a list of state updates.
        for raw_update in payload[1]:
            try:
                state_update = schemas.CLIENT_STATE_UPDATE.parse(raw_update)
                logger.info('Parsed ClientStateUpdate: {}'.format(state_update))
                yield state_update
            except ValueError as e:
                logger.warning('Failed to parse ClientStateUpdate: {}'
                               .format(e))
    else:
        logger.info('Ignoring payload with header: {}'.format(payload[0]))


##############################################################################
# Message parsing utils
##############################################################################


def from_timestamp(microsecond_timestamp):
    """Convert a microsecond timestamp to a UTC datetime instance."""
    # Create datetime without losing precision from floating point (yes, this
    # is actually needed):
    return datetime.datetime.fromtimestamp(
        microsecond_timestamp // 1000000, datetime.timezone.utc
    ).replace(microsecond=(microsecond_timestamp % 1000000))


def to_timestamp(datetime_timestamp):
    """Convert UTC datetime to microsecond timestamp used by Hangouts."""
    return int(datetime_timestamp.timestamp() * 1000000)


##############################################################################
# Message types and parsers
##############################################################################


TypingStatusMessage = namedtuple(
    'TypingStatusMessage', ['conv_id', 'user_id', 'timestamp', 'status']
)


def parse_typing_status_message(p):
    """Return TypingStatusMessage from ClientSetTypingNotification.

    The same status may be sent multiple times consecutively, and when a
    message is sent the typing status will not change to stopped.
    """
    return TypingStatusMessage(
        conv_id=p.conversation_id.id_,
        user_id=user.UserID(chat_id=p.user_id.chat_id,
                            gaia_id=p.user_id.gaia_id),
        timestamp=from_timestamp(p.timestamp),
        status=p.status,
    )


WatermarkNotification = namedtuple(
    'WatermarkNotification', ['conv_id', 'user_id', 'read_timestamp']
)


def parse_watermark_notification(client_watermark_notification):
    """Return WatermarkNotification from ClientWatermarkNotification."""
    return WatermarkNotification(
        conv_id=client_watermark_notification.conversation_id.id_,
        user_id=user.UserID(
            chat_id=client_watermark_notification.participant_id.chat_id,
            gaia_id=client_watermark_notification.participant_id.gaia_id,
        ),
        read_timestamp=from_timestamp(
            client_watermark_notification.latest_read_timestamp
        ),
    )
