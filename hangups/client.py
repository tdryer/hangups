"""Abstract class for writing chat clients."""

import aiohttp
import asyncio
import collections
import itertools
import json
import logging
import random
import re
import time
import datetime
import os

from hangups import (javascript, parsers, exceptions, http_utils, channel,
                     event, hangouts_pb2, pblite)

logger = logging.getLogger(__name__)
ORIGIN_URL = 'https://talkgadget.google.com'
IMAGE_UPLOAD_URL = 'http://docs.google.com/upload/photos/resumable'
PVT_TOKEN_URL = 'https://talkgadget.google.com/talkgadget/_/extension-start'
CHAT_INIT_URL = 'https://talkgadget.google.com/u/0/talkgadget/_/chat'
CHAT_INIT_PARAMS = {
    'prop': 'aChromeExtension',
    'fid': 'gtn-roster-iframe-id',
    'ec': '["ci:ec",true,true,false]',
    'pvt': None,  # Populated later
}
CHAT_INIT_REGEX = re.compile(
    r"(?:<script>AF_initDataCallback\((.*?)\);</script>)", re.DOTALL
)
# Timeout to send for setactiveclient requests:
ACTIVE_TIMEOUT_SECS = 120
# Minimum timeout between subsequent setactiveclient requests:
SETACTIVECLIENT_LIMIT_SECS = 60


# Initial account data received after the client is first connected:
InitialData = collections.namedtuple('InitialData', [
    'conversation_states',  # [ClientConversationState]
    'self_entity',  # ClientEntity
    'entities',  # [ClientEntity]
    'conversation_participants',  # [ClientConversationParticipantData]
    'sync_timestamp'  # datetime
])


class Client(object):
    """Instant messaging client for Hangouts.

    Maintains a connections to the servers, emits events, and accepts commands.
    """

    def __init__(self, cookies):
        """Create new client.

        cookies is a dictionary of authentication cookies.
        """

        # Event fired when the client connects for the first time with
        # arguments (initial_data).
        self.on_connect = event.Event('Client.on_connect')
        # Event fired when the client reconnects after being disconnected with
        # arguments ().
        self.on_reconnect = event.Event('Client.on_reconnect')
        # Event fired when the client is disconnected with arguments ().
        self.on_disconnect = event.Event('Client.on_disconnect')
        # Event fired when a ClientStateUpdate arrives with arguments
        # (state_update).
        self.on_state_update = event.Event('Client.on_state_update')

        self._cookies = cookies
        proxy = os.environ.get('HTTP_PROXY')
        if proxy:
            self._connector = aiohttp.ProxyConnector(proxy)
        else:
            self._connector = aiohttp.TCPConnector()

        # hangups.channel.Channel instantiated in connect()
        self._channel = None
        # API key sent with every request:
        self._api_key = None
        # Parameters sent in request headers:
        self._header_date = None
        self._header_version = None
        self._header_id = None
        # String identifying this client:
        self._client_id = None
        # Account email address:
        self._email = None
        # Time in seconds that the client as last set as active:
        self._last_active_secs = 0.0
        # ActiveClientState enum int value or None:
        self._active_client_state = None
        # Future for Channel.listen
        self._listen_future = None

    ##########################################################################
    # Public methods
    ##########################################################################

    @asyncio.coroutine
    def connect(self):
        """Establish a connection to the chat server.

        Returns when an error has occurred, or Client.disconnect has been
        called.
        """
        initial_data = yield from self._initialize_chat()
        self._channel = channel.Channel(self._cookies, self._connector)
        @asyncio.coroutine
        def _on_connect():
            """Wrapper to fire on_connect with initial_data."""
            yield from self.on_connect.fire(initial_data)
        self._channel.on_connect.add_observer(_on_connect)
        self._channel.on_reconnect.add_observer(self.on_reconnect.fire)
        self._channel.on_disconnect.add_observer(self.on_disconnect.fire)
        self._channel.on_message.add_observer(self._on_push_data)

        self._listen_future = asyncio.async(self._channel.listen())
        try:
            yield from self._listen_future
        except asyncio.CancelledError:
            pass
        logger.info('disconnecting gracefully')

    @asyncio.coroutine
    def disconnect(self):
        """Gracefully disconnect from the server.

        When disconnection is complete, Client.connect will return.
        """
        self._listen_future.cancel()
        self._connector.close()

    @asyncio.coroutine
    def set_active(self):
        """Set this client as active.

        While a client is active, no other clients will raise notifications.
        Call this method whenever there is an indication the user is
        interacting with this client. This method may be called very
        frequently, and it will only make a request when necessary.
        """
        is_active = (self._active_client_state ==
                     hangouts_pb2.IS_ACTIVE_CLIENT)
        timed_out = (time.time() - self._last_active_secs >
                     SETACTIVECLIENT_LIMIT_SECS)
        if not is_active or timed_out:
            # Update these immediately so if the function is called again
            # before the API request finishes, we don't start extra requests.
            self._active_client_state = hangouts_pb2.IS_ACTIVE_CLIENT
            self._last_active_secs = time.time()
            try:
                yield from self.setactiveclient(True, ACTIVE_TIMEOUT_SECS)
            except exceptions.NetworkError as e:
                logger.warning('Failed to set active client: {}'.format(e))
            else:
                logger.info('Set active client for {} seconds'
                            .format(ACTIVE_TIMEOUT_SECS))

    ##########################################################################
    # Private methods
    ##########################################################################

    @asyncio.coroutine
    def _initialize_chat(self):
        """Request push channel creation and initial chat data.

        Returns instance of InitialData.

        The response body is a HTML document containing a series of script tags
        containing JavaScript objects. We need to parse the objects to get at
        the data.
        """
        # We first need to fetch the 'pvt' token, which is required for the
        # initialization request (otherwise it will return 400).
        try:
            res = yield from http_utils.fetch(
                'get', PVT_TOKEN_URL, cookies=self._cookies,
                connector=self._connector
            )
            CHAT_INIT_PARAMS['pvt'] = javascript.loads(res.body.decode())[1]
            logger.info('Found PVT token: {}'.format(CHAT_INIT_PARAMS['pvt']))
        except (exceptions.NetworkError, ValueError) as e:
            raise exceptions.HangupsError('Failed to fetch PVT token: {}'
                                          .format(e))
        # Now make the actual initialization request:
        try:
            res = yield from http_utils.fetch(
                'get', CHAT_INIT_URL, cookies=self._cookies,
                params=CHAT_INIT_PARAMS, connector=self._connector
            )
        except exceptions.NetworkError as e:
            raise exceptions.HangupsError('Initialize chat request failed: {}'
                                          .format(e))

        # Parse the response by using a regex to find all the JS objects, and
        # parsing them. Not everything will be parsable, but we don't care if
        # an object we don't need can't be parsed.

        data_dict = {}
        for data in CHAT_INIT_REGEX.findall(res.body.decode()):
            try:
                logger.debug("Attempting to load javascript: {}..."
                             .format(repr(data[:100])))
                data = javascript.loads(data)
                # pylint: disable=invalid-sequence-index
                data_dict[data['key']] = data['data']
            except ValueError as e:
                try:
                    data = data.replace("data:function(){return", "data:")
                    data = data.replace("}}", "}")
                    data = javascript.loads(data)
                    data_dict[data['key']] = data['data']

                except ValueError as e:
                    raise

                # logger.debug('Failed to parse initialize chat object: {}\n{}'
                #              .format(e, data))

        # Extract various values that we will need.
        try:
            self._api_key = data_dict['ds:7'][0][2]
            logger.info('Found api_key: %s', self._api_key)
            self._email = data_dict['ds:33'][0][2]
            logger.info('Found email: %s', self._email)
            self._header_date = data_dict['ds:2'][0][4]
            logger.info('Found header_date: %s', self._header_date)
            self._header_version = data_dict['ds:2'][0][6]
            logger.info('Found header_version: %s', self._header_version)
            self._header_id = data_dict['ds:4'][0][7]
            logger.info('Found header_id: %s', self._header_id)
        except KeyError as e:
            raise exceptions.HangupsError('Failed to get initialize chat '
                                          'value: {}'.format(e))

        # Parse GetSelfInfoResponse
        get_self_info_response = hangouts_pb2.GetSelfInfoResponse()
        pblite.decode(get_self_info_response, data_dict['ds:20'][0])
        logger.debug('Parsed GetSelfInfoResponse:\n%s', get_self_info_response)

        # Parse SyncRecentConversationsResponse
        sync_recent_conversations_response = (
            hangouts_pb2.SyncRecentConversationsResponse()
        )
        pblite.decode(sync_recent_conversations_response,
                      data_dict['ds:19'][0])
        # TODO: this might be too much data to log
        #logger.debug('Parsed SyncRecentConversationsResponse:\n%s',
        #             sync_recent_conversations_response)

        # Parse GetSuggestedEntitiesResponse
        # This gives us entities for the user's contacts, but doesn't include
        # users not in contacts.
        get_suggested_entities_response = hangouts_pb2.GetSuggestedEntitiesResponse()
        pblite.decode(get_suggested_entities_response, data_dict['ds:21'][0])
        logger.debug('Parsed GetSuggestedEntitiesResponse:\n%s', get_suggested_entities_response)

        # Combine entities from all responses into one list of all the known
        # entities
        initial_entities = []
        initial_entities.extend(get_suggested_entities_response.entity)
        initial_entities.extend(e.entity for e in itertools.chain(
            get_suggested_entities_response.group1.entity,
            get_suggested_entities_response.group2.entity,
            get_suggested_entities_response.group3.entity,
            get_suggested_entities_response.group4.entity,
            get_suggested_entities_response.group5.entity,
            get_suggested_entities_response.group6.entity
        ))

        # Create list of ConversationParticipant data to use as a fallback for
        # entities that can't be found.
        conv_part_list = []
        for conversation_state in sync_recent_conversations_response.conversation_state:
            conv_part_list.extend(conversation_state.conversation.participant_data)

        sync_timestamp = parsers.from_timestamp(
            sync_recent_conversations_response.sync_timestamp
        )

        return InitialData(
            sync_recent_conversations_response.conversation_state,
            get_self_info_response.self_entity, initial_entities,
            conv_part_list, sync_timestamp,
        )

    def _get_cookie(self, name):
        """Return a cookie for raise error if that cookie was not provided."""
        try:
            return self._cookies[name]
        except KeyError:
            raise KeyError("Cookie '{}' is required".format(name))

    def _get_request_header(self):
        """Return request header for chat API request."""
        return [
            [6, 3, self._header_version, self._header_date],
            [self._client_id, self._header_id],
            None,
            "en"
        ]

    @asyncio.coroutine
    def _on_push_data(self, submission):
        """Parse StateUpdate messages and call the appropriate events."""
        for state_update in parsers.parse_submission(submission):
            if isinstance(state_update, dict) and 'client_id' in state_update:
                # Hack to receive client ID:
                self._client_id = state_update['client_id']
                logger.info('Received new client_id: {}'
                            .format(self._client_id))
            else:
                header = state_update.state_update_header
                self._active_client_state = header.active_client_state
                yield from self.on_state_update.fire(state_update)

    # TODO: add better logging here and remove it from _base_request
    @asyncio.coroutine
    def _pb_request(self, endpoint, request_pb, response_pb):
        """Make chat API request with protobuf request/response.

        Raises hangups.NetworkError if the request fails.
        """
        url = 'https://clients6.google.com/chat/v1/{}'.format(endpoint)
        body = json.dumps(pblite.encode(request_pb))
        logger.debug(body)
        content_type = 'application/json+protobuf'
        res = yield from self._base_request(url, content_type, body,
                                            use_json=False)
        pblite.decode(response_pb, javascript.loads(res.body.decode()))
        logger.debug(response_pb)
        status = response_pb.response_header.status
        description = response_pb.response_header.error_description
        if status != hangouts_pb2.RESPONSE_STATUS_OK:
            raise exceptions.NetworkError(
                'Request failed with status {}: \'{}\''
                .format(status, description)
            )

    # TODO: remove this
    @asyncio.coroutine
    def _request(self, endpoint, body_json, use_json=True):
        """Make chat API request.

        Raises hangups.NetworkError if the request fails.
        """
        url = 'https://clients6.google.com/chat/v1/{}'.format(endpoint)
        res = yield from self._base_request(
            url, 'application/json+protobuf', json.dumps(body_json),
            use_json=use_json
        )
        return res

    @asyncio.coroutine
    def _base_request(self, url, content_type, data, use_json=True):
        """Make API request.

        Raises hangups.NetworkError if the request fails.
        """
        headers = channel.get_authorization_headers(
            self._get_cookie('SAPISID')
        )
        headers['content-type'] = content_type
        required_cookies = ['SAPISID', 'HSID', 'SSID', 'APISID', 'SID']
        cookies = {cookie: self._get_cookie(cookie)
                   for cookie in required_cookies}
        params = {
            'key': self._api_key,
            'alt': 'json' if use_json else 'protojson',
        }
        res = yield from http_utils.fetch(
            'post', url, headers=headers, cookies=cookies, params=params,
            data=data, connector=self._connector
        )
        logger.debug('Response to request for {} was {}:\n{}'
                     .format(url, res.code, res.body))
        return res

    def _get_request_header_pb(self):
        """Return populated ClientRequestHeader message."""
        client_identifier = hangouts_pb2.ClientIdentifier(
            header_id=self._header_id,
        )
        # resource is allowed to be null if it's not available yet (the Chrome
        # client does this for the first getentitybyid call)
        if self._client_id is not None:
            client_identifier.resource = self._client_id
        return hangouts_pb2.RequestHeader(
            client_version=hangouts_pb2.ClientVersion(
                client_id=hangouts_pb2.CLIENT_ID_WEB_GMAIL,
                build_type=hangouts_pb2.BUILD_TYPE_PRODUCTION_WEB,
                major_version=self._header_version,
                version_timestamp=int(self._header_date),
            ),
            client_identifier=client_identifier,
            language_code='en',
        )

    def get_client_generated_id(self):
        """Return ID for client_generated_id fields."""
        return random.randint(0, 2**32)

    ###########################################################################
    # Raw API request methods
    ###########################################################################

    @asyncio.coroutine
    def syncallnewevents(self, timestamp):
        """List all events occurring at or after timestamp.

        This method requests protojson rather than json so we have one chat
        message parser rather than two.

        timestamp: datetime.datetime instance specifying the time after
        which to return all events occurring in.

        Raises hangups.NetworkError if the request fails.

        Returns SyncAllNewEventsResponse.
        """
        request = hangouts_pb2.SyncAllNewEventsRequest(
            request_header=self._get_request_header_pb(),
            last_sync_timestamp=parsers.to_timestamp(timestamp),
            max_response_size_bytes=1048576,
        )
        response = hangouts_pb2.SyncAllNewEventsResponse()
        yield from self._pb_request('conversations/syncallnewevents', request,
                                    response)
        return response

    @asyncio.coroutine
    def sendchatmessage(
            self, conversation_id, segments, image_id=None,
            otr_status=hangouts_pb2.ON_THE_RECORD
    ):
        """Send a chat message to a conversation.

        conversation_id must be a valid conversation ID. segments must be a
        list of message segments to send, in pblite format.

        otr_status determines whether the message will be saved in the server's
        chat history. Note that the OTR status of the conversation is
        irrelevant, clients may send messages with whatever OTR status they
        like.

        image_id is an option ID of an image retrieved from
        Client.upload_image. If provided, the image will be attached to the
        message.

        Raises hangups.NetworkError if the request fails.
        """
        # TODO: temporary conversation for compat
        segments_pb = []
        for segment_pblite in segments:
            segment_pb = hangouts_pb2.Segment()
            pblite.decode(segment_pb, segment_pblite)
            segments_pb.append(segment_pb)

        request = hangouts_pb2.SendChatMessageRequest(
            request_header=self._get_request_header_pb(),
            message_content=hangouts_pb2.MessageContent(
                segment=segments_pb,
            ),
            event_request_header=hangouts_pb2.EventRequestHeader(
                conversation_id=hangouts_pb2.ConversationID(
                    id=conversation_id,
                ),
                client_generated_id=self.get_client_generated_id(),
                expected_otr=otr_status,
            ),
        )

        if image_id is not None:
            request.existing_media = hangouts_pb2.ExistingMedia(
                photo=hangouts_pb2.Photo(photo_id=image_id)
            )

        logger.debug(request)
        response = hangouts_pb2.SendChatMessageResponse()
        yield from self._pb_request('conversations/sendchatmessage', request,
                                    response)
        return response

    @asyncio.coroutine
    def setactiveclient(self, is_active, timeout_secs):
        """Set the active client.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.SetActiveClientRequest(
            request_header=self._get_request_header_pb(),
            is_active=is_active,
            full_jid="{}/{}".format(self._email, self._client_id),
            timeout_secs=timeout_secs,
        )
        response = hangouts_pb2.SetActiveClientResponse()
        yield from self._pb_request('clients/setactiveclient', request,
                                    response)
        return response

    @asyncio.coroutine
    def updatewatermark(self, conv_id, read_timestamp):
        """Update the watermark (read timestamp) for a conversation.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.UpdateWatermarkRequest(
            request_header=self._get_request_header_pb(),
            conversation_id=hangouts_pb2.ConversationID(id=conv_id),
            last_read_timestamp=parsers.to_timestamp(read_timestamp),
        )
        response = hangouts_pb2.UpdateWatermarkResponse()
        yield from self._pb_request('conversations/updatewatermark', request,
                                    response)
        return response

    @asyncio.coroutine
    def getentitybyid(self, chat_id_list):
        """Return information about a list of contacts.

        Raises hangups.NetworkError if the request fails.
        """
        # TODO: change chat_id_list to gaia_id_list
        request = hangouts_pb2.GetEntityByIdRequest(
            request_header=self._get_request_header_pb(),
            batch_lookup_spec=[hangouts_pb2.EntityLookupSpec(gaia_id=gaia_id)
                               for gaia_id in chat_id_list],
        )
        response = hangouts_pb2.GetEntityByIdResponse()
        yield from self._pb_request('contacts/getentitybyid', request,
                                    response)
        return response

    @asyncio.coroutine
    def renameconversation(self, conversation_id, name,
                           otr_status=hangouts_pb2.ON_THE_RECORD):
        """Rename a conversation.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.RenameConversationRequest(
            request_header=self._get_request_header_pb(),
            new_name=name,
            event_request_header=hangouts_pb2.EventRequestHeader(
                conversation_id=hangouts_pb2.ConversationID(
                    id=conversation_id,
                ),
                client_generated_id=self.get_client_generated_id(),
                expected_otr=otr_status,
            ),
        )
        response = hangouts_pb2.RenameConversationResponse()
        yield from self._pb_request('conversations/renameconversation',
                                    request, response)
        return response

    @asyncio.coroutine
    def getconversation(self, conversation_id, event_timestamp, max_events=50):
        """Return conversation events.

        This is mainly used for retrieving conversation scrollback. Events
        occurring before event_timestamp are returned, in order from oldest to
        newest.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.GetConversationRequest(
            request_header=self._get_request_header_pb(),
            conversation_spec=hangouts_pb2.ConversationSpec(
                conversation_id=hangouts_pb2.ConversationID(id=conversation_id)
            ),
            include_event=True,
            max_events_per_conversation=max_events,
            event_continuation_token=hangouts_pb2.EventContinuationToken(
                event_timestamp=parsers.to_timestamp(event_timestamp)
            ),
        )
        response = hangouts_pb2.GetConversationResponse()
        yield from self._pb_request('conversations/getconversation', request,
                                    response)
        return response

    @asyncio.coroutine
    def upload_image(self, image_file, filename=None):
        """Upload an image that can be later attached to a chat message.

        image_file is a file-like object containing an image.

        The name of the uploaded file may be changed by specifying the filename
        argument.

        Raises hangups.NetworkError if the request fails.

        Returns ID of uploaded image.
        """
        image_filename = (filename if filename
                          else os.path.basename(image_file.name))
        image_data = image_file.read()

        # Create image and request upload URL
        res1 = yield from self._base_request(
            IMAGE_UPLOAD_URL,
            'application/x-www-form-urlencoded;charset=UTF-8',
            json.dumps({
                "protocolVersion": "0.8",
                "createSessionRequest": {
                    "fields": [{
                        "external": {
                            "name": "file",
                            "filename": image_filename,
                            "put": {},
                            "size": len(image_data),
                        }
                    }]
                }
            }))
        upload_url = (json.loads(res1.body.decode())['sessionStatus']
                      ['externalFieldTransfers'][0]['putInfo']['url'])

        # Upload image data and get image ID
        res2 = yield from self._base_request(
            upload_url, 'application/octet-stream', image_data
        )
        return (json.loads(res2.body.decode())['sessionStatus']
                ['additionalInfo']
                ['uploader_service.GoogleRupioAdditionalInfo']
                ['completionInfo']['customerSpecificInfo']['photoid'])

    ###########################################################################
    # UNUSED raw API request methods (by hangups itself) for reference
    ###########################################################################

    @asyncio.coroutine
    def removeuser(self, conversation_id,
                   otr_status=hangouts_pb2.ON_THE_RECORD):
        """Leave group conversation.

        conversation_id must be a valid conversation ID.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.RemoveUserRequest(
            request_header=self._get_request_header_pb(),
            event_request_header=hangouts_pb2.EventRequestHeader(
                conversation_id=hangouts_pb2.ConversationID(
                    id=conversation_id,
                ),
                client_generated_id=self.get_client_generated_id(),
                expected_otr=otr_status,
            ),
        )
        response = hangouts_pb2.RemoveUserResponse()
        yield from self._pb_request('conversations/removeuser', request,
                                    response)
        return response

    @asyncio.coroutine
    def deleteconversation(self, conversation_id):
        """Delete one-to-one conversation.

        One-to-one conversations are "sticky"; they can't actually be deleted.
        This API clears the event history of the specified conversation up to
        delete_upper_bound_timestamp, hiding it if no events remain.

        conversation_id must be a valid conversation ID.

        Raises hangups.NetworkError if the request fails.
        """
        timestamp = parsers.to_timestamp(
            datetime.datetime.now(tz=datetime.timezone.utc)
        )
        request = hangouts_pb2.DeleteConversationRequest(
            request_header=self._get_request_header_pb(),
            conversation_id=hangouts_pb2.ConversationID(id=conversation_id),
            delete_upper_bound_timestamp=timestamp
        )
        response = hangouts_pb2.DeleteConversationResponse()
        yield from self._pb_request('conversations/deleteconversation',
                                    request, response)
        return response

    @asyncio.coroutine
    def settyping(self, conversation_id, typing=hangouts_pb2.TYPING_STARTED):
        """Send typing notification.

        conversation_id must be a valid conversation ID.
        typing must be a hangups.TypingType Enum.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.SetTypingRequest(
            request_header=self._get_request_header_pb(),
            conversation_id=hangouts_pb2.ConversationID(id=conversation_id),
            type=typing,
        )
        response = hangouts_pb2.SetTypingResponse()
        yield from self._pb_request('conversations/settyping', request,
                                    response)
        return response

    @asyncio.coroutine
    def getselfinfo(self):
        """Return information about your account.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.GetSelfInfoRequest(
            request_header=self._get_request_header_pb(),
        )
        response = hangouts_pb2.GetSelfInfoResponse()
        yield from self._pb_request('contacts/getselfinfo', request, response)
        return response

    @asyncio.coroutine
    def setfocus(self, conversation_id):
        """Set focus to a conversation.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.SetFocusRequest(
            request_header=self._get_request_header_pb(),
            conversation_id=hangouts_pb2.ConversationID(id=conversation_id),
            type=hangouts_pb2.FOCUSED,
            timeout_secs=20,
        )
        response = hangouts_pb2.SetFocusResponse()
        yield from self._pb_request('conversations/setfocus', request,
                                    response)
        return response

    @asyncio.coroutine
    def searchentities(self, search_string, max_results):
        """Search for people.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.SearchEntitiesRequest(
            request_header=self._get_request_header_pb(),
            query=search_string,
            max_count=max_results,
        )
        response = hangouts_pb2.SearchEntitiesResponse()
        yield from self._pb_request('contacts/searchentities', request,
                                    response)
        return response

    @asyncio.coroutine
    def setpresence(self, online, mood=None):
        """Set the presence or mood of this client.

        Raises hangups.NetworkError if the request fails.
        """
        type_ = (hangouts_pb2.CLIENT_PRESENCE_STATE_DESKTOP_ACTIVE if online
                 else hangouts_pb2.CLIENT_PRESENCE_STATE_DESKTOP_IDLE)
        request = hangouts_pb2.SetPresenceRequest(
            request_header=self._get_request_header_pb(),
            presence_state_setting=hangouts_pb2.PresenceStateSetting(
                timeout_secs=720,
                type=type_,
            ),
        )
        if mood is not None:
            segment = (
                request.mood_setting.mood_message.mood_content.segment.add()
            )
            segment.type = hangouts_pb2.TEXT
            segment.text = mood
        response = hangouts_pb2.SetPresenceResponse()
        yield from self._pb_request('presence/setpresence', request, response)
        return response

    @asyncio.coroutine
    def querypresence(self, gaia_id):
        """Check someone's presence status.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.QueryPresenceRequest(
            request_header=self._get_request_header_pb(),
            user_id=[hangouts_pb2.UserID(gaia_id=gaia_id)],
            field_mask=[hangouts_pb2.FIELD_MASK_REACHABLE,
                        hangouts_pb2.FIELD_MASK_AVAILABLE,
                        hangouts_pb2.FIELD_MASK_DEVICE],
        )
        response = hangouts_pb2.QueryPresenceResponse()
        yield from self._pb_request('presence/querypresence', request,
                                    response)
        return response

    @asyncio.coroutine
    def syncrecentconversations(self):
        """List the contents of recent conversations, including messages.

        Similar to syncallnewevents, but appears to return a limited number of
        conversations (20) rather than all conversations in a given date range.

        Can be used to retrieve archived conversations.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.SyncRecentConversationsRequest(
            request_header=self._get_request_header_pb(),
            max_conversations=5,
            max_events_per_conversation=2,
            sync_filter=[hangouts_pb2.SYNC_FILTER_INBOX],
        )
        response = hangouts_pb2.SyncRecentConversationsResponse()
        yield from self._pb_request('conversations/syncrecentconversations',
                                    request, response)
        return response

    @asyncio.coroutine
    def setconversationnotificationlevel(self, conversation_id, level):
        """Set the notification level of a conversation.

        Pass hangouts_pb2.QUIET to disable notifications, or hangouts_pb2.RING
        to enable them.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.SetConversationNotificationLevelRequest(
            request_header=self._get_request_header_pb(),
            conversation_id=hangouts_pb2.ConversationID(id=conversation_id),
            level=level,
        )
        response = hangouts_pb2.SetConversationNotificationLevelResponse()
        yield from self._pb_request(
            'conversations/setconversationnotificationlevel', request, response
        )
        return response

    @asyncio.coroutine
    def easteregg(self, conversation_id, easteregg):
        """Send an easteregg to a conversation.

        easteregg may not be empty.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.EasterEggRequest(
            request_header=self._get_request_header_pb(),
            conversation_id=hangouts_pb2.ConversationID(id=conversation_id),
            easter_egg=hangouts_pb2.EasterEgg(message=easteregg),
        )
        response = hangouts_pb2.EasterEggResponse()
        yield from self._pb_request('conversations/easteregg', request,
                                    response)
        return response

    @asyncio.coroutine
    def createconversation(self, chat_id_list, force_group=False):
        """Create new one-to-one or group conversation.

        chat_id_list is list of other users to invite to the conversation.

        Raises hangups.NetworkError if the request fails.
        """
        is_group = len(chat_id_list) > 1 or force_group
        request = hangouts_pb2.CreateConversationRequest(
            request_header=self._get_request_header_pb(),
            type=hangouts_pb2.GROUP if is_group else hangouts_pb2.ONE_TO_ONE,
            client_generated_id=self.get_client_generated_id(),
            name="created by hangups",
            invitee_id=[hangouts_pb2.InviteeID(gaia_id=chat_id)
                        for chat_id in chat_id_list],
        )
        response = hangouts_pb2.CreateConversationResponse()
        yield from self._pb_request('conversations/createconversation',
                                    request, response)
        return response

    @asyncio.coroutine
    def adduser(self, conversation_id, chat_id_list,
                otr_status=hangouts_pb2.ON_THE_RECORD):
        """Add users to an existing group conversation.

        conversation_id must be a valid conversation ID.
        chat_id_list is list of users which should be invited to conversation.

        Raises hangups.NetworkError if the request fails.
        """
        request = hangouts_pb2.AddUserRequest(
            request_header=self._get_request_header_pb(),
            invitee_id=[hangouts_pb2.InviteeID(gaia_id=chat_id)
                        for chat_id in chat_id_list],
            event_request_header=hangouts_pb2.EventRequestHeader(
                conversation_id=hangouts_pb2.ConversationID(
                    id=conversation_id,
                ),
                client_generated_id=self.get_client_generated_id(),
                expected_otr=otr_status,
            ),
        )
        response = hangouts_pb2.AddUserResponse()
        yield from self._pb_request('conversations/adduser', request, response)
        return response
