"""Conversation objects."""

import asyncio
import datetime
import logging
import math

from hangups import (parsers, event, user, conversation_event, exceptions,
                     hangouts_pb2)

logger = logging.getLogger(__name__)

CONVERSATIONS_PER_REQUEST = 100


@asyncio.coroutine
def build_user_conversation_list(client):
    """Build :class:`~UserList` and :class:`~ConversationList`.

    This method requests data necessary to build the list of conversations and
    users. Users that are not in the contact list but are participating in a
    conversation will also be retrieved.

    Args:
        client (Client): Connected client.

    Returns:
        (:class:`~UserList`, :class:`~ConversationList`):
            Tuple of built objects.
    """

    # Retrieve conversations in groups of CONVERSATIONS_PER_REQUEST.
    conv_states = []
    sync_timestamp, next_timestamp = None, None
    last_synced = CONVERSATIONS_PER_REQUEST

    while last_synced == CONVERSATIONS_PER_REQUEST:
        response = (
            yield from client.sync_recent_conversations(
                hangouts_pb2.SyncRecentConversationsRequest(
                    request_header=client.get_request_header(),
                    last_event_timestamp=next_timestamp,
                    max_conversations=CONVERSATIONS_PER_REQUEST,
                    max_events_per_conversation=1,
                    sync_filter=[hangouts_pb2.SYNC_FILTER_INBOX]
                )
            )
        )

        # Add these conversations to the list of states
        response_conv_states = response.conversation_state
        min_timestamp = float('inf')
        for conv_state in response_conv_states:
            conv_event = conv_state.event[0]
            if conv_event.timestamp < min_timestamp:
                min_timestamp = conv_event.timestamp
            conv_states.append(conv_state)

        # Update the number of conversations synced and sync timestamp
        last_synced = len(response_conv_states)
        sync_timestamp = parsers.from_timestamp(
            # SyncRecentConversations seems to return a sync_timestamp 4
            # minutes before the present. To prevent SyncAllNewEvents later
            # breaking requesting events older than what we already have, use
            # current_server_time instead.
            response.response_header.current_server_time
        )

        logger.debug('Added {} conversations'.format(last_synced))

        if math.isfinite(min_timestamp):
            # Start syncing conversations just before this one
            next_timestamp = min_timestamp - 1
        else:
            # No minimum timestamp; abort.
            next_timestamp = 0
            break

    logger.info('Synced {} total conversations'.format(len(conv_states)))

    # Retrieve entities participating in all conversations.
    required_user_ids = set()
    for conv_state in conv_states:
        required_user_ids |= {
            user.UserID(chat_id=part.id.chat_id, gaia_id=part.id.gaia_id)
            for part in conv_state.conversation.participant_data
        }
    required_entities = []
    if required_user_ids:
        logger.debug('Need to request additional users: {}'
                     .format(required_user_ids))
        try:
            response = yield from client.get_entity_by_id(
                hangouts_pb2.GetEntityByIdRequest(
                    request_header=client.get_request_header(),
                    batch_lookup_spec=[
                        hangouts_pb2.EntityLookupSpec(
                            gaia_id=user_id.gaia_id,
                            create_offnetwork_gaia=True,
                        )
                        for user_id in required_user_ids
                    ],
                )
            )
            for entity_result in response.entity_result:
                required_entities.extend(entity_result.entity)
        except exceptions.NetworkError as e:
            logger.warning('Failed to request missing users: {}'.format(e))

    # Build list of conversation participants.
    conv_part_list = []
    for conv_state in conv_states:
        conv_part_list.extend(conv_state.conversation.participant_data)

    # Retrieve self entity.
    get_self_info_response = yield from client.get_self_info(
        hangouts_pb2.GetSelfInfoRequest(
            request_header=client.get_request_header(),
        )
    )
    self_entity = get_self_info_response.self_entity

    user_list = user.UserList(client, self_entity, required_entities,
                              conv_part_list)
    conversation_list = ConversationList(client, conv_states,
                                         user_list, sync_timestamp)
    return (user_list, conversation_list)


class Conversation(object):
    """A single chat conversation.

    Use :class:`ConversationList` methods to get instances of this class.
    """

    def __init__(self, client, user_list, conversation, events=[]):
        # pylint: disable=dangerous-default-value
        self._client = client  # Client
        self._user_list = user_list  # UserList
        self._conversation = conversation  # hangouts_pb2.Conversation
        self._events = []  # [hangouts_pb2.Event]
        self._events_dict = {}  # {event_id: ConversationEvent}
        self._send_message_lock = asyncio.Lock()
        for event_ in events:
            # Workaround to ignore observed events returned from
            # syncrecentconversations.
            if event_.event_type != hangouts_pb2.EVENT_TYPE_OBSERVED_EVENT:
                self.add_event(event_)

        self.on_event = event.Event('Conversation.on_event')
        """
        :class:`~hangups.event.Event` fired when an event occurs in this
        conversation.

        Args:
            conv_event: :class:`ConversationEvent` that occurred.
        """

        self.on_typing = event.Event('Conversation.on_typing')
        """
        :class:`~hangups.event.Event` fired when a users starts or stops typing
        in this conversation.

        Args:
            typing_message: :class:`~hangups.parsers.TypingStatusMessage` that
                occurred.
        """

        self.on_watermark_notification = event.Event(
            'Conversation.on_watermark_notification'
        )
        """
        :class:`~hangups.event.Event` fired when a watermark (read timestamp)
        is updated for this conversation.

        Args:
            watermark_notification:
                :class:`~hangups.parsers.WatermarkNotification` that occurred.
        """

        self.on_watermark_notification.add_observer(
            self._on_watermark_notification
        )

    @property
    def id_(self):
        """The conversation's ID (:class:`str`)."""
        return self._conversation.conversation_id.id

    @property
    def users(self):
        """List of conversation participants (:class:`~hangups.user.User`)."""
        return [self._user_list.get_user(user.UserID(chat_id=part.id.chat_id,
                                                     gaia_id=part.id.gaia_id))
                for part in self._conversation.participant_data]

    @property
    def name(self):
        """The conversation's custom name (:class:`str`)

        May be ``None`` if conversation has no custom name.
        """
        custom_name = self._conversation.name
        return None if custom_name == '' else custom_name

    @property
    def last_modified(self):
        """When conversation was last modified (:class:`datetime.datetime`)."""
        timestamp = self._conversation.self_conversation_state.sort_timestamp
        # timestamp can be None for some reason when there is an ongoing video
        # hangout
        if timestamp is None:
            timestamp = 0
        return parsers.from_timestamp(timestamp)

    @property
    def latest_read_timestamp(self):
        """Timestamp of latest read event (:class:`datetime.datetime`)."""
        timestamp = (self._conversation.self_conversation_state.
                     self_read_state.latest_read_timestamp)
        return parsers.from_timestamp(timestamp)

    @property
    def events(self):
        """Loaded events sorted oldest to newest.

        (list of :class:`ConversationEvent`).
        """
        return list(self._events)

    @property
    def unread_events(self):
        """Loaded events which are unread sorted oldest to newest.

        Some Hangouts clients don't update the read timestamp for certain event
        types, such as membership changes, so this may return more unread
        events than these clients will show. There's also a delay between
        sending a message and the user's own message being considered read.

        (list of :class:`ConversationEvent`).
        """
        return [conv_event for conv_event in self._events
                if conv_event.timestamp > self.latest_read_timestamp]

    @property
    def is_archived(self):
        """``True`` if this conversation has been archived."""
        return (hangouts_pb2.CONVERSATION_VIEW_ARCHIVED in
                self._conversation.self_conversation_state.view)

    @property
    def is_quiet(self):
        """``True`` if notification level for this conversation is quiet."""
        level = self._conversation.self_conversation_state.notification_level
        return level == hangouts_pb2.NOTIFICATION_LEVEL_QUIET

    @property
    def is_off_the_record(self):
        """``True`` if conversation is off the record (history is disabled)."""
        status = self._conversation.otr_status
        return status == hangouts_pb2.OFF_THE_RECORD_STATUS_OFF_THE_RECORD

    def _on_watermark_notification(self, notif):
        """Update the conversations latest_read_timestamp."""
        if self.get_user(notif.user_id).is_self:
            logger.info('latest_read_timestamp for {} updated to {}'
                        .format(self.id_, notif.read_timestamp))
            self_conversation_state = (
                self._conversation.self_conversation_state
            )
            self_conversation_state.self_read_state.latest_read_timestamp = (
                parsers.to_timestamp(notif.read_timestamp)
            )

    def update_conversation(self, conversation):
        """Update the internal state of the conversation.

        This method is used by :class:`ConversationList` to maintain this
        instance.

        Args:
            conversation: ``Conversation`` message.
        """
        # StateUpdate.conversation is actually a delta; fields that aren't
        # specified are assumed to be unchanged. Until this class is
        # refactored, hide this by saving and restoring previous values where
        # necessary.

        # delivery_medium_option
        new_state = conversation.self_conversation_state
        if len(new_state.delivery_medium_option) == 0:
            old_state = self._conversation.self_conversation_state
            new_state.delivery_medium_option.extend(
                old_state.delivery_medium_option
            )

        # latest_read_timestamp
        old_timestamp = self.latest_read_timestamp
        self._conversation = conversation
        if parsers.to_timestamp(self.latest_read_timestamp) == 0:
            self_conversation_state = (
                self._conversation.self_conversation_state
            )
            self_conversation_state.self_read_state.latest_read_timestamp = (
                parsers.to_timestamp(old_timestamp)
            )

    @staticmethod
    def _wrap_event(event_):
        """Wrap hangouts_pb2.Event in ConversationEvent subclass."""
        cls = conversation_event.ConversationEvent
        if event_.HasField('chat_message'):
            cls = conversation_event.ChatMessageEvent
        elif event_.HasField('otr_modification'):
            cls = conversation_event.OTREvent
        elif event_.HasField('conversation_rename'):
            cls = conversation_event.RenameEvent
        elif event_.HasField('membership_change'):
            cls = conversation_event.MembershipChangeEvent
        elif event_.HasField('hangout_event'):
            cls = conversation_event.HangoutEvent
        elif event_.HasField('group_link_sharing_modification'):
            cls = conversation_event.GroupLinkSharingModificationEvent
        return cls(event_)

    def add_event(self, event_):
        """Add an event to the conversation.

        This method is used by :class:`ConversationList` to maintain this
        instance.

        Args:
            event_: ``Event`` message.

        Returns:
            :class:`ConversationEvent` representing the event.
        """
        conv_event = self._wrap_event(event_)
        if conv_event.id_ not in self._events_dict:
            self._events.append(conv_event)
            self._events_dict[conv_event.id_] = conv_event
        else:
            # If this happens, there's probably a bug.
            logger.info('Conversation %s ignoring duplicate event %s',
                        self.id_, conv_event.id_)
            return None
        return conv_event

    def get_user(self, user_id):
        """Get user by its ID.

        Args:
            user_id (~hangups.user.UserID): ID of user to return.

        Raises:
            KeyError: If the user ID is not found.

        Returns:
            :class:`~hangups.user.User` with matching ID.
        """
        return self._user_list.get_user(user_id)

    def _get_default_delivery_medium(self):
        """Return default DeliveryMedium to use for sending messages.

        Use the first option, or an option that's marked as the current
        default.
        """
        medium_options = (
            self._conversation.self_conversation_state.delivery_medium_option
        )
        try:
            default_medium = medium_options[0].delivery_medium
        except IndexError:
            logger.warning('Conversation %r has no delivery medium', self.id_)
            default_medium = hangouts_pb2.DeliveryMedium(
                medium_type=hangouts_pb2.DELIVERY_MEDIUM_BABEL
            )
        for medium_option in medium_options:
            if medium_option.current_default:
                default_medium = medium_option.delivery_medium
        return default_medium

    def _get_event_request_header(self):
        """Return EventRequestHeader for conversation."""
        otr_status = (hangouts_pb2.OFF_THE_RECORD_STATUS_OFF_THE_RECORD
                      if self.is_off_the_record else
                      hangouts_pb2.OFF_THE_RECORD_STATUS_ON_THE_RECORD)
        return hangouts_pb2.EventRequestHeader(
            conversation_id=hangouts_pb2.ConversationId(id=self.id_),
            client_generated_id=self._client.get_client_generated_id(),
            expected_otr=otr_status,
            delivery_medium=self._get_default_delivery_medium(),
        )

    @asyncio.coroutine
    def send_message(self, segments, image_file=None, image_id=None,
                     image_user_id=None):
        """Send a message to this conversation.

        A per-conversation lock is acquired to ensure that messages are sent in
        the correct order when this method is called multiple times
        asynchronously.

        Args:
            segments: List of :class:`ChatMessageSegment` objects to include in
                the message.
            image_file: (optional) File-like object containing an image to be
                attached to the message.
            image_id: (optional) ID of an Picasa photo to be attached to the
                message. If you specify both ``image_file`` and ``image_id``
                together, ``image_file`` takes precedence and ``image_id`` will
                be ignored.
            image_user_id: (optional) Picasa user ID, required only if
                ``image_id`` refers to an image from a different Picasa user,
                such as Google's sticker user.

        Raises:
            NetworkError: If the message cannot be sent.
        """
        with (yield from self._send_message_lock):
            if image_file:
                try:
                    image_id = yield from self._client.upload_image(image_file)
                except exceptions.NetworkError as e:
                    logger.warning('Failed to upload image: {}'.format(e))
                    raise
            try:
                request = hangouts_pb2.SendChatMessageRequest(
                    request_header=self._client.get_request_header(),
                    event_request_header=self._get_event_request_header(),
                    message_content=hangouts_pb2.MessageContent(
                        segment=[seg.serialize() for seg in segments],
                    ),
                )
                if image_id is not None:
                    request.existing_media.photo.photo_id = image_id
                if image_user_id is not None:
                    request.existing_media.photo.user_id = image_user_id
                    request.existing_media.photo.is_custom_user_id = True
                yield from self._client.send_chat_message(request)
            except exceptions.NetworkError as e:
                logger.warning('Failed to send message: {}'.format(e))
                raise

    @asyncio.coroutine
    def leave(self):
        """Leave this conversation.

        Raises:
            NetworkError: If conversation cannot be left.
        """
        is_group_conversation = (self._conversation.type ==
                                 hangouts_pb2.CONVERSATION_TYPE_GROUP)
        try:
            if is_group_conversation:
                yield from self._client.remove_user(
                    hangouts_pb2.RemoveUserRequest(
                        request_header=self._client.get_request_header(),
                        event_request_header=self._get_event_request_header(),
                    )
                )
            else:
                yield from self._client.delete_conversation(
                    hangouts_pb2.DeleteConversationRequest(
                        request_header=self._client.get_request_header(),
                        conversation_id=hangouts_pb2.ConversationId(
                            id=self.id_
                        ),
                        delete_upper_bound_timestamp=parsers.to_timestamp(
                            datetime.datetime.now(tz=datetime.timezone.utc)
                        )
                    )
                )
        except exceptions.NetworkError as e:
            logger.warning('Failed to leave conversation: {}'.format(e))
            raise

    @asyncio.coroutine
    def rename(self, name):
        """Rename this conversation.

        Hangouts only officially supports renaming group conversations, so
        custom names for one-to-one conversations may or may not appear in all
        first party clients.

        Args:
            name (str): New name.

        Raises:
            NetworkError: If conversation cannot be renamed.
        """
        yield from self._client.rename_conversation(
            hangouts_pb2.RenameConversationRequest(
                request_header=self._client.get_request_header(),
                new_name=name,
                event_request_header=self._get_event_request_header(),
            )
        )

    @asyncio.coroutine
    def set_notification_level(self, level):
        """Set the notification level of this conversation.

        Args:
            level: ``NOTIFICATION_LEVEL_QUIET`` to disable notifications, or
                ``NOTIFICATION_LEVEL_RING`` to enable them.

        Raises:
            NetworkError: If the request fails.
        """
        yield from self._client.set_conversation_notification_level(
            hangouts_pb2.SetConversationNotificationLevelRequest(
                request_header=self._client.get_request_header(),
                conversation_id=hangouts_pb2.ConversationId(id=self.id_),
                level=level,
            )
        )

    @asyncio.coroutine
    def set_typing(self, typing=hangouts_pb2.TYPING_TYPE_STARTED):
        """Set your typing status in this conversation.

        Args:
            typing: (optional) ``TYPING_TYPE_STARTED``, ``TYPING_TYPE_PAUSED``,
                or ``TYPING_TYPE_STOPPED`` to start, pause, or stop typing,
                respectively. Defaults to ``TYPING_TYPE_STARTED``.

        Raises:
            NetworkError: If typing status cannot be set.
        """
        # TODO: Add rate-limiting to avoid unnecessary requests.
        try:
            yield from self._client.set_typing(
                hangouts_pb2.SetTypingRequest(
                    request_header=self._client.get_request_header(),
                    conversation_id=hangouts_pb2.ConversationId(id=self.id_),
                    type=typing,
                )
            )
        except exceptions.NetworkError as e:
            logger.warning('Failed to set typing status: {}'.format(e))
            raise

    @asyncio.coroutine
    def update_read_timestamp(self, read_timestamp=None):
        """Update the timestamp of the latest event which has been read.

        This method will avoid making an API request if it will have no effect.

        Args:
            read_timestamp (datetime.datetime): (optional) Timestamp to set.
                Defaults to the timestamp of the newest event.

        Raises:
            NetworkError: If the timestamp cannot be updated.
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
                yield from self._client.update_watermark(
                    hangouts_pb2.UpdateWatermarkRequest(
                        request_header=self._client.get_request_header(),
                        conversation_id=hangouts_pb2.ConversationId(
                            id=self.id_
                        ),
                        last_read_timestamp=parsers.to_timestamp(
                            read_timestamp
                        ),
                    )
                )
            except exceptions.NetworkError as e:
                logger.warning('Failed to update read timestamp: {}'.format(e))
                raise

    @asyncio.coroutine
    def get_events(self, event_id=None, max_events=50):
        """Get events from this conversation.

        Makes a request to load historical events if necessary.

        Args:
            event_id (str): (optional) If provided, return events preceding
                this event, otherwise return the newest events.
            max_events (int): Maximum number of events to return. Defaults to
                50.

        Returns:
            List of :class:`ConversationEvent` instances, ordered newest-first.

        Raises:
            KeyError: If ``event_id`` does not correspond to a known event.
            NetworkError: If the events could not be requested.
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
                res = yield from self._client.get_conversation(
                    hangouts_pb2.GetConversationRequest(
                        request_header=self._client.get_request_header(),
                        conversation_spec=hangouts_pb2.ConversationSpec(
                            conversation_id=hangouts_pb2.ConversationId(
                                id=self.id_
                            )
                        ),
                        include_event=True,
                        max_events_per_conversation=max_events,
                        event_continuation_token=(
                            hangouts_pb2.EventContinuationToken(
                                event_timestamp=parsers.to_timestamp(
                                    conv_event.timestamp
                                )
                            )
                        )
                    )
                )
                conv_events = [self._wrap_event(event) for event
                               in res.conversation_state.event]
                logger.info('Loaded {} events for conversation {}'
                            .format(len(conv_events), self.id_))
                # Iterate though the events newest to oldest.
                for conv_event in reversed(conv_events):
                    # Add event as the new oldest event, unless we already have
                    # it.
                    if conv_event.id_ not in self._events_dict:
                        self._events.insert(0, conv_event)
                        self._events_dict[conv_event.id_] = conv_event
                    else:
                        # If this happens, there's probably a bug.
                        logger.info(
                            'Conversation %s ignoring duplicate event %s',
                            self.id_, conv_event.id_
                        )
        return conv_events

    def next_event(self, event_id, prev=False):
        """Get the event following another event in this conversation.

        Args:
            event_id (str): ID of the event.
            prev (bool): If ``True``, return the previous event rather than the
                next event. Defaults to ``False``.

        Raises:
            KeyError: If no such :class:`ConversationEvent` is known.

        Returns:
            :class:`ConversationEvent` or ``None`` if there is no following
            event.
        """
        i = self.events.index(self._events_dict[event_id])
        if prev and i > 0:
            return self.events[i - 1]
        elif not prev and i + 1 < len(self.events):
            return self.events[i + 1]
        else:
            return None

    def get_event(self, event_id):
        """Get an event in this conversation by its ID.

        Args:
            event_id (str): ID of the event.

        Raises:
            KeyError: If no such :class:`ConversationEvent` is known.

        Returns:
            :class:`ConversationEvent` with the given ID.
        """
        return self._events_dict[event_id]


class ConversationList(object):
    """Maintains a list of the user's conversations.

    Using :func:`build_user_conversation_list` to initialize this class is
    recommended.

    Args:
        client: The connected :class:`Client`.
        conv_states: List of ``ConversationState`` messages used to initialize
            the list of conversations.
        user_list: :class:`UserList` object.
        sync_timestamp (datetime.datetime): The time when ``conv_states`` was
            synced.
    """

    def __init__(self, client, conv_states, user_list, sync_timestamp):
        self._client = client  # Client
        self._conv_dict = {}  # {conv_id: Conversation}
        self._sync_timestamp = sync_timestamp  # datetime
        self._user_list = user_list  # UserList

        # Initialize the list of conversations from Client's list of
        # hangouts_pb2.ConversationState.
        for conv_state in conv_states:
            self._add_conversation(conv_state.conversation, conv_state.event)

        self._client.on_state_update.add_observer(self._on_state_update)
        self._client.on_connect.add_observer(self._sync)
        self._client.on_reconnect.add_observer(self._sync)

        self.on_event = event.Event('ConversationList.on_event')
        """
        :class:`~hangups.event.Event` fired when an event occurs in any
        conversation.

        Args:
            conv_event: :class:`ConversationEvent` that occurred.
        """

        self.on_typing = event.Event('ConversationList.on_typing')
        """
        :class:`~hangups.event.Event` fired when a users starts or stops typing
        in any conversation.

        Args:
            typing_message: :class:`~hangups.parsers.TypingStatusMessage` that
                occurred.
        """

        self.on_watermark_notification = event.Event(
            'ConversationList.on_watermark_notification'
        )
        """
        :class:`~hangups.event.Event` fired when a watermark (read timestamp)
        is updated for any conversation.

        Args:
            watermark_notification:
                :class:`~hangups.parsers.WatermarkNotification` that occurred.
        """

    def get_all(self, include_archived=False):
        """Get all the conversations.

        Args:
            include_archived (bool): (optional) Whether to include archived
                conversations. Defaults to ``False``.

        Returns:
            List of all :class:`.Conversation` objects.
        """
        return [conv for conv in self._conv_dict.values()
                if not conv.is_archived or include_archived]

    def get(self, conv_id):
        """Get a conversation by its ID.

        Args:
            conv_id (str): ID of conversation to return.

        Raises:
            KeyError: If the conversation ID is not found.

        Returns:
            :class:`.Conversation` with matching ID.
        """
        return self._conv_dict[conv_id]

    @asyncio.coroutine
    def leave_conversation(self, conv_id):
        """Leave a conversation.

        Args:
            conv_id (str): ID of conversation to leave.
        """
        logger.info('Leaving conversation: {}'.format(conv_id))
        yield from self._conv_dict[conv_id].leave()
        del self._conv_dict[conv_id]

    def _add_conversation(self, conversation, events=[]):
        """Add new conversation from hangouts_pb2.Conversation"""
        # pylint: disable=dangerous-default-value
        conv_id = conversation.conversation_id.id
        logger.info('Adding new conversation: {}'.format(conv_id))
        conv = Conversation(self._client, self._user_list, conversation,
                            events)
        self._conv_dict[conv_id] = conv
        return conv

    @asyncio.coroutine
    def _on_state_update(self, state_update):
        """Receive a StateUpdate and fan out to Conversations."""
        # Handle updating a conversation
        if state_update.HasField('conversation'):
            self._handle_conversation(state_update.conversation)
        # Handle the notification
        notification_type = state_update.WhichOneof('state_update')
        if notification_type == 'typing_notification':
            yield from self._handle_set_typing_notification(
                state_update.typing_notification
            )
        elif notification_type == 'watermark_notification':
            yield from self._handle_watermark_notification(
                state_update.watermark_notification
            )
        elif notification_type == 'event_notification':
            yield from self._on_event(
                state_update.event_notification.event
            )

    @asyncio.coroutine
    def _on_event(self, event_):
        """Receive a hangouts_pb2.Event and fan out to Conversations."""
        self._sync_timestamp = parsers.from_timestamp(event_.timestamp)
        try:
            conv = self._conv_dict[event_.conversation_id.id]
        except KeyError:
            logger.warning('Received Event for unknown conversation {}'
                           .format(event_.conversation_id.id))
        else:
            conv_event = conv.add_event(event_)
            # conv_event may be None if the event was a duplicate.
            if conv_event is not None:
                yield from self.on_event.fire(conv_event)
                yield from conv.on_event.fire(conv_event)

    def _handle_conversation(self, conversation):
        """Receive Conversation and create or update the conversation."""
        conv_id = conversation.conversation_id.id
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            conv.update_conversation(conversation)
        else:
            self._add_conversation(conversation)

    @asyncio.coroutine
    def _handle_set_typing_notification(self, set_typing_notification):
        """Receive SetTypingNotification and update the conversation."""
        conv_id = set_typing_notification.conversation_id.id
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            res = parsers.parse_typing_status_message(set_typing_notification)
            yield from self.on_typing.fire(res)
            yield from conv.on_typing.fire(res)
        else:
            logger.warning('Received SetTypingNotification for '
                           'unknown conversation {}'.format(conv_id))

    @asyncio.coroutine
    def _handle_watermark_notification(self, watermark_notification):
        """Receive WatermarkNotification and update the conversation."""
        conv_id = watermark_notification.conversation_id.id
        conv = self._conv_dict.get(conv_id, None)
        if conv is not None:
            res = parsers.parse_watermark_notification(watermark_notification)
            yield from self.on_watermark_notification.fire(res)
            yield from conv.on_watermark_notification.fire(res)
        else:
            logger.warning('Received WatermarkNotification for '
                           'unknown conversation {}'.format(conv_id))

    @asyncio.coroutine
    def _sync(self):
        """Sync conversation state and events that could have been missed."""
        logger.info('Syncing events since {}'.format(self._sync_timestamp))
        try:
            res = yield from self._client.sync_all_new_events(
                hangouts_pb2.SyncAllNewEventsRequest(
                    request_header=self._client.get_request_header(),
                    last_sync_timestamp=parsers.to_timestamp(
                        self._sync_timestamp
                    ),
                    max_response_size_bytes=1048576,  # 1 MB
                )
            )
        except exceptions.NetworkError as e:
            logger.warning('Failed to sync events, some events may be lost: {}'
                           .format(e))
        else:
            for conv_state in res.conversation_state:
                conv_id = conv_state.conversation_id.id
                conv = self._conv_dict.get(conv_id, None)
                if conv is not None:
                    conv.update_conversation(conv_state.conversation)
                    for event_ in conv_state.event:
                        timestamp = parsers.from_timestamp(event_.timestamp)
                        if timestamp > self._sync_timestamp:
                            # This updates the sync_timestamp for us, as well
                            # as triggering events.
                            yield from self._on_event(event_)
                else:
                    self._add_conversation(conv_state.conversation,
                                           conv_state.event)
