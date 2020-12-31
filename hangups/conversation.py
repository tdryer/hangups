"""Conversation objects."""

import asyncio
import datetime
import logging

from hangups import (parsers, event, user, conversation_event, exceptions,
                     hangouts_pb2)

logger = logging.getLogger(__name__)

CONVERSATIONS_PER_REQUEST = 100
MAX_CONVERSATION_PAGES = 100


async def build_user_conversation_list(client):
    """Build :class:`.UserList` and :class:`.ConversationList`.

    This method requests data necessary to build the list of conversations and
    users. Users that are not in the contact list but are participating in a
    conversation will also be retrieved.

    Args:
        client (Client): Connected client.

    Returns:
        (:class:`.UserList`, :class:`.ConversationList`):
            Tuple of built objects.
    """
    conv_states, sync_timestamp = await _sync_all_conversations(client)

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
            response = await client.get_entity_by_id(
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
    get_self_info_response = await client.get_self_info(
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


async def _sync_all_conversations(client):
    """Sync all conversations by making paginated requests.

    Conversations are ordered by ascending sort timestamp.

    Args:
        client (Client): Connected client.

    Raises:
        NetworkError: If the requests fail.

    Returns:
        tuple of list of ``ConversationState`` messages and sync timestamp
    """
    conv_states = []
    sync_timestamp = None
    request = hangouts_pb2.SyncRecentConversationsRequest(
        request_header=client.get_request_header(),
        max_conversations=CONVERSATIONS_PER_REQUEST,
        max_events_per_conversation=1,
        sync_filter=[
            hangouts_pb2.SYNC_FILTER_INBOX,
            hangouts_pb2.SYNC_FILTER_ARCHIVED,
        ]
    )
    for _ in range(MAX_CONVERSATION_PAGES):
        logger.info(
            'Requesting conversations page %s', request.last_event_timestamp
        )
        response = await client.sync_recent_conversations(request)
        conv_states = list(response.conversation_state) + conv_states
        sync_timestamp = parsers.from_timestamp(
            # SyncRecentConversations seems to return a sync_timestamp 4
            # minutes before the present. To prevent SyncAllNewEvents later
            # breaking requesting events older than what we already have, use
            # current_server_time instead.
            response.response_header.current_server_time
        )
        if response.continuation_end_timestamp == 0:
            logger.info('Reached final conversations page')
            break
        else:
            request.last_event_timestamp = response.continuation_end_timestamp
    else:
        logger.warning('Exceeded maximum number of conversation pages')
    logger.info('Synced %s total conversations', len(conv_states))
    return conv_states, sync_timestamp


class Conversation:
    """A single chat conversation.

    Use :class:`.ConversationList` methods to get instances of this class.
    """

    def __init__(self, client, user_list, conversation, events=[],
                 event_cont_token=None):
        # pylint: disable=dangerous-default-value
        self._client = client  # Client
        self._user_list = user_list  # UserList
        self._conversation = conversation  # hangouts_pb2.Conversation
        self._events = []  # [hangouts_pb2.Event]
        self._events_dict = {}  # {event_id: ConversationEvent}
        self._send_message_lock = asyncio.Lock()
        self._watermarks = {}  # {UserID: datetime.datetime}
        self._event_cont_token = event_cont_token
        for event_ in events:
            # Workaround to ignore observed events returned from
            # syncrecentconversations.
            if event_.event_type != hangouts_pb2.EVENT_TYPE_OBSERVED_EVENT:
                self.add_event(event_)

        self.on_event = event.Event('Conversation.on_event')
        """
        :class:`.Event` fired when an event occurs in this conversation.

        Args:
            conv_event: :class:`.ConversationEvent` that occurred.
        """

        self.on_typing = event.Event('Conversation.on_typing')
        """
        :class:`.Event` fired when a users starts or stops typing in this
        conversation.

        Args:
            typing_message: :class:`~hangups.parsers.TypingStatusMessage` that
                occurred.
        """

        self.on_watermark_notification = event.Event(
            'Conversation.on_watermark_notification'
        )
        """
        :class:`.Event` fired when a watermark (read timestamp) is updated for
        this conversation.

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

        (list of :class:`.ConversationEvent`).
        """
        return list(self._events)

    @property
    def watermarks(self):
        """Participant watermarks.

        (dict of :class:`.UserID`, :class:`datetime.datetime`).
        """
        return self._watermarks.copy()

    @property
    def unread_events(self):
        """Loaded events which are unread sorted oldest to newest.

        Some Hangouts clients don't update the read timestamp for certain event
        types, such as membership changes, so this may return more unread
        events than these clients will show. There's also a delay between
        sending a message and the user's own message being considered read.

        (list of :class:`.ConversationEvent`).
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

    @property
    def is_group_link_sharing_enabled(self):
        """``True`` if group link sharing (joining by link) is enabled."""
        if not self._conversation.type == hangouts_pb2.CONVERSATION_TYPE_GROUP:
            return False
        status = self._conversation.group_link_sharing_status
        return status == hangouts_pb2.GROUP_LINK_SHARING_STATUS_ON

    def _on_watermark_notification(self, notif):
        """Handle a watermark notification."""
        # Update the conversation:
        if self.get_user(notif.user_id).is_self:
            logger.info('latest_read_timestamp for {} updated to {}'
                        .format(self.id_, notif.read_timestamp))
            self_conversation_state = (
                self._conversation.self_conversation_state
            )
            self_conversation_state.self_read_state.latest_read_timestamp = (
                parsers.to_timestamp(notif.read_timestamp)
            )
        # Update the participants' watermarks:
        previous_timestamp = self._watermarks.get(
            notif.user_id,
            datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
        )
        if notif.read_timestamp > previous_timestamp:
            logger.info(('latest_read_timestamp for conv {} participant {}' +
                         ' updated to {}').format(self.id_,
                                                  notif.user_id.chat_id,
                                                  notif.read_timestamp))
            self._watermarks[notif.user_id] = notif.read_timestamp

    def update_conversation(self, conversation):
        """Update the internal state of the conversation.

        This method is used by :class:`.ConversationList` to maintain this
        instance.

        Args:
            conversation: ``Conversation`` message.
        """
        # StateUpdate.conversation is actually a delta; fields that aren't
        # specified are assumed to be unchanged. Until this class is
        # refactored, hide this by saving and restoring previous values where
        # necessary.

        new_state = conversation.self_conversation_state
        old_state = self._conversation.self_conversation_state
        self._conversation = conversation

        # delivery_medium_option
        if not new_state.delivery_medium_option:
            new_state.delivery_medium_option.extend(
                old_state.delivery_medium_option
            )

        # latest_read_timestamp
        old_timestamp = old_state.self_read_state.latest_read_timestamp
        new_timestamp = new_state.self_read_state.latest_read_timestamp
        if new_timestamp == 0:
            new_state.self_read_state.latest_read_timestamp = old_timestamp

        # user_read_state(s)
        for new_entry in conversation.read_state:
            tstamp = parsers.from_timestamp(new_entry.latest_read_timestamp)
            if tstamp == 0:
                continue
            uid = parsers.from_participantid(new_entry.participant_id)
            if uid not in self._watermarks or self._watermarks[uid] < tstamp:
                self._watermarks[uid] = tstamp

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

        This method is used by :class:`.ConversationList` to maintain this
        instance.

        Args:
            event_: ``Event`` message.

        Returns:
            :class:`.ConversationEvent` representing the event.
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

    async def send_message(self, segments, image_file=None, image_id=None,
                           image_user_id=None):
        """Send a message to this conversation.

        A per-conversation lock is acquired to ensure that messages are sent in
        the correct order when this method is called multiple times
        asynchronously.

        Args:
            segments: List of :class:`.ChatMessageSegment` objects to include
                in the message.
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
            .NetworkError: If the message cannot be sent.

        Returns:
            :class:`.ConversationEvent` representing the new message.
        """
        async with self._send_message_lock:
            if image_file:
                try:
                    uploaded_image = await self._client.upload_image(
                        image_file, return_uploaded_image=True
                    )
                except exceptions.NetworkError as e:
                    logger.warning('Failed to upload image: {}'.format(e))
                    raise
                image_id = uploaded_image.image_id
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
                response = await self._client.send_chat_message(request)
                return self._wrap_event(response.created_event)
            except exceptions.NetworkError as e:
                logger.warning('Failed to send message: {}'.format(e))
                raise

    @staticmethod
    def _wrap_user_id(id_):
        """Convert a user ID into a hangouts_pb2.InviteeID object."""
        if isinstance(id_, hangouts_pb2.InviteeID):
            return id_
        elif isinstance(id_, user.UserID):
            return hangouts_pb2.InviteeID(gaia_id=id_.gaia_id)
        else:
            return hangouts_pb2.InviteeID(gaia_id=id_)

    @staticmethod
    def _wrap_participant_id(id_):
        """Convert a user ID into a hangouts_pb2.ParticipantId object."""
        if isinstance(id_, hangouts_pb2.ParticipantId):
            return id_
        elif isinstance(id_, user.UserID):
            return hangouts_pb2.ParticipantId(gaia_id=id_.gaia_id)
        else:
            return hangouts_pb2.ParticipantId(gaia_id=id_)

    async def add_users(self, user_ids):
        """Add one or more users to this conversation.

        Args:
            user_ids: List of IDs of the new users to be added; accepts
                :class:`.UserID`, ``InviteeID`` or just :class:`str` IDs.

        Raises:
            .ConversationTypeError: If conversation is not a group.
            .NetworkError: If conversation cannot be invited to.

        Returns:
            :class:`.ConversationEvent` representing the change.
        """
        if not self._conversation.type == hangouts_pb2.CONVERSATION_TYPE_GROUP:
            raise exceptions.ConversationTypeError(
                'Can only add users to group conversations'
            )
        try:
            response = await self._client.add_user(
                hangouts_pb2.AddUserRequest(
                    request_header=self._client.get_request_header(),
                    event_request_header=self._get_event_request_header(),
                    invitee_id=[self._wrap_user_id(user_id)
                                for user_id in user_ids],
                )
            )
            return self._wrap_event(response.created_event)
        except exceptions.NetworkError as e:
            logger.warning('Failed to add user: {}'.format(e))
            raise

    async def remove_user(self, user_id):
        """Remove a user from this conversation.

        Args:
            user_id: ID of the user to be removed; accepts :class:`.UserID`,
                ``ParticipantId`` or just :class:`str` IDs.

        Raises:
            .ConversationTypeError: If conversation is not a group.
            .NetworkError: If conversation cannot be removed from.

        Returns:
            :class:`.ConversationEvent` representing the change.
        """
        if not self._conversation.type == hangouts_pb2.CONVERSATION_TYPE_GROUP:
            raise exceptions.ConversationTypeError(
                'Can only remove users to group conversations'
            )
        try:
            response = await self._client.remove_user(
                hangouts_pb2.RemoveUserRequest(
                    request_header=self._client.get_request_header(),
                    event_request_header=self._get_event_request_header(),
                    participant_id=self._wrap_participant_id(user_id),
                )
            )
            return self._wrap_event(response.created_event)
        except exceptions.NetworkError as e:
            logger.warning('Failed to remove user: {}'.format(e))
            raise

    async def leave(self):
        """Leave this conversation.

        Raises:
            .NetworkError: If conversation cannot be left.
        """
        is_group_conversation = (self._conversation.type ==
                                 hangouts_pb2.CONVERSATION_TYPE_GROUP)
        try:
            if is_group_conversation:
                await self._client.remove_user(
                    hangouts_pb2.RemoveUserRequest(
                        request_header=self._client.get_request_header(),
                        event_request_header=self._get_event_request_header(),
                    )
                )
            else:
                await self._client.delete_conversation(
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

    async def rename(self, name):
        """Rename this conversation.

        Hangouts only officially supports renaming group conversations, so
        custom names for one-to-one conversations may or may not appear in all
        first party clients.

        Args:
            name (str): New name.

        Raises:
            .NetworkError: If conversation cannot be renamed.
        """
        await self._client.rename_conversation(
            hangouts_pb2.RenameConversationRequest(
                request_header=self._client.get_request_header(),
                new_name=name,
                event_request_header=self._get_event_request_header(),
            )
        )

    async def set_notification_level(self, level):
        """Set the notification level of this conversation.

        Args:
            level: ``NOTIFICATION_LEVEL_QUIET`` to disable notifications, or
                ``NOTIFICATION_LEVEL_RING`` to enable them.

        Raises:
            .NetworkError: If the request fails.
        """
        await self._client.set_conversation_notification_level(
            hangouts_pb2.SetConversationNotificationLevelRequest(
                request_header=self._client.get_request_header(),
                conversation_id=hangouts_pb2.ConversationId(id=self.id_),
                level=level,
            )
        )

    async def modify_otr_status(self, off_record):
        """Set the OTR mode of this conversation.

        Args:
            off_record: ``True`` to disable history, or ``False`` to enable it.

        Raises:
            .NetworkError: If the request fails.

        Returns:
            :class:`.ConversationEvent` representing the change.
        """
        if off_record:
            status = hangouts_pb2.OFF_THE_RECORD_STATUS_OFF_THE_RECORD
        else:
            status = hangouts_pb2.OFF_THE_RECORD_STATUS_ON_THE_RECORD
        try:
            response = await self._client.modify_otr_status(
                hangouts_pb2.ModifyOTRStatusRequest(
                    request_header=self._client.get_request_header(),
                    otr_status=status,
                    event_request_header=self._get_event_request_header(),
                )
            )
            return self._wrap_event(response.created_event)
        except exceptions.NetworkError as e:
            logger.warning('Failed to set OTR mode: {}'.format(e))
            raise

    async def set_group_link_sharing_enabled(self, enabled):
        """Set the link sharing mode of this conversation.

        Args:
            enabled: ``True`` to allow joining the conversation by link, or
                ``False`` to prevent it.

        Raises:
            .ConversationTypeError: If conversation is not a group.
            .NetworkError: If the request fails.

        Returns:
            :class:`.ConversationEvent` representing the change.
        """
        if not self._conversation.type == hangouts_pb2.CONVERSATION_TYPE_GROUP:
            raise exceptions.ConversationTypeError(
                'Can only set link sharing in group conversations'
            )
        if enabled:
            status = hangouts_pb2.GROUP_LINK_SHARING_STATUS_ON
        else:
            status = hangouts_pb2.GROUP_LINK_SHARING_STATUS_OFF
        try:
            response = await self._client.set_group_link_sharing_enabled(
                hangouts_pb2.SetGroupLinkSharingEnabledRequest(
                    request_header=self._client.get_request_header(),
                    group_link_sharing_status=status,
                    event_request_header=self._get_event_request_header(),
                )
            )
            return self._wrap_event(response.created_event)
        except exceptions.NetworkError as e:
            logger.warning('Failed to set link sharing mode: {}'.format(e))
            raise

    async def set_typing(self, typing=hangouts_pb2.TYPING_TYPE_STARTED):
        """Set your typing status in this conversation.

        Args:
            typing: (optional) ``TYPING_TYPE_STARTED``, ``TYPING_TYPE_PAUSED``,
                or ``TYPING_TYPE_STOPPED`` to start, pause, or stop typing,
                respectively. Defaults to ``TYPING_TYPE_STARTED``.

        Raises:
            .NetworkError: If typing status cannot be set.
        """
        # TODO: Add rate-limiting to avoid unnecessary requests.
        try:
            await self._client.set_typing(
                hangouts_pb2.SetTypingRequest(
                    request_header=self._client.get_request_header(),
                    conversation_id=hangouts_pb2.ConversationId(id=self.id_),
                    type=typing,
                )
            )
        except exceptions.NetworkError as e:
            logger.warning('Failed to set typing status: {}'.format(e))
            raise

    async def update_read_timestamp(self, read_timestamp=None):
        """Update the timestamp of the latest event which has been read.

        This method will avoid making an API request if it will have no effect.

        Args:
            read_timestamp (datetime.datetime): (optional) Timestamp to set.
                Defaults to the timestamp of the newest event.

        Raises:
            .NetworkError: If the timestamp cannot be updated.
        """
        if read_timestamp is None:
            read_timestamp = (self.events[-1].timestamp if self.events else
                              datetime.datetime.now(datetime.timezone.utc))
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
                await self._client.update_watermark(
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

    async def get_events(self, event_id=None, max_events=50):
        """Get events from this conversation.

        Makes a request to load historical events if necessary.

        Args:
            event_id (str): (optional) If provided, return events preceding
                this event, otherwise return the newest events.
            max_events (int): Maximum number of events to return. Defaults to
                50.

        Returns:
            List of :class:`.ConversationEvent` instances, ordered
            oldest-first.

        Raises:
            KeyError: If ``event_id`` does not correspond to a known event.
            .NetworkError: If the events could not be requested.
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
                # Return at most max_events events preceding the event at this
                # index.
                index = self._events.index(conv_event)
                conv_events = self._events[max(index - max_events, 0):index]
            else:
                logger.info('Loading events for conversation {} before {}'
                            .format(self.id_, conv_event.timestamp))
                res = await self._client.get_conversation(
                    hangouts_pb2.GetConversationRequest(
                        request_header=self._client.get_request_header(),
                        conversation_spec=hangouts_pb2.ConversationSpec(
                            conversation_id=hangouts_pb2.ConversationId(
                                id=self.id_
                            )
                        ),
                        include_event=True,
                        max_events_per_conversation=max_events,
                        event_continuation_token=self._event_cont_token
                    )
                )
                # Certain fields of conversation_state are not populated by
                # SyncRecentConversations. This is the case with the
                # user_read_state fields which are all set to 0 but for the
                # 'self' user. Update here so these fields get populated on the
                # first call to GetConversation.
                if res.conversation_state.HasField('conversation'):
                    self.update_conversation(
                        res.conversation_state.conversation
                    )
                self._event_cont_token = (
                    res.conversation_state.event_continuation_token
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
            KeyError: If no such :class:`.ConversationEvent` is known.

        Returns:
            :class:`.ConversationEvent` or ``None`` if there is no following
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
            KeyError: If no such :class:`.ConversationEvent` is known.

        Returns:
            :class:`.ConversationEvent` with the given ID.
        """
        return self._events_dict[event_id]


class ConversationList:
    """Maintains a list of the user's conversations.

    Using :func:`build_user_conversation_list` to initialize this class is
    recommended.

    Args:
        client: The connected :class:`Client`.
        conv_states: List of ``ConversationState`` messages used to initialize
            the list of conversations.
        user_list: :class:`.UserList` object.
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
            self._add_conversation(conv_state.conversation, conv_state.event,
                                   conv_state.event_continuation_token)

        self._client.on_state_update.add_observer(self._on_state_update)
        self._client.on_connect.add_observer(self._sync)
        self._client.on_reconnect.add_observer(self._sync)

        self.on_event = event.Event('ConversationList.on_event')
        """
        :class:`.Event` fired when an event occurs in any conversation.

        Args:
            conv_event: :class:`ConversationEvent` that occurred.
        """

        self.on_typing = event.Event('ConversationList.on_typing')
        """
        :class:`.Event` fired when a users starts or stops typing in any
        conversation.

        Args:
            typing_message: :class:`~hangups.parsers.TypingStatusMessage` that
                occurred.
        """

        self.on_watermark_notification = event.Event(
            'ConversationList.on_watermark_notification'
        )
        """
        :class:`.Event` fired when a watermark (read timestamp) is updated for
        any conversation.

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

    async def leave_conversation(self, conv_id):
        """Leave a conversation.

        Args:
            conv_id (str): ID of conversation to leave.
        """
        logger.info('Leaving conversation: {}'.format(conv_id))
        await self._conv_dict[conv_id].leave()
        del self._conv_dict[conv_id]

    def _add_conversation(self, conversation, events=[],
                          event_cont_token=None):
        """Add new conversation from hangouts_pb2.Conversation"""
        # pylint: disable=dangerous-default-value
        conv_id = conversation.conversation_id.id
        logger.debug('Adding new conversation: {}'.format(conv_id))
        conv = Conversation(self._client, self._user_list, conversation,
                            events, event_cont_token)
        self._conv_dict[conv_id] = conv
        return conv

    async def _on_state_update(self, state_update):
        """Receive a StateUpdate and fan out to Conversations.

        Args:
            state_update: hangouts_pb2.StateUpdate instance
        """
        # The state update will include some type of notification:
        notification_type = state_update.WhichOneof('state_update')

        # If conversation fields have been updated, the state update will have
        # a conversation containing changed fields. Handle updating the
        # conversation from this delta:
        if state_update.HasField('conversation'):
            try:
                await self._handle_conversation_delta(
                    state_update.conversation
                )
            except exceptions.NetworkError:
                logger.warning(
                    'Discarding %s for %s: Failed to fetch conversation',
                    notification_type.replace('_', ' '),
                    state_update.conversation.conversation_id.id
                )
                return

        if notification_type == 'typing_notification':
            await self._handle_set_typing_notification(
                state_update.typing_notification
            )
        elif notification_type == 'watermark_notification':
            await self._handle_watermark_notification(
                state_update.watermark_notification
            )
        elif notification_type == 'event_notification':
            await self._on_event(
                state_update.event_notification.event
            )

    async def _get_or_fetch_conversation(self, conv_id):
        """Get a cached conversation or fetch a missing conversation.

        Args:
            conv_id: string, conversation identifier

        Raises:
            NetworkError: If the request to fetch the conversation fails.

        Returns:
            :class:`.Conversation` with matching ID.
        """
        conv = self._conv_dict.get(conv_id, None)
        if conv is None:
            logger.info('Fetching unknown conversation %s', conv_id)
            res = await self._client.get_conversation(
                hangouts_pb2.GetConversationRequest(
                    request_header=self._client.get_request_header(),
                    conversation_spec=hangouts_pb2.ConversationSpec(
                        conversation_id=hangouts_pb2.ConversationId(
                            id=conv_id
                        )
                    ), include_event=False
                )
            )
            conv_state = res.conversation_state
            event_cont_token = None
            if conv_state.HasField('event_continuation_token'):
                event_cont_token = conv_state.event_continuation_token
            return self._add_conversation(conv_state.conversation,
                                          event_cont_token=event_cont_token)
        else:
            return conv

    async def _on_event(self, event_):
        """Receive a hangouts_pb2.Event and fan out to Conversations.

        Args:
            event_: hangouts_pb2.Event instance
        """
        conv_id = event_.conversation_id.id
        try:
            conv = await self._get_or_fetch_conversation(conv_id)
        except exceptions.NetworkError:
            logger.warning(
                'Failed to fetch conversation for event notification: %s',
                conv_id
            )
        else:
            self._sync_timestamp = parsers.from_timestamp(event_.timestamp)
            conv_event = conv.add_event(event_)
            # conv_event may be None if the event was a duplicate.
            if conv_event is not None:
                await self.on_event.fire(conv_event)
                await conv.on_event.fire(conv_event)

    async def _handle_conversation_delta(self, conversation):
        """Receive Conversation delta and create or update the conversation.

        Args:
            conversation: hangouts_pb2.Conversation instance

        Raises:
            NetworkError: A request to fetch the complete conversation failed.
        """
        conv_id = conversation.conversation_id.id
        conv = self._conv_dict.get(conv_id, None)
        if conv is None:
            # Ignore the delta and fetch the complete conversation.
            await self._get_or_fetch_conversation(conv_id)
        else:
            # Update conversation using the delta.
            conv.update_conversation(conversation)

    async def _handle_set_typing_notification(self, set_typing_notification):
        """Receive SetTypingNotification and update the conversation.

        Args:
            set_typing_notification: hangouts_pb2.SetTypingNotification
                instance
        """
        conv_id = set_typing_notification.conversation_id.id
        res = parsers.parse_typing_status_message(set_typing_notification)
        await self.on_typing.fire(res)
        try:
            conv = await self._get_or_fetch_conversation(conv_id)
        except exceptions.NetworkError:
            logger.warning(
                'Failed to fetch conversation for typing notification: %s',
                conv_id
            )
        else:
            await conv.on_typing.fire(res)

    async def _handle_watermark_notification(self, watermark_notification):
        """Receive WatermarkNotification and update the conversation.

        Args:
            watermark_notification: hangouts_pb2.WatermarkNotification instance
        """
        conv_id = watermark_notification.conversation_id.id
        res = parsers.parse_watermark_notification(watermark_notification)
        await self.on_watermark_notification.fire(res)
        try:
            conv = await self._get_or_fetch_conversation(conv_id)
        except exceptions.NetworkError:
            logger.warning(
                'Failed to fetch conversation for watermark notification: %s',
                conv_id
            )
        else:
            await conv.on_watermark_notification.fire(res)

    async def _sync(self):
        """Sync conversation state and events that could have been missed."""
        logger.info('Syncing events since {}'.format(self._sync_timestamp))
        try:
            res = await self._client.sync_all_new_events(
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
                            await self._on_event(event_)
                else:
                    self._add_conversation(
                        conv_state.conversation,
                        conv_state.event,
                        conv_state.event_continuation_token
                    )
