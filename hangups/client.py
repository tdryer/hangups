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

from hangups import (javascript, parsers, exceptions, http_utils, channel,
                     event, schemas)

logger = logging.getLogger(__name__)
ORIGIN_URL = 'https://talkgadget.google.com'
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
        # ActiveClientState enum value or None:
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

    @asyncio.coroutine
    def set_active(self):
        """Set this client as active.

        While a client is active, no other clients will raise notifications.
        Call this method whenever there is an indication the user is
        interacting with this client. This method may be called very
        frequently, and it will only make a request when necessary.
        """
        is_active = (self._active_client_state ==
                     schemas.ActiveClientState.IS_ACTIVE_CLIENT)
        timed_out = (time.time() - self._last_active_secs >
                     SETACTIVECLIENT_LIMIT_SECS)
        if not is_active or timed_out:
            # Update these immediately so if the function is called again
            # before the API request finishes, we don't start extra requests.
            self._active_client_state = (
                schemas.ActiveClientState.IS_ACTIVE_CLIENT
            )
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
            self._email = data_dict['ds:34'][0][2]
            self._header_date = data_dict['ds:2'][0][4]
            self._header_version = data_dict['ds:2'][0][6]
            self._header_id = data_dict['ds:4'][0][7]
            _sync_timestamp = parsers.from_timestamp(
                # cgserp?
                # data_dict['ds:21'][0][1][4]
                # data_dict['ds:35'][0][1][4]
                data_dict['ds:21'][0][1][4]
            )
        except KeyError as e:
            raise exceptions.HangupsError('Failed to get initialize chat '
                                          'value: {}'.format(e))

        # Parse the entity representing the current user.
        self_entity = schemas.CLIENT_GET_SELF_INFO_RESPONSE.parse(
            # cgsirp?
            # data_dict['ds:20'][0]
            # data_dict['ds:35'][0]
            data_dict['ds:20'][0]
        ).self_entity

        # Parse every existing conversation's state, including participants.
        initial_conv_states = schemas.CLIENT_CONVERSATION_STATE_LIST.parse(
            # csrcrp?
            # data_dict['ds:19'][0][3]
            # data_dict['ds:36'][0][3]
            data_dict['ds:19'][0][3]
        )
        initial_conv_parts = []
        for conv_state in initial_conv_states:
            initial_conv_parts.extend(conv_state.conversation.participant_data)

        # Parse the entities for the user's contacts (doesn't include users not
        # in contacts). If this fails, continue without the rest of the
        # entities.
        initial_entities = []
        try:
            entities = schemas.INITIAL_CLIENT_ENTITIES.parse(
                # cgserp?
                # data_dict['ds:21'][0]
                # data_dict['ds:37'][0]
                data_dict['ds:21'][0]
            )
        except ValueError as e:
            logger.warning('Failed to parse initial client entities: {}'
                           .format(e))
        else:
            initial_entities.extend(entities.entities)
            initial_entities.extend(e.entity for e in itertools.chain(
                entities.group1.entity, entities.group2.entity,
                entities.group3.entity, entities.group4.entity,
                entities.group5.entity
            ))

        return InitialData(initial_conv_states, self_entity, initial_entities,
                           initial_conv_parts, _sync_timestamp)

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
        """Parse ClientStateUpdate and call the appropriate events."""
        for state_update in parsers.parse_submission(submission):
            if isinstance(state_update, dict) and 'client_id' in state_update:
                # Hack to receive client ID:
                self._client_id = state_update['client_id']
                logger.info('Received new client_id: {}'
                            .format(self._client_id))
            else:
                self._active_client_state = (
                    state_update.state_update_header.active_client_state
                )
                yield from self.on_state_update.fire(state_update)

    @asyncio.coroutine
    def _request(self, endpoint, body_json, use_json=True):
        """Make chat API request.

        Raises hangups.NetworkError if the request fails.
        """
        url = 'https://clients6.google.com/chat/v1/{}'.format(endpoint)
        headers = channel.get_authorization_headers(self._get_cookie('SAPISID'))
        headers['content-type'] = 'application/json+protobuf'
        required_cookies = ['SAPISID', 'HSID', 'SSID', 'APISID', 'SID']
        cookies = {cookie: self._get_cookie(cookie)
                   for cookie in required_cookies}
        params = {
            'key': self._api_key,
            'alt': 'json' if use_json else 'protojson',
        }
        res = yield from http_utils.fetch(
            'post', url, headers=headers, cookies=cookies, params=params,
            data=json.dumps(body_json), connector=self._connector
        )
        logger.debug('Response to request for {} was {}:\n{}'
                     .format(endpoint, res.code, res.body))
        return res

    ###########################################################################
    # Raw API request methods
    ###########################################################################

    @asyncio.coroutine
    def syncallnewevents(self, timestamp):
        """List all events occuring at or after timestamp.

        This method requests protojson rather than json so we have one chat
        message parser rather than two.

        timestamp: datetime.datetime instance specifying the time after
        which to return all events occuring in.

        Raises hangups.NetworkError if the request fails.

        Returns a ClientSyncAllNewEventsResponse.
        """
        res = yield from self._request('conversations/syncallnewevents', [
            self._get_request_header(),
            # last_sync_timestamp
            parsers.to_timestamp(timestamp),
            [], None, [], False, [],
            1048576 # max_response_size_bytes
        ], use_json=False)
        try:
            res = schemas.CLIENT_SYNC_ALL_NEW_EVENTS_RESPONSE.parse(
                javascript.loads(res.body.decode())
            )
        except ValueError as e:
            raise exceptions.NetworkError('Response failed to parse: {}'
                                          .format(e))
        # can return 200 but still contain an error
        status = res.response_header.status
        if status != 1:
            raise exceptions.NetworkError('Response status is \'{}\''
                                          .format(status))
        return res

    @asyncio.coroutine
    def sendchatmessage(self, conversation_id, segments):
        """Send a chat message to a conversation.

        conversation_id must be a valid conversation ID. segments must be a
        list of message segments to send, in pblite format.

        Raises hangups.NetworkError if the request fails.
        """
        client_generated_id = random.randint(0, 2**32)
        body = [
            self._get_request_header(),
            None, None, None, [],
            [
                segments, []
            ],
            None,
            [
                [conversation_id], client_generated_id, 2
            ],
            None, None, None, []
        ]
        res = yield from self._request('conversations/sendchatmessage', body)
        # sendchatmessage can return 200 but still contain an error
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            raise exceptions.NetworkError('Unexpected status: {}'
                                          .format(res_status))

    @asyncio.coroutine
    def setactiveclient(self, is_active, timeout_secs):
        """Set the active client.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('clients/setactiveclient', [
            self._get_request_header(),
            # is_active: whether the client is active or not
            is_active,
            # full_jid: user@domain/resource
            "{}/{}".format(self._email, self._client_id),
            # timeout_secs: timeout in seconds for this client to be active
            timeout_secs
        ])
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            raise exceptions.NetworkError('Unexpected status: {}'
                                          .format(res_status))

    ###########################################################################
    # UNUSED raw API request methods (by hangups itself) for reference
    ###########################################################################

    @asyncio.coroutine
    def removeuser(self, conversation_id):
        """Leave group conversation.

        conversation_id must be a valid conversation ID.

        Raises hangups.NetworkError if the request fails.
        """
        client_generated_id = random.randint(0, 2**32)
        res = yield from self._request('conversations/removeuser', [
            self._get_request_header(),
            None, None, None,
            [
                [conversation_id], client_generated_id, 2
            ],
        ])
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            raise exceptions.NetworkError('Unexpected status: {}'
                                          .format(res_status))

    @asyncio.coroutine
    def deleteconversation(self, conversation_id):
        """Delete one-to-one conversation.

        conversation_id must be a valid conversation ID.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('conversations/deleteconversation', [
            self._get_request_header(),
            [conversation_id],
            # Not sure what timestamp should be there, last time I have tried it
            # Hangouts client in GMail sent something like now() - 5 hours
            parsers.to_timestamp(
                datetime.datetime.now(tz=datetime.timezone.utc)
            ),
            None, [],
        ])
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            raise exceptions.NetworkError('Unexpected status: {}'
                                          .format(res_status))

    @asyncio.coroutine
    def settyping(self, conversation_id, typing=schemas.TypingStatus.TYPING):
        """Send typing notification.

        conversation_id must be a valid conversation ID.
        typing must be a hangups.TypingStatus Enum.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('conversations/settyping', [
            self._get_request_header(),
            [conversation_id],
            typing.value
        ])
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            raise exceptions.NetworkError('Unexpected status: {}'
                                          .format(res_status))

    @asyncio.coroutine
    def updatewatermark(self, conv_id, read_timestamp):
        """Update the watermark (read timestamp) for a conversation.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('conversations/updatewatermark', [
            self._get_request_header(),
            # conversation_id
            [conv_id],
            # latest_read_timestamp
            parsers.to_timestamp(read_timestamp),
        ])
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            raise exceptions.NetworkError('Unexpected status: {}'
                                          .format(res_status))

    @asyncio.coroutine
    def getselfinfo(self):
        """Return information about your account.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('contacts/getselfinfo', [
            self._get_request_header(),
            [], []
        ])
        return json.loads(res.body.decode())

    @asyncio.coroutine
    def setfocus(self, conversation_id):
        """Set focus (occurs whenever you give focus to a client).

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('conversations/setfocus', [
            self._get_request_header(),
            [conversation_id],
            1,
            20
        ])
        return json.loads(res.body.decode())

    @asyncio.coroutine
    def searchentities(self, search_string, max_results):
        """Search for people.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('contacts/searchentities', [
            self._get_request_header(),
            [],
            search_string,
            max_results
        ])
        return json.loads(res.body.decode())

    @asyncio.coroutine
    def setpresence(self, online, mood=None):
        """Set the presence or mood of this client.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('presence/setpresence', [
            self._get_request_header(),
            [
                # timeout_secs timeout in seconds for this presence
                720,
                # client_presence_state:
                # 40 => DESKTOP_ACTIVE
                # 30 => DESKTOP_IDLE
                # 1 => NONE
                1 if online else 40,
            ],
            None,
            None,
            # True if going offline, False if coming online
            [not online],
            # UTF-8 smiley like 0x1f603
            [mood],
        ])
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            raise exceptions.NetworkError('Unexpected status: {}'
                                          .format(res_status))

    @asyncio.coroutine
    def querypresence(self, chat_id):
        """Check someone's presence status.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('presence/querypresence', [
            self._get_request_header(),
            [
                [chat_id]
            ],
            [1, 2, 5, 7, 8]
        ])
        return json.loads(res.body.decode())

    @asyncio.coroutine
    def getentitybyid(self, chat_id_list):
        """Return information about a list of contacts.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('contacts/getentitybyid', [
            self._get_request_header(),
            None,
            [[str(chat_id)] for chat_id in chat_id_list],
        ])
        return json.loads(res.body.decode())

    @asyncio.coroutine
    def getconversation(self, conversation_id, event_timestamp, max_events=50):
        """Return conversation events.

        This is mainly used for retrieving conversation scrollback. Events
        occurring before event_timestamp are returned, in order from oldest to
        newest.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('conversations/getconversation', [
            self._get_request_header(),
            [[conversation_id], [], []],  # conversationSpec
            False,  # includeConversationMetadata
            True,  # includeEvents
            None,  # ???
            max_events,  # maxEventsPerConversation
            # eventContinuationToken (specifying timestamp is sufficient)
            [
                None,  # eventId
                None,  # storageContinuationToken
                parsers.to_timestamp(event_timestamp),  # eventTimestamp
            ]
        ], use_json=False)
        try:
            res = schemas.CLIENT_GET_CONVERSATION_RESPONSE.parse(
                javascript.loads(res.body.decode())
            )
        except ValueError as e:
            raise exceptions.NetworkError('Response failed to parse: {}'
                                          .format(e))
        # can return 200 but still contain an error
        status = res.response_header.status
        if status != 1:
            raise exceptions.NetworkError('Response status is \'{}\''
                                          .format(status))
        return res

    @asyncio.coroutine
    def syncrecentconversations(self):
        """List the contents of recent conversations, including messages.

        Similar to syncallnewevents, but appears to return a limited number of
        conversations (20) rather than all conversations in a given date range.

        Raises hangups.NetworkError if the request fails.
        """
        res = yield from self._request('conversations/syncrecentconversations',
                                       [self._get_request_header()])
        return json.loads(res.body.decode())

    @asyncio.coroutine
    def setchatname(self, conversation_id, name):
        """Set the name of a conversation.

        Raises hangups.NetworkError if the request fails.
        """
        client_generated_id = random.randint(0, 2 ** 32)
        body = [
            self._get_request_header(),
            None,
            name,
            None,
            [[conversation_id], client_generated_id, 1]
        ]
        res = yield from self._request('conversations/renameconversation', body)
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            logger.warning('renameconversation returned status {}'
                           .format(res_status))
            raise exceptions.NetworkError()

    @asyncio.coroutine
    def sendeasteregg(self, conversation_id, easteregg):
        """Send a easteregg to a conversation.

        easteregg may not be empty.

        Raises hangups.NetworkError if the request fails.
        """
        body = [
            self._get_request_header(),
            [conversation_id],
            [easteregg, None, 1]
        ]
        res = yield from self._request('conversations/easteregg', body)
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            logger.warning('easteregg returned status {}'
                           .format(res_status))
            raise exceptions.NetworkError()

