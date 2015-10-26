"""Parsing helper functions."""

from collections import namedtuple
import datetime
import logging

from hangups import user


logger = logging.getLogger(__name__)


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
    """Return TypingStatusMessage from hangouts_pb2.SetTypingNotification.

    The same status may be sent multiple times consecutively, and when a
    message is sent the typing status will not change to stopped.
    """
    return TypingStatusMessage(
        conv_id=p.conversation_id.id,
        user_id=user.UserID(chat_id=p.sender_id.chat_id,
                            gaia_id=p.sender_id.gaia_id),
        timestamp=from_timestamp(p.timestamp),
        status=p.type,
    )


WatermarkNotification = namedtuple(
    'WatermarkNotification', ['conv_id', 'user_id', 'read_timestamp']
)


def parse_watermark_notification(p):
    """Return WatermarkNotification from hangouts_pb2.WatermarkNotification."""
    return WatermarkNotification(
        conv_id=p.conversation_id.id,
        user_id=user.UserID(
            chat_id=p.sender_id.chat_id,
            gaia_id=p.sender_id.gaia_id,
        ),
        read_timestamp=from_timestamp(
            p.latest_read_timestamp
        ),
    )
