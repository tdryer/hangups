"""Conversation objects."""

import logging
from tornado import gen

from hangups import parsers, event, user, conversation_event

logger = logging.getLogger(__name__)


class Conversation(object):

    """Wrapper around Client for working with a single chat conversation."""

    def __init__(self, client, user_list, client_conversation, client_events):
        """Initialize a new Conversation."""
        self._client = client  # Client
        self._user_list = user_list  # UserList
        self._conversation = client_conversation  # ClientConversation
        self._events = []  # [ConversationEvent]
        for event_ in client_events:
            self.add_event(event_)

        # Event fired when a user starts or stops typing with arguments
        # (typing_message).
        self.on_typing = event.Event('Conversation.on_typing')
        # Event fired when a new ConversationEvent arrives with arguments
        # (ConversationEvent).
        self.on_event = event.Event('Conversation.on_event')

    def update_conversation(self, client_conversation):
        """Update the internal ClientConversation."""
        self._conversation = client_conversation

    def add_event(self, event_):
        """Add a ClientEvent to the Conversation.

        Returns an instance of ConversationEvent or subclass.
        """
        if event_.chat_message is not None:
            conv_event = conversation_event.ChatMessageEvent(event_)
        elif event_.conversation_rename is not None:
            conv_event = conversation_event.RenameEvent(event_)
        elif event_.membership_change is not None:
            conv_event = conversation_event.MembershipChangeEvent(event_)
        else:
            conv_event = conversation_event.ConversationEvent(event_)
        self._events.append(conv_event)
        return conv_event

    def get_user(self, user_id):
        """Return the User instance with the given UserID."""
        return self._user_list.get_user(user_id)

    @gen.coroutine
    def send_message(self, segments):
        """Send a message to this conversation.

        segments must be a list of ChatMessageSegments to include in the
        message.

        Raises hangups.NetworkError if the message can not be sent.
        """
        yield self._client.sendchatmessage(self.id_, [seg.serialize()
                                                      for seg in segments])

    @property
    def id_(self):
        """The conversation's ID."""
        return self._conversation.conversation_id.id_

    @property
    def users(self):
        """User instances of the conversation's current participants."""
        return [self._user_list.get_user(user.UserID(chat_id=part.id_.chat_id,
                                                     gaia_id=part.id_.gaia_id))
                for part in self._conversation.participant_data]

    @property
    def name(self):
        """The conversation's custom name, or None if it doesn't have one."""
        return self._conversation.name

    @property
    def last_modified(self):
        """datetime timestamp of when the conversation was last modified."""
        return parsers.from_timestamp(
            self._conversation.self_conversation_state.sort_timestamp
        )

    @property
    def events(self):
        """The list of ConversationEvents, sorted oldest to newest."""
        return list(self._events)


class ConversationList(object):
    """Wrapper around Client that maintains a list of Conversations."""

    def __init__(self, client, conv_states, user_list):
        self._client = client
        self._conv_dict = {}  # {conv_id: Conversation}

        # Initialize the list of conversations from Client's list of
        # ClientConversationStates.
        for conv_state in conv_states:
            conv_id = conv_state.conversation_id.id_
            self._conv_dict[conv_id] = Conversation(
                self._client, user_list, conv_state.conversation,
                conv_state.event
            )

        self._client.on_state_update.add_observer(self._on_state_update)
        self._client.on_event_notification.add_observer(
            self._on_event_notification
        )

        # Event fired when a new ConversationEvent arrives with arguments
        # (ConversationEvent).
        self.on_event = event.Event('ConversationList.on_event')
        # Event fired when a user starts or stops typing with arguments
        # (typing_message).
        self.on_typing = event.Event('ConversationList.on_typing')

    def get_all(self):
        """Return list of all Conversations."""
        return list(self._conv_dict.values())

    def get(self, conv_id):
        """Return a Conversation from its ID.

        Raises KeyError if the conversation ID is invalid.
        """
        return self._conv_dict[conv_id]

    def _on_state_update(self, state_update):
        """Receive a ClientStateUpdate and fan out to Conversations."""
        if state_update.client_conversation is not None:
            self._handle_client_conversation(state_update.client_conversation)
        if state_update.typing_notification is not None:
            self._handle_set_typing_notification(
                state_update.typing_notification
            )
        if state_update.event_notification is not None:
            self._on_event_notification(state_update.event_notification)

    def _on_event_notification(self, event_notification):
        """Receive a ClientEventNofication and fan out to Conversations."""
        event_ = event_notification.event
        try:
            conv = self._conv_dict[event_.conversation_id.id_]
        except KeyError:
            logger.warning('Received ClientEvent for unknown conversation {}'
                           .format(event_.conversation_id.id_))
        else:
            conv_event = conv.add_event(event_)
            self.on_event.fire(conv_event)
            conv.on_event.fire(conv_event)

    def _handle_client_conversation(self, client_conversation):
        """Receive ClientConversation and update the conversation."""
        conv_id = client_conversation.conversation_id.id_
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            conv.update_conversation(client_conversation)
        else:
            logger.warning('Received ClientConversation for '
                           'unknown conversation {}'.format(conv_id))

    def _handle_set_typing_notification(self, set_typing_notification):
        """Receive ClientSetTypingNotification and update the conversation."""
        conv_id = set_typing_notification.conversation_id.id_
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            res = parsers.parse_typing_status_message(set_typing_notification)
            self.on_typing.fire(res)
            conv.on_typing.fire(res)
        else:
            logger.warning('Received ClientSetTypingNotification for '
                           'unknown conversation {}'.format(conv_id))
