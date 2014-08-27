"""pblite message schemas and related enums."""

# Stop pylint from complaining about enum:
# pylint: disable=no-init

import enum

from hangups.pblite import Message, Field, RepeatedField, EnumField


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


class ConversationType(enum.Enum):

    """Conversation type."""

    STICKY_ONE_TO_ONE = 1
    GROUP = 2


class ClientConversationView(enum.Enum):

    """Conversation view."""

    UNKNOWN_CONVERSATION_VIEW = 0
    INBOX_VIEW = 1
    ARCHIVED_VIEW = 2


class ClientNotificationLevel(enum.Enum):

    """Notification level."""

    QUIET = 10
    RING = 30


class ClientConversationStatus(enum.Enum):

    """Conversation status."""

    UNKNOWN_CONVERSATION_STATUS = 0
    INVITED = 1
    ACTIVE = 2
    LEFT = 3


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

CONVERSATION_STATUS_MSG = Message(
    ('conversation_id', CONVERSATION_ID),
    ('type_', EnumField(ConversationType)),
    ('name', Field(is_optional=True)),
    ('self_conversation_state', Message(
        (None, Field(is_optional=True)),
        (None, Field(is_optional=True)),
        (None, Field(is_optional=True)),
        (None, Field(is_optional=True)),
        (None, Field(is_optional=True)),
        (None, Field(is_optional=True)),
        ('self_read_state', Message(
            ('participant_id', USER_ID),
            ('last_read_timestamp', Field()),
        )),
        ('status', EnumField(ClientConversationStatus)),
        ('notification_level', EnumField(ClientNotificationLevel)),
        ('view', RepeatedField(
            EnumField(ClientConversationView)
        )),
        ('inviter_id', USER_ID),
        ('invite_timestamp', Field()),
        ('sort_timestamp', Field(is_optional=True)),
        ('active_timestamp', Field()),
        (None, Field(is_optional=True)),
        (None, Field(is_optional=True)),
        (None, Field()),
        (None, Field()),
    )),
    (None, Field()),
    (None, Field()),
    (None, Field(is_optional=True)),
    ('read_state', RepeatedField(
        Message(
            ('participant_id', USER_ID),
            ('last_read_timestamp', Field()),
        )
    )),
    (None, Field()),
    (None, Field()),
    (None, Field()),
    (None, Field()),
    ('current_participant', RepeatedField(USER_ID)),
    ('participant_data', RepeatedField(
        Message(
            ('id_', USER_ID),
            ('fallback_name', Field()),
            (None, Field(is_optional=True)),
        )
    )),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field()),
    (None, Field()),
)
