# Import the objects here that form the public API of hangups so they may be
# conveniently imported.

# Keep version in a separate file so setup.py can import it separately.
from .version import __version__
from .client import Client
from .user import UserList
from .conversation import ConversationList, build_user_conversation_list
from .auth import (
    get_auth, get_auth_stdin, GoogleAuthError, CredentialsPrompt,
    RefreshTokenCache
)
from .exceptions import HangupsError, NetworkError, ConversationTypeError
from .conversation_event import (
    ChatMessageSegment, ConversationEvent, ChatMessageEvent, OTREvent,
    RenameEvent, MembershipChangeEvent, HangoutEvent,
    GroupLinkSharingModificationEvent
)
# Only import Protocol Buffer objects that are needed for the high-level
# hangups API (ConversationList, etc.) here. Low-level Client users could need
# just about anything, and importing it here would create conflicts.
from .hangouts_pb2 import (
    TYPING_TYPE_STARTED, TYPING_TYPE_PAUSED, TYPING_TYPE_STOPPED,
    MEMBERSHIP_CHANGE_TYPE_LEAVE, MEMBERSHIP_CHANGE_TYPE_JOIN,
    HANGOUT_EVENT_TYPE_START, HANGOUT_EVENT_TYPE_END, HANGOUT_EVENT_TYPE_JOIN,
    HANGOUT_EVENT_TYPE_LEAVE, HANGOUT_EVENT_TYPE_COMING_SOON,
    HANGOUT_EVENT_TYPE_ONGOING, GROUP_LINK_SHARING_STATUS_OFF,
    GROUP_LINK_SHARING_STATUS_ON, NOTIFICATION_LEVEL_QUIET,
    NOTIFICATION_LEVEL_RING, SEGMENT_TYPE_TEXT, SEGMENT_TYPE_LINE_BREAK,
    SEGMENT_TYPE_LINK, OFF_THE_RECORD_STATUS_ON_THE_RECORD,
    OFF_THE_RECORD_STATUS_OFF_THE_RECORD
)
