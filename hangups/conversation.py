"""Conversation objects."""

import logging
from tornado import gen

from hangups import parsers, exceptions, event

logger = logging.getLogger(__name__)


class Conversation(object):
    """Wrapper around Client for working with a single chat conversation."""

    def __init__(self, client, id_, users, last_modified, chat_name,
                 chat_messages):
        # TODO: initialize directly from ClientConversationState
        self._client = client
        self._id = id_ # ConversationID
        self._users = {user.id_: user for user in users} # {UserID: User}
        self._last_modified = last_modified # datetime
        self._name = chat_name # str
        self._chat_messages = chat_messages # ChatMessage

        # Event fired when a new message arrives with arguments (chat_message).
        self.on_message = event.Event('Conversation.on_message')
        # Event fired when a users starts or stops typing with arguments
        # (typing_message).
        self.on_typing = event.Event('Conversation.on_typing')

    @property
    def id_(self):
        """Return the Conversation's ID."""
        return self._id

    @property
    def users(self):
        """Return the list of Users participating in the Conversation."""
        return list(self._users.values())

    def get_user(self, user_id):
        """Return a participating use by UserID.

        Raises KeyError if the user ID is not a participant.
        """
        return self._users[user_id]

    @property
    def name(self):
        """ Return chat name if it was renamed manually or None
        :rtype: str
        """
        return self._name

    @property
    def last_modified(self):
        """Return the timestamp of when the conversation was last modified."""
        return self._last_modified

    @property
    def chat_messages(self):
        """Return a list of ChatMessages, sorted oldest to newest."""
        return list(self._chat_messages)

    @gen.coroutine
    def send_message(self, text):
        """Send a message to this conversation.

        text may not be empty.

        Raises hangups.NetworkError if the message can not be sent.
        """
        yield self._client.sendchatmessage(self._id, text)

    def handle_chat_message(self, chat_message):
        """Receive ClientChatMessage and update the conversation."""
        # TODO: We're actually receiving ClientEventNotification for now
        # because that's what the parser takes.
        try:
            res = parsers.parse_chat_message(chat_message)
        except exceptions.ParseError as e:
            logger.warning('Failed to parse message: {}'.format(e))
        except exceptions.ParseNotImplementedError as e:
            logger.info('Failed to parse message: {}'.format(e))
        else:
            self.on_message.fire(res)

    def handle_set_typing_notification(self, set_typing_notification):
        """Receive ClientSetTypingNotification and update the conversation."""
        res = parsers.parse_typing_status_message(set_typing_notification)
        self.on_typing.fire(res)


class ConversationList(object):
    """Wrapper around Client that maintains a list of Conversations."""

    def __init__(self, client):
        self._client = client
        # {conv_id: Conversation}
        self._conv_dict = client.initial_conversations
        self._client.on_state_update.add_observer(self._on_state_update)

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
        if state_update.typing_notification is not None:
            conv_id = state_update.typing_notification.conversation_id.id_
            if conv_id in self._conv_dict:
                self.get(conv_id).handle_set_typing_notification(
                    state_update.typing_notification
                )
            else:
                logger.warning('Received ClientSetTypingNotification for '
                               'unknown conversation {}'.format(conv_id))

        if state_update.event_notification is not None:
            ev = state_update.event_notification.event
            conv_id = ev.conversation_id.id_
            if conv_id in self._conv_dict:
                conv = self.get(conv_id)
                if ev.chat_message is not None:
                    conv.handle_chat_message(state_update.event_notification)
            else:
                logger.warning('Received ClientEvent for '
                               'unknown conversation {}'.format(conv_id))
