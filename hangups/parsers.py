"""Parser for long-polling responses from the talkgadget API."""

import logging
from collections import namedtuple
import datetime

from hangups import javascript, exceptions, schemas, user


logger = logging.getLogger(__name__)


def parse_submission(submission):
    """Yield ClientStateUpdate instances from a channel submission."""
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
        logger.warning('Invalid payload header: {}'.format(payload[0]))


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
