"""pblite message schemas and related enums."""

# Stop pylint from complaining about enum:
# pylint: disable=no-init

import enum

from hangups.pblite import Message, Field, EnumField


##############################################################################
# Enums
##############################################################################

class TypingStatus(enum.Enum):

    """Typing statuses."""

    TYPING = 1  # The user started typing
    PAUSED = 2  # The user stopped typing with inputted text
    STOPPED = 3  # The user stopped typing with no inputted text


class FocusStatus(enum.Enum):

    """Focus statuses."""

    FOCUSED = 1
    UNFOCUSED = 2


class FocusDevice(enum.Enum):

    """Focus devices."""

    DESKTOP = 20
    MOBILE = 300
    UNSPECIFIED = None


##############################################################################
# pblite Messages
##############################################################################

CONVERSATION_ID = Message(
    ('id_', Field()),
)

USER_ID = Message(
    ('gaia_id', Field()),
    ('chat_id', Field()),
)

TYPING_STATUS_MSG = Message(
    ('conversation_id', CONVERSATION_ID),
    ('user_id', USER_ID),
    ('timestamp', Field()),
    ('status', EnumField(TypingStatus)),
)

FOCUS_STATUS_MSG = Message(
    ('conversation_id', CONVERSATION_ID),
    ('user_id', USER_ID),
    ('timestamp', Field()),
    ('status', EnumField(FocusStatus)),
    ('device', EnumField(FocusDevice)),
)
