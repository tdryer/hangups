"""Conversation objects."""

import asyncio
import logging

from hangups import (parsers, event, user, conversation_event, exceptions,
                     schemas)

logger = logging.getLogger(__name__)


class Conversation(object):

    """Wrapper around Client for working with a single chat conversation."""

    def __init__(self, client, user_list, client_conversation,
                 client_events=[]):
        """Initialize a new Conversation."""
        self._client = client  # Client
        self._user_list = user_list  # UserList
        self._conversation = client_conversation  # ClientConversation
        self._events = []  # [ConversationEvent]
        self._events_dict = {}  # {event_id: ConversationEvent}
        for event_ in client_events:
            self.add_event(event_)

        # Event fired when a user starts or stops typing with arguments
        # (typing_message).
        self.on_typing = event.Event('Conversation.on_typing')
        # Event fired when a new ConversationEvent arrives with arguments
        # (ConversationEvent).
        self.on_event = event.Event('Conversation.on_event')
        # Event fired when a watermark (read timestamp) is updated with
        # arguments (WatermarkNotification).
        self.on_watermark_notification = event.Event(
            'Conversation.on_watermark_notification'
        )
        self.on_watermark_notification.add_observer(
            self._on_watermark_notification
        )

    def _on_watermark_notification(self, notif):
        """Update the conversations latest_read_timestamp."""
        if self.get_user(notif.user_id).is_self:
            logger.info('latest_read_timestamp for {} updated to {}'
                        .format(self.id_, notif.read_timestamp))
            self_conversation_state = self._conversation.self_conversation_state
            self_conversation_state.self_read_state.latest_read_timestamp = (
                parsers.to_timestamp(notif.read_timestamp)
            )

    def update_conversation(self, client_conversation):
        """Update the internal ClientConversation."""
        # When latest_read_timestamp is 0, this seems to indicate no change
        # from the previous value. Word around this by saving and restoring the
        # previous value.
        old_timestamp = self.latest_read_timestamp
        self._conversation = client_conversation
        if parsers.to_timestamp(self.latest_read_timestamp) == 0:
            self_conversation_state = self._conversation.self_conversation_state
            self_conversation_state.self_read_state.latest_read_timestamp = (
                parsers.to_timestamp(old_timestamp)
            )

    @staticmethod
    def _wrap_event(event_):
        """Wrap ClientEvent in ConversationEvent subclass."""
        if event_.chat_message is not None:
            return conversation_event.ChatMessageEvent(event_)
        elif event_.conversation_rename is not None:
            return conversation_event.RenameEvent(event_)
        elif event_.membership_change is not None:
            return conversation_event.MembershipChangeEvent(event_)
        else:
            return conversation_event.ConversationEvent(event_)

    def add_event(self, event_):
        """Add a ClientEvent to the Conversation.

        Returns an instance of ConversationEvent or subclass.
        """
        conv_event = self._wrap_event(event_)
        self._events.append(conv_event)
        self._events_dict[conv_event.id_] = conv_event
        return conv_event

    def get_user(self, user_id):
        """Return the User instance with the given UserID."""
        return self._user_list.get_user(user_id)

    @asyncio.coroutine
    def send_message(self, segments):
        """Send a message to this conversation.

        segments must be a list of ChatMessageSegments to include in the
        message.

        Raises hangups.NetworkError if the message can not be sent.
        """
        try:
            yield from self._client.sendchatmessage(
                self.id_, [seg.serialize() for seg in segments]
            )
        except exceptions.NetworkError as e:
            logger.warning('Failed to send message: {}'.format(e))
            raise

    @asyncio.coroutine
    def leave(self):
        """Leave conversation.

        Raises hangups.NetworkError if conversation cannot be left.
        """
        try:
            if self._conversation.type_ == schemas.ConversationType.GROUP:
                yield from self._client.removeuser(self.id_)
            else:
                yield from self._client.deleteconversation(self.id_)
        except exceptions.NetworkError as e:
            logger.warning('Failed to leave conversation: {}'.format(e))
            raise

    @asyncio.coroutine
    def set_typing(self, typing=schemas.TypingStatus.TYPING):
        """Set typing status.

        TODO: Add rate-limiting to avoid unnecessary requests.

        Raises hangups.NetworkError if typing status cannot be set.
        """
        try:
            yield from self._client.settyping(self.id_, typing)
        except exceptions.NetworkError as e:
            logger.warning('Failed to set typing status: {}'.format(e))
            raise

    @asyncio.coroutine
    def update_read_timestamp(self, read_timestamp=None):
        """Update the timestamp of the latest event which has been read.

        By default, the timestamp of the newest event is used.

        This method will avoid making an API request if it will have no effect.

        Raises hangups.NetworkError if the timestamp can not be updated.
        """
        if read_timestamp is None:
            read_timestamp = self.events[-1].timestamp
        if read_timestamp > self.latest_read_timestamp:
            logger.info(
                'Setting {} latest_read_timestamp from {} to {}'
                .format(self.id_, self.latest_read_timestamp, read_timestamp)
            )
            # Prevent duplicate requests by updating the conversation now.
            state = self._conversation.self_conversation_state
            state.self_read_state.latest_read_timestamp = (
                parsers.to_timestamp(read_timestamp)
            )
            try:
                yield from self._client.updatewatermark(self.id_,
                                                        read_timestamp)
            except exceptions.NetworkError as e:
                logger.warning('Failed to update read timestamp: {}'.format(e))
                raise

    @asyncio.coroutine
    def get_events(self, event_id=None, max_events=50):
        """Return list of ConversationEvents ordered newest-first.

        If event_id is specified, return events preceeding this event.

        This method will make an API request to load historical events if
        necessary. If the beginning of the conversation is reached, an empty
        list will be returned.

        Raises KeyError if event_id does not correspond to a known event.

        Raises hangups.NetworkError if the events could not be requested.
        """
        if event_id is None:
            # If no event_id is provided, return the newest events in this
            # conversation.
            conv_events = self._events[-1 * max_events:]
        else:
            # If event_id is provided, return the events we have that are
            # older, or request older events if event_id corresponds to the
            # oldest event we have.
            conv_event = self.get_event(event_id)
            if self._events[0].id_ != event_id:
                conv_events = self._events[self._events.index(conv_event) + 1:]
            else:
                logger.info('Loading events for conversation {} before {}'
                            .format(self.id_, conv_event.timestamp))
                res = yield from self._client.getconversation(
                    self.id_, conv_event.timestamp, max_events
                )
                conv_events = [self._wrap_event(client_event) for client_event
                               in res.conversation_state.event]
                logger.info('Loaded {} events for conversation {}'
                            .format(len(conv_events), self.id_))
                for conv_event in reversed(conv_events):
                    self._events.insert(0, conv_event)
                    self._events_dict[conv_event.id_] = conv_event
        return conv_events

    def next_event(self, event_id, prev=False):
        """Return ConversationEvent following the event with given event_id.

        If prev is True, return the previous event rather than the following
        one.

        Raises KeyError if no such ConversationEvent is known.

        Return None if there is no following event.
        """
        i = self.events.index(self._events_dict[event_id])
        if prev and i > 0:
            return self.events[i - 1]
        elif not prev and i + 1 < len(self.events):
            return self.events[i + 1]
        else:
            return None

    def get_event(self, event_id):
        """Return ConversationEvent with the given event_id.

        Raises KeyError if no such ConversationEvent is known.
        """
        return self._events_dict[event_id]

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
    def latest_read_timestamp(self):
        """datetime timestamp of the last read ConversationEvent."""
        timestamp = (self._conversation.self_conversation_state.\
                     self_read_state.latest_read_timestamp)
        return parsers.from_timestamp(timestamp)

    @property
    def events(self):
        """The list of ConversationEvents, sorted oldest to newest."""
        return list(self._events)

    @property
    def unread_events(self):
        """List of ConversationEvents that are unread.

        Events are sorted oldest to newest.

        Note that some Hangouts clients don't update the read timestamp for
        certain event types, such as membership changes, so this method may
        return more unread events than these clients will show. There's also a
        delay between sending a message and the user's own message being
        considered read.
        """
        return [conv_event for conv_event in self._events
                if conv_event.timestamp > self.latest_read_timestamp]

    @property
    def is_archived(self):
        """True if this conversation has been archived."""
        return (schemas.ClientConversationView.ARCHIVED_VIEW in
                self._conversation.self_conversation_state.view)


class ConversationList(object):
    """Wrapper around Client that maintains a list of Conversations."""

    def __init__(self, client, conv_states, user_list, sync_timestamp):
        self._client = client  # Client
        self._conv_dict = {}  # {conv_id: Conversation}
        self._sync_timestamp = sync_timestamp  # datetime
        self._user_list = user_list # UserList

        # Initialize the list of conversations from Client's list of
        # ClientConversationStates.
        for conv_state in conv_states:
            self.add_conversation(conv_state.conversation, conv_state.event)

        self._client.on_state_update.add_observer(self._on_state_update)
        self._client.on_connect.add_observer(self._sync)
        self._client.on_reconnect.add_observer(self._sync)

        # Event fired when a new ConversationEvent arrives with arguments
        # (ConversationEvent).
        self.on_event = event.Event('ConversationList.on_event')
        # Event fired when a user starts or stops typing with arguments
        # (typing_message).
        self.on_typing = event.Event('ConversationList.on_typing')
        # Event fired when a watermark (read timestamp) is updated with
        # arguments (WatermarkNotification).
        self.on_watermark_notification = event.Event(
            'ConversationList.on_watermark_notification'
        )

    def get_all(self, include_archived=False):
        """Return list of all Conversations.

        If include_archived is False, do not return any archived conversations.
        """
        return [conv for conv in self._conv_dict.values()
                if not conv.is_archived or include_archived]

    def get(self, conv_id):
        """Return a Conversation from its ID.

        Raises KeyError if the conversation ID is invalid.
        """
        return self._conv_dict[conv_id]

    def add_conversation(self, client_conversation, client_events=[]):
        """Add new conversation from ClientConversation"""
        conv_id = client_conversation.conversation_id.id_
        logger.info('Adding new conversation: {}'.format(conv_id))
        conv = Conversation(
            self._client, self._user_list,
            client_conversation, client_events
        )
        self._conv_dict[conv_id] = conv
        return conv

    @asyncio.coroutine
    def leave_conversation(self, conv_id):
        """Leave conversation and remove it from ConversationList"""
        logger.info('Leaving conversation: {}'.format(conv_id))
        yield from self._conv_dict[conv_id].leave()
        del self._conv_dict[conv_id]

    @asyncio.coroutine
    def _on_state_update(self, state_update):
        """Receive a ClientStateUpdate and fan out to Conversations."""
        if state_update.client_conversation is not None:
            self._handle_client_conversation(state_update.client_conversation)
        if state_update.typing_notification is not None:
            yield from self._handle_set_typing_notification(
                state_update.typing_notification
            )
        if state_update.watermark_notification is not None:
            yield from self._handle_watermark_notification(
                state_update.watermark_notification
            )
        if state_update.event_notification is not None:
            yield from self._on_client_event(
                state_update.event_notification.event
            )

    @asyncio.coroutine
    def _on_client_event(self, event_):
        """Receive a ClientEvent and fan out to Conversations."""
        self._sync_timestamp = parsers.from_timestamp(event_.timestamp)
        try:
            conv = self._conv_dict[event_.conversation_id.id_]
        except KeyError:
            logger.warning('Received ClientEvent for unknown conversation {}'
                           .format(event_.conversation_id.id_))
        else:
            conv_event = conv.add_event(event_)
            yield from self.on_event.fire(conv_event)
            yield from conv.on_event.fire(conv_event)

    def _handle_client_conversation(self, client_conversation):
        """Receive ClientConversation and create or update the conversation."""
        conv_id = client_conversation.conversation_id.id_
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            conv.update_conversation(client_conversation)
        else:
            self.add_conversation(client_conversation)

    @asyncio.coroutine
    def _handle_set_typing_notification(self, set_typing_notification):
        """Receive ClientSetTypingNotification and update the conversation."""
        conv_id = set_typing_notification.conversation_id.id_
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            res = parsers.parse_typing_status_message(set_typing_notification)
            yield from self.on_typing.fire(res)
            yield from conv.on_typing.fire(res)
        else:
            logger.warning('Received ClientSetTypingNotification for '
                           'unknown conversation {}'.format(conv_id))

    @asyncio.coroutine
    def _handle_watermark_notification(self, watermark_notification):
        """Receive ClientWatermarkNotification and update the conversation."""
        conv_id = watermark_notification.conversation_id.id_
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            res = parsers.parse_watermark_notification(watermark_notification)
            yield from self.on_watermark_notification.fire(res)
            yield from conv.on_watermark_notification.fire(res)
        else:
            logger.warning('Received ClientWatermarkNotification for '
                           'unknown conversation {}'.format(conv_id))

    @asyncio.coroutine
    def _sync(self, initial_data=None):
        """Sync conversation state and events that could have been missed."""
        logger.info('Syncing events since {}'.format(self._sync_timestamp))
        try:
            res = yield from self._client.syncallnewevents(self._sync_timestamp)
        except exceptions.NetworkError as e:
            logger.warning('Failed to sync events, some events may be lost: {}'
                           .format(e))
        else:
            for conv_state in res.conversation_state:
                conv_id = conv_state.conversation_id.id_
                conv = self._conv_dict.get(conv_id, None)
                if conv is not None:
                    conv.update_conversation(conv_state.conversation)
                    for event_ in conv_state.event:
                        timestamp = parsers.from_timestamp(event_.timestamp)
                        if timestamp > self._sync_timestamp:
                            # This updates the sync_timestamp for us, as well
                            # as triggering events.
                            yield from self._on_client_event(event_)
                else:
                    self.add_conversation(conv_state.conversation,
                                          conv_state.event)
