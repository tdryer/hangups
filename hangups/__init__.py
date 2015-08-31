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
# Only import enum values and messages from the proto file that are necessary
# for third-party code to use hangups.
from .hangouts_pb2 import (
    TYPING_TYPE_STARTED, TYPING_TYPE_PAUSED, TYPING_TYPE_STOPPED,
    MEMBERSHIP_CHANGE_TYPE_LEAVE, MEMBERSHIP_CHANGE_TYPE_JOIN
)
