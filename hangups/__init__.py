# Import the objects here that form the public API of hangups so they may be
# conveniently imported.

# Keep version in a separate file so setup.py can import it separately.
from .version import __version__
from .client import Client
from .user import UserList
from .conversation import ConversationList, build_user_conversation_list
from .auth import get_auth, get_auth_stdin, GoogleAuthError
from .exceptions import HangupsError, NetworkError
from .conversation_event import (ChatMessageSegment, ConversationEvent,
                                 ChatMessageEvent, RenameEvent,
                                 MembershipChangeEvent)
# Only import Protocol Buffer objects that are needed for the high-level
# hangups API (ConversationList, etc.) here. Low-level Client users could need
# just about anything, and importing it here would create conflicts.
from .hangouts_pb2 import (
    TYPING_TYPE_STARTED, TYPING_TYPE_PAUSED, TYPING_TYPE_STOPPED,
    MEMBERSHIP_CHANGE_TYPE_LEAVE, MEMBERSHIP_CHANGE_TYPE_JOIN
)
