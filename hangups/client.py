"""Abstract class for writing chat clients."""

from tornado import gen, httpclient
import collections
import hashlib
import itertools
import json
import logging
import random
import re
import time

from hangups import (javascript, parsers, exceptions, http_utils, channel,
                     event, schemas)

logger = logging.getLogger(__name__)
ORIGIN_URL = 'https://talkgadget.google.com'
CHAT_INIT_URL = 'https://talkgadget.google.com/u/0/talkgadget/_/chat'
CHAT_INIT_PARAMS = {
    'prop': 'aChromeExtension',
    'fid': 'gtn-roster-iframe-id',
    'ec': '["ci:ec",true,true,false]',
}
CHAT_INIT_REGEX = re.compile(
    r"(?:<script>AF_initDataCallback\((.*?)\);</script>)", re.DOTALL
)
# Set the connection and request timeouts low so we fail fast when there's a
# network problem.
CONNECT_TIMEOUT = 10
REQUEST_TIMEOUT = 10


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

        # hangups.channel.Channel instantiated in connect()
        self._channel = None
        # API key sent with every request:
        self._api_key = None
        # Parameters sent in request headers:
        self._header_date = None
        self._header_version = None
        self._header_id = None
        # TODO This one isn't being set anywhere:
        self._header_client = None
        # Parameters needed to create the Channel:
        self._channel_path = None
        self._clid = None
        self._channel_ec_param = None
        self._channel_prop_param = None

    ##########################################################################
    # Public methods
    ##########################################################################

    @gen.coroutine
    def connect(self):
        """Connect to the server and receive events."""
        initial_data = yield self._initialize_chat()
        self._channel = channel.Channel(self._cookies, self._channel_path,
                                        self._clid, self._channel_ec_param,
                                        self._channel_prop_param)
        self._channel.on_connect.add_observer(
            lambda: self.on_connect.fire(initial_data)
        )
        self._channel.on_reconnect.add_observer(self.on_reconnect.fire)
        self._channel.on_disconnect.add_observer(self.on_disconnect.fire)
        self._channel.on_message.add_observer(self._on_push_data)
        yield self._channel.listen()

    ##########################################################################
    # Private methods
    ##########################################################################

    @gen.coroutine
    def _initialize_chat(self):
        """Request push channel creation and initial chat data.

        Returns instance of InitialData.

        The response body is a HTML document containing a series of script tags
        containing JavaScript objects. We need to parse the objects to get at
        the data.
        """
        try:
            res = yield http_utils.fetch(
                CHAT_INIT_URL, cookies=self._cookies, params=CHAT_INIT_PARAMS,
                connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT
            )
        except httpclient.HTTPError as e:
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
                logger.debug('Failed to parse initialize chat object: {}\n{}'
                             .format(e, data))

        # Extract various values that we will need.
        try:
            self._api_key = data_dict['ds:7'][0][2]
            self._header_date = data_dict['ds:2'][0][4]
            self._header_version = data_dict['ds:2'][0][6]
            self._header_id = data_dict['ds:4'][0][7]
            self._channel_path = data_dict['ds:4'][0][1]
            self._clid = data_dict['ds:4'][0][7]
            self._channel_ec_param = data_dict['ds:4'][0][4]
            self._channel_prop_param = data_dict['ds:4'][0][5]
            _sync_timestamp = parsers.from_timestamp(
                data_dict['ds:21'][0][1][4]
            )
        except KeyError as e:
            raise exceptions.HangupsError('Failed to get initialize chat '
                                          'value: {}'.format(e))

        # Parse the entity representing the current user.
        self_entity = schemas.CLIENT_GET_SELF_INFO_RESPONSE.parse(
            data_dict['ds:20'][0]
        ).self_entity

        # Parse every existing conversation's state, including participants.
        initial_conv_states = schemas.CLIENT_CONVERSATION_STATE_LIST.parse(
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

    def _get_authorization_header(self):
        """Return autorization header for chat API request."""
        # technically, it doesn't matter what the url and time are
        time_msec = int(time.time() * 1000)
        auth_string = '{} {} {}'.format(time_msec, self._get_cookie("SAPISID"),
                                        ORIGIN_URL)
        auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()
        return 'SAPISIDHASH {}_{}'.format(time_msec, auth_hash)

    def _get_cookie(self, name):
        """Return a cookie for raise error if that cookie was not provided."""
        try:
            return self._cookies[name]
        except KeyError:
            raise KeyError("Cookie '{}' is required".format(name))

    def _get_request_header(self):
        """Return request header for chat API request."""
        return [
            [3, 3, self._header_version, self._header_date],
            [self._header_client, self._header_id],
            None,
            "en"
        ]

    def _on_push_data(self, submission):
        """Parse ClientStateUpdate and call the appropriate events."""
        for state_update in parsers.parse_submission(submission):
            self.on_state_update.fire(state_update)

    @gen.coroutine
    def _request(self, endpoint, body_json, use_json=True):
        """Make chat API request."""
        url = 'https://clients6.google.com/chat/v1/{}'.format(endpoint)
        headers = {
            'authorization': self._get_authorization_header(),
            'x-origin': ORIGIN_URL,
            'x-goog-authuser': '0',
            'content-type': 'application/json+protobuf',
        }
        required_cookies = ['SAPISID', 'HSID', 'SSID', 'APISID', 'SID']
        cookies = {cookie: self._get_cookie(cookie)
                   for cookie in required_cookies}
        params = {
            'key': self._api_key,
            'alt': 'json' if use_json else 'protojson',
        }
        res = yield http_utils.fetch(
            url, method='POST', headers=headers, cookies=cookies,
            params=params, data=json.dumps(body_json),
            request_timeout=REQUEST_TIMEOUT, connect_timeout=CONNECT_TIMEOUT
        )
        logger.debug('Response to request for {} was {}:\n{}'
                     .format(endpoint, res.code, res.body))
        if res.code != 200:
            raise ValueError('Request to {} endpoint failed with {}: {}'
                             .format(endpoint, res.code, res.body.decode()))
        return res

    @gen.coroutine
    def getselfinfo(self):
        """Return information about your account."""
        res = yield self._request('contacts/getselfinfo', [
            self._get_request_header(),
            [], []
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def setfocus(self, conversation_id):
        """Set focus (occurs whenever you give focus to a client)."""
        res = yield self._request('conversations/setfocus', [
            self._get_request_header(),
            [conversation_id],
            1,
            20
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def searchentities(self, search_string, max_results):
        """Search for people."""
        res = yield self._request('contacts/searchentities', [
            self._get_request_header(),
            [],
            search_string,
            max_results
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def querypresence(self, chat_id):
        """Check someone's presence status."""
        res = yield self._request('presence/querypresence', [
            self._get_request_header(),
            [
                [chat_id]
            ],
            [1, 2, 5, 7, 8]
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def getentitybyid(self, chat_id_list):
        """Return information about a list of contacts."""
        res = yield self._request('contacts/getentitybyid', [
            self._get_request_header(),
            None,
            [[str(chat_id)] for chat_id in chat_id_list],
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def getconversation(self, conversation_id, num_events,
                        storage_continuation_token, event_timestamp):
        """Return data about a conversation.

        Seems to require both a timestamp and a token from a previous event
        """
        res = yield self._request('conversations/getconversation', [
            self._get_request_header(),
            [
                [conversation_id], [], []
            ],
            True, True, None, num_events,
            [None, storage_continuation_token, event_timestamp]
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def syncallnewevents(self, timestamp):
        """List all events occuring at or after timestamp.

        This method requests protojson rather than json so we have one chat
        message parser rather than two.

        timestamp: datetime.datetime instance specifying the time after
        which to return all events occuring in.

        Raises hangups.NetworkError if the request fails.

        Returns a ClientSyncAllNewEventsResponse.
        """
        try:
            res = yield self._request('conversations/syncallnewevents', [
                self._get_request_header(),
                # last_sync_timestamp
                int(timestamp.timestamp()) * 1000000,
                [], None, [], False, [],
                1048576 # max_response_size_bytes
            ], use_json=False)
        except (httpclient.HTTPError, IOError) as e:
            # In addition to HTTPError, httpclient can raise IOError (which
            # includes socker.gaierror).
            raise exceptions.NetworkError(e)
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

    @gen.coroutine
    def syncrecentconversations(self):
        """List the contents of recent conversations, including messages.

        Similar to syncallnewevents, but appears to return a limited number of
        conversations (20) rather than all conversations in a given date range.
        """
        res = yield self._request('conversations/syncrecentconversations', [
            self._get_request_header(),
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def setchatname(self, conversation_id, name):
        """Set the name of a conversation.

        Raises hangups.NetworkError if the request can not be sent.
        """
        client_generated_id = random.randint(0, 2 ** 32)
        body = [
            self._get_request_header(),
            None,
            name,
            None,
            [[conversation_id], client_generated_id, 1]
        ]
        try:
            res = yield self._request('conversations/renameconversation', body)
        except (httpclient.HTTPError, IOError) as e:
            # In addition to HTTPError, httpclient can raise IOError (which
            # includes socker.gaierror).
            logger.warning('Failed to send message: {}'.format(e))
            raise exceptions.NetworkError(e)
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            logger.warning('renameconversation returned status {}'
                           .format(res_status))
            raise exceptions.NetworkError()

    @gen.coroutine
    def sendeasteregg(self, conversation_id, easteregg):
        """Send a easteregg to a conversation.

        easteregg may not be empty.

        Raises hangups.NetworkError if the easteregg can not be sent.
        """
        body = [
            self._get_request_header(),
            [conversation_id],
            [easteregg, None, 1]
        ]
        try:
            res = yield self._request('conversations/easteregg', body)
        except (httpclient.HTTPError, IOError) as e:
            # In addition to HTTPError, httpclient can raise IOError (which
            # includes socker.gaierror).
            logger.warning('Failed to send easteregg: {}'.format(e))
            raise exceptions.NetworkError(e)
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            logger.warning('easteregg returned status {}'
                           .format(res_status))
            raise exceptions.NetworkError()

    @gen.coroutine
    def sendchatmessage(self, conversation_id, segments):
        """Send a chat message to a conversation.

        conversation_id must be a valid conversation ID. segments must be a
        list of message segments to send, in pblite format.

        Raises hangups.NetworkError if the message can not be sent.
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
        try:
            res = yield self._request('conversations/sendchatmessage', body)
        except (httpclient.HTTPError, IOError) as e:
            # In addition to HTTPError, httpclient can raise IOError (which
            # includes socker.gaierror).
            logger.warning('Failed to send message: {}'.format(e))
            raise exceptions.NetworkError(e)
        # sendchatmessage can return 200 but still contain an error
        res = json.loads(res.body.decode())
        res_status = res['response_header']['status']
        if res_status != 'OK':
            logger.warning('sendchatmessage returned status {}'
                           .format(res_status))
            raise exceptions.NetworkError()
