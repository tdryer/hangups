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

    UNKNOWN = None
    QUIET = 10
    RING = 30


class ClientConversationStatus(enum.Enum):

    """Conversation status."""

    UNKNOWN_CONVERSATION_STATUS = 0
    INVITED = 1
    ACTIVE = 2
    LEFT = 3


class SegmentType(enum.Enum):

    """Message content segment type."""

    TEXT = 0
    LINE_BREAK = 1
    LINK = 2


class MembershipChangeType(enum.Enum):

    """Conversation membership change type."""

    JOIN = 1
    LEAVE = 2


class ClientHangoutEventType(enum.Enum):

    """Hangout event type."""

    # Not sure all of these are correct
    START_HANGOUT = 1
    END_HANGOUT = 2
    JOIN_HANGOUT = 3
    LEAVE_HANGOUT = 4
    HANGOUT_COMING_SOON = 5
    ONGOING_HANGOUT = 6


class ClientOffTheRecordStatus(enum.Enum):

    """Off-the-record status."""

    OFF_THE_RECORD = 1
    ON_THE_RECORD = 2


class ClientOffTheRecordToggle(enum.Enum):

    """Off-the-record toggle status."""

    ENABLED = 0
    DISABLED = 1


class ActiveClientState(enum.Enum):

    """Active client state."""

    NO_ACTIVE_CLIENT = 0
    IS_ACTIVE_CLIENT = 1
    OTHER_CLIENT_IS_ACTIVE = 2


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

OPTIONAL_USER_ID = Message(
    ('gaia_id', Field()),
    ('chat_id', Field()),
    is_optional=True,
)

CLIENT_SET_TYPING_NOTIFICATION = Message(
    ('conversation_id', CONVERSATION_ID),
    ('user_id', USER_ID),
    ('timestamp', Field()),
    ('status', EnumField(TypingStatus)),
    is_optional=True,
)

CLIENT_SET_FOCUS_NOTIFICATION = Message(
    ('conversation_id', CONVERSATION_ID),
    ('user_id', USER_ID),
    ('timestamp', Field()),
    ('status', EnumField(FocusStatus)),
    ('device', EnumField(FocusDevice)),
    is_optional=True,
)

CLIENT_CONVERSATION = Message(
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
            ('latest_read_timestamp', Field()),
        )),
        ('status', EnumField(ClientConversationStatus)),
        ('notification_level', EnumField(ClientNotificationLevel)),
        ('view', RepeatedField(
            EnumField(ClientConversationView)
        )),
        ('inviter_id', USER_ID),
        ('invite_timestamp', Field()),
        ('sort_timestamp', Field(is_optional=True)),
        ('active_timestamp', Field(is_optional=True)),
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
            ('fallback_name', Field(is_optional=True)),
            (None, Field(is_optional=True)),
        )
    )),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field()),
    (None, Field()),
    is_optional=True,
)

MESSAGE_SEGMENT = Message(
    ('type_', EnumField(SegmentType)),
    ('text', Field(is_optional=True)),  # Can be None for linebreaks
    ('formatting', Message(
        ('bold', Field(is_optional=True)),
        ('italic', Field(is_optional=True)),
        ('strikethrough', Field(is_optional=True)),
        ('underline', Field(is_optional=True)),
        is_optional=True,
    )),
    ('link_data', Message(
        ('link_target', Field(is_optional=True)),
        is_optional=True,
    )),
)

MESSAGE_ATTACHMENT = Message(
    ('embed_item', Message(
        # 249 (PLUS_PHOTO), 340, 335, 0
        ('type_', RepeatedField(Field())),
        ('data', Field()),  # can be a dict
    )),
)

CLIENT_CHAT_MESSAGE = Message(
    (None, Field(is_optional=True)),  # always None?
    ('annotation', RepeatedField(Field(), is_optional=True)),
    ('message_content', Message(
        ('segment', RepeatedField(MESSAGE_SEGMENT, is_optional=True)),
        ('attachment', RepeatedField(MESSAGE_ATTACHMENT, is_optional=True)),
    )),
    is_optional=True,
)

CLIENT_CONVERSATION_RENAME = Message(
    ('new_name', Field()),
    ('old_name', Field()),
    is_optional=True,
)

CLIENT_HANGOUT_EVENT = Message(
    ('event_type', EnumField(ClientHangoutEventType)),
    ('participant_id', RepeatedField(USER_ID)),
    ('hangout_duration_secs', Field(is_optional=True)),
    ('transferred_conversation_id', Field(is_optional=True)),  # always None?
    ('refresh_timeout_secs', Field(is_optional=True)),
    ('is_periodic_refresh', Field(is_optional=True)),
    (None, Field(is_optional=True)),  # always 1?
    is_optional=True,
)

CLIENT_OTR_MODIFICATION = Message(
    ('old_otr_status', EnumField(ClientOffTheRecordStatus)),
    ('new_otr_status', EnumField(ClientOffTheRecordStatus)),
    ('old_otr_toggle', EnumField(ClientOffTheRecordToggle)),
    ('new_otr_toggle', EnumField(ClientOffTheRecordToggle)),
    is_optional=True,
)

CLIENT_MEMBERSHIP_CHANGE = Message(
    ('type_', EnumField(MembershipChangeType)),
    (None, RepeatedField(Field())),
    ('participant_ids', RepeatedField(USER_ID)),
    (None, Field()),
    is_optional=True,
)

CLIENT_EVENT = Message(
    ('conversation_id', CONVERSATION_ID),
    ('sender_id', OPTIONAL_USER_ID),
    ('timestamp', Field()),
    ('self_event_state', Message(
        ('user_id', USER_ID),
        ('client_generated_id', Field(is_optional=True)),
        ('notification_level', EnumField(ClientNotificationLevel)),
        is_optional=True,
    )),
    (None, Field(is_optional=True)),  # always None?
    (None, Field(is_optional=True)),  # always 0? (expiration_timestamp?)
    ('chat_message', CLIENT_CHAT_MESSAGE),
    (None, Field(is_optional=True)),  # always None?
    ('membership_change', CLIENT_MEMBERSHIP_CHANGE),
    ('conversation_rename', CLIENT_CONVERSATION_RENAME),
    ('hangout_event', CLIENT_HANGOUT_EVENT),
    ('event_id', Field(is_optional=True)),
    ('advances_sort_timestamp', Field(is_optional=True)),
    ('otr_modification', CLIENT_OTR_MODIFICATION),
    (None, Field(is_optional=True)),  # 0, 1 or None? related to notifications?
    ('event_otr', EnumField(ClientOffTheRecordStatus)),
    (None, Field()),  # always 1? (advances_sort_timestamp?)
)

CLIENT_EVENT_NOTIFICATION = Message(
    ('event', CLIENT_EVENT),
    is_optional=True,
)

CLIENT_WATERMARK_NOTIFICATION = Message(
    ('participant_id', USER_ID),
    ('conversation_id', CONVERSATION_ID),
    ('latest_read_timestamp', Field()),
    is_optional=True,
)

CLIENT_STATE_UPDATE_HEADER = Message(
    ('active_client_state', EnumField(ActiveClientState)),
    (None, Field(is_optional=True)),
    ('request_trace_id', Field()),
    (None, Field(is_optional=True)),
    ('current_server_time', Field()),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    # optional ID of the client causing the update?
    (None, Field(is_optional=True)),
)

CLIENT_STATE_UPDATE = Message(
    ('state_update_header', CLIENT_STATE_UPDATE_HEADER),
    ('conversation_notification', Field(is_optional=True)),  # always None?
    ('event_notification', CLIENT_EVENT_NOTIFICATION),
    ('focus_notification', CLIENT_SET_FOCUS_NOTIFICATION),
    ('typing_notification', CLIENT_SET_TYPING_NOTIFICATION),
    ('notification_level_notification', Field(is_optional=True)),
    ('reply_to_invite_notification', Field(is_optional=True)),
    ('watermark_notification', CLIENT_WATERMARK_NOTIFICATION),
    (None, Field(is_optional=True)),
    ('settings_notification', Field(is_optional=True)),
    ('view_modification', Field(is_optional=True)),
    ('easter_egg_notification', Field(is_optional=True)),
    ('client_conversation', CLIENT_CONVERSATION),
    ('self_presence_notification', Field(is_optional=True)),
    ('delete_notification', Field(is_optional=True)),
    ('presence_notification', Field(is_optional=True)),
    ('block_notification', Field(is_optional=True)),
    ('invitation_watermark_notification', Field(is_optional=True)),
)

CLIENT_EVENT_CONTINUATION_TOKEN = Message(
    ('event_id', Field(is_optional=True)),
    ('storage_continuation_token', Field()),
    ('event_timestamp', Field()),
    is_optional=True,
)

CLIENT_CONVERSATION_STATE = Message(
    ('conversation_id', CONVERSATION_ID),
    ('conversation', CLIENT_CONVERSATION),
    ('event', RepeatedField(CLIENT_EVENT)),
    (None, Field(is_optional=True)),
    ('event_continuation_token', CLIENT_EVENT_CONTINUATION_TOKEN),
    (None, Field(is_optional=True)),
    (None, RepeatedField(Field())),
)

CLIENT_CONVERSATION_STATE_LIST = RepeatedField(CLIENT_CONVERSATION_STATE)

CLIENT_ENTITY = Message(
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    ('id_', USER_ID),
    ('properties', Message(
        ('type_', Field(is_optional=True)),  # 0, 1, or None
        ('display_name', Field(is_optional=True)),
        ('first_name', Field(is_optional=True)),
        ('photo_url', Field(is_optional=True)),
        ('emails', RepeatedField(Field())),
    )),
)

ENTITY_GROUP = Message(
    (None, Field()), # always 0?
    (None, Field()), # some sort of ID
    ('entity', RepeatedField(Message(
        ('entity', CLIENT_ENTITY),
        (None, Field()),  # always 0?
    ))),
)

INITIAL_CLIENT_ENTITIES = Message(
    (None, Field()),  # 'cgserp'
    (None, Field()),  # a header
    ('entities', RepeatedField(CLIENT_ENTITY)),
    (None, Field(is_optional=True)),  # always None?
    ('group1', ENTITY_GROUP),
    ('group2', ENTITY_GROUP),
    ('group3', ENTITY_GROUP),
    ('group4', ENTITY_GROUP),
    ('group5', ENTITY_GROUP),

)

CLIENT_GET_SELF_INFO_RESPONSE = Message(
    (None, Field()),  # 'cgsirp'
    (None, Field()),  # response header
    ('self_entity', CLIENT_ENTITY),
)

CLIENT_RESPONSE_HEADER = Message(
    ('status', Field()),  # 1 => success
    (None, Field(is_optional=True)),
    (None, Field(is_optional=True)),
    ('request_trace_id', Field()),
    ('current_server_time', Field()),
)

CLIENT_SYNC_ALL_NEW_EVENTS_RESPONSE = Message(
    (None, Field()),  # 'csanerp'
    ('response_header', CLIENT_RESPONSE_HEADER),
    ('sync_timestamp', Field()),
    ('conversation_state', RepeatedField(CLIENT_CONVERSATION_STATE)),
)

CLIENT_GET_CONVERSATION_RESPONSE = Message(
    (None, Field()),  # 'cgcrp'
    ('response_header', CLIENT_RESPONSE_HEADER),
    ('conversation_state', CLIENT_CONVERSATION_STATE),
)
