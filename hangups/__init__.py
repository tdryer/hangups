from .version import __version__
from .client import Client
from .user import UserList, build_user_list
from .conversation import ConversationList
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
