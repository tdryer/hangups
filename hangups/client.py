"""Abstract class for writing chat clients."""

from tornado import gen, httpclient, ioloop
import hashlib
import json
import logging
import random
import re
import time

from hangups import (javascript, parsers, exceptions, http_utils, channel,
                     event, schemas, conversation, user)

logger = logging.getLogger(__name__)
ORIGIN_URL = 'https://talkgadget.google.com'
# Set the connection and request timeouts low so we fail fast when there's a
# network problem.
CONNECT_TIMEOUT = 10
REQUEST_TIMEOUT = 10


class Client(object):
    """Instant messaging client for Hangouts.

    Maintains a connections to the servers, emits events, and accepts commands.
    """

    def __init__(self, cookies):
        """Create new client.

        cookies is a dictionary of authentication cookies.
        """

        # Event fired when the client connects for the first time with
        # arguments ().
        self.on_connect = event.Event('Client.on_connect')
        # Event fired when the client reconnects after being disconnected with
        # arguments ().
        self.on_reconnect = event.Event('Client.on_reconnect')
        # Event fired when the client is disconnected with arguments ().
        self.on_disconnect = event.Event('Client.on_disconnect')
        # Event fired when a ClientStateUpdate arrives with arguments
        # (state_update).
        self.on_state_update = event.Event('Client.on_state_update')
        # Event fired when a ClientEventNotification arrives with arguments
        # (event_notification).
        self.on_event_notification = event.Event(
            'Client.on_event_notification'
        )

        self._cookies = cookies
        self._sync_timestamp = None  # datetime.datetime

        # These are instantiated after ConnectionEvent:
        self.initial_users = None # {UserID: User}
        self.self_user_id = None # UserID
        self.initial_conv_states = None # [ClientConversationState]

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
        yield self._init_talkgadget_1()
        self._channel = channel.Channel(self._cookies, self._channel_path,
                                        self._clid, self._channel_ec_param,
                                        self._channel_prop_param)
        sync_f = lambda: ioloop.IOLoop.instance().add_future(
            self._sync_chat_messages(), lambda f: f.result()
        )
        self._channel.on_connect.add_observer(sync_f)
        self._channel.on_connect.add_observer(self.on_connect.fire)
        self._channel.on_reconnect.add_observer(sync_f)
        self._channel.on_reconnect.add_observer(self.on_reconnect.fire)
        self._channel.on_disconnect.add_observer(self.on_disconnect.fire)
        self._channel.on_message.add_observer(self._on_push_data)
        yield self._channel.listen()

    ##########################################################################
    # Private methods
    ##########################################################################

    @gen.coroutine
    def _sync_chat_messages(self):
        """Sync chat messages since self._sync_timestamp."""
        logger.info('Syncing messages since {}'.format(self._sync_timestamp))
        res = yield self.syncallnewevents(self._sync_timestamp)

        # Parse chat message from response and fire on_message event for each
        # new chat message.
        conversation_state = res[3]
        for conv in conversation_state:
            events = conv[2]
            for msg in events:
                try:
                    ev_notif = schemas.CLIENT_EVENT_NOTIFICATION.parse([msg])
                except ValueError as e:
                    logger.warning('Failed to parse ClientEvent: {}'.format(e))
                else:
                    # Workaround for syncallnewevents timestamp being
                    # inclusive:
                    timestamp = parsers.from_timestamp(ev_notif.event.timestamp)
                    if timestamp > self._sync_timestamp:
                        self.on_event_notification.fire(ev_notif)

        self._sync_timestamp = parsers.from_timestamp(int(res[1][4]))

    @gen.coroutine
    def _init_talkgadget_1(self):
        """Make first talkgadget request and parse response.

        The response body is a HTML document containing a series of script tags
        containing JavaScript object. We need to parse the object to get at the
        data.
        """
        url = 'https://talkgadget.google.com/u/0/talkgadget/_/chat'
        params = {
            'prop': 'aChromeExtension',
            'fid': 'gtn-roster-iframe-id',
            'ec': '["ci:ec",true,true,false]',
        }
        headers = {
            # appears to require a browser user agent
            'user-agent': (
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
                '(KHTML, like Gecko) Chrome/34.0.1847.132 Safari/537.36'
            ),
        }
        res = yield http_utils.fetch(
            url, cookies=self._cookies, params=params, headers=headers,
            connect_timeout=CONNECT_TIMEOUT, request_timeout=REQUEST_TIMEOUT
        )
        logger.debug('First talkgadget request result:\n{}'.format(res.body))
        if res.code != 200:
            raise ValueError("First talkgadget request failed with {}: {}"
                             .format(res.code, res.body))
        res = res.body.decode()

        # Parse the response by using a regex to find all the JS objects, and
        # parsing them.
        res = res.replace('\n', '')
        regex = re.compile(
            r"(?:<script>AF_initDataCallback\((.*?)\);</script>)"
        )
        data_dict = {}
        for data in regex.findall(res):
            try:
                data = javascript.loads(data)
                # pylint: disable=invalid-sequence-index
                data_dict[data['key']] = data['data']
            except ValueError as e:
                # not everything will be parsable, but we don't care
                logger.debug('Failed to parse JavaScript: {}\n{}'
                             .format(e, data))

        # TODO: handle errors here
        self._api_key = data_dict['ds:7'][0][2]
        self._header_date = data_dict['ds:2'][0][4]
        self._header_version = data_dict['ds:2'][0][6]
        self._header_id = data_dict['ds:4'][0][7]
        self._channel_path = data_dict['ds:4'][0][1]
        self._clid = data_dict['ds:4'][0][7]
        self._channel_ec_param = data_dict['ds:4'][0][4]
        self._channel_prop_param = data_dict['ds:4'][0][5]
        self._sync_timestamp = parsers.from_timestamp(
            data_dict['ds:21'][0][1][4]
        )

        # add self to the contacts
        self_contact = data_dict['ds:20'][0][2]
        self.self_user_id = user.UserID(chat_id=self_contact[8][0],
                                        gaia_id=self_contact[8][1])
        self.initial_users = {
            self.self_user_id: user.User(
                id_=self.self_user_id, full_name=self_contact[9][1],
                first_name=self_contact[9][2], is_self=True
            )
        }

        # We get every conversation's 20 most recent events.
        self.initial_conv_states = schemas.CLIENT_CONVERSATION_STATE_LIST.parse(
            data_dict['ds:19'][0][3]
        )
        # Add the participant to our list of contacts as a fallback, in
        # case they can't be found later by other methods.
        fallback_users = {}
        for conv_state in self.initial_conv_states:
            for participant in conv_state.conversation.participant_data:
                user_id = user.UserID(chat_id=participant.id_.chat_id,
                                      gaia_id=participant.id_.gaia_id)
                # fallback_name can be None, so default to "Unknown"
                display_name = (participant.fallback_name
                                if participant.fallback_name is not None
                                else "Unknown")
                fallback_users[user_id] = user.User(
                    id_=user_id, first_name=display_name.split()[0],
                    full_name=display_name,
                    is_self=(user_id == self.self_user_id)
                )

        # build dict of contacts and their names (doesn't include users not in
        # contacts)
        contacts_main = data_dict['ds:21'][0]
        # contacts_main[2] has some, but the format is slightly different
        contacts = (contacts_main[4][2] + contacts_main[5][2] +
                    contacts_main[6][2] + contacts_main[7][2] +
                    contacts_main[8][2])
        for c in contacts:
            user_id = user.UserID(chat_id=c[0][8][0], gaia_id=c[0][8][1])
            self.initial_users[user_id] = user.User(
                id_=user_id, full_name=c[0][9][1], first_name=c[0][9][2],
                is_self=(user_id == self.self_user_id)
            )
        for user_id, user_ in fallback_users.items():
            if user_id not in self.initial_users:
                logging.warning('Using fallback user: {}'.format(user_))
                self.initial_users[user_id] = user_

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
            if state_update.event_notification is not None:
                self._sync_timestamp = parsers.from_timestamp(
                    state_update.event_notification.event.timestamp
                )
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
        """
        try:
            res = yield self._request('conversations/syncallnewevents', [
                self._get_request_header(),
                int(timestamp.timestamp()) * 1000000,
                [], None, [], False, [],
                1048576 # max response size? (number of bytes in a MB)
            ], use_json=False)
        except (httpclient.HTTPError, IOError) as e:
            # In addition to HTTPError, httpclient can raise IOError (which
            # includes socker.gaierror).
            raise exceptions.NetworkError(e)
        # can return 200 but still contain an error
        res = javascript.loads(res.body.decode())
        res_status = res[1][0]
        if res_status != 1:
            raise exceptions.NetworkError('Response status is \'{}\''
                                          .format(res_status))
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
    def sendchatmessage(self, conversation_id, message, is_bold=False,
                        is_italic=False, is_strikethrough=False,
                        is_underlined=False):
        """Send a chat message to a conversation.

        message may not be empty.

        Raises hangups.NetworkError if the message can not be sent.
        """
        client_generated_id = random.randint(0, 2**32)
        body = [
            self._get_request_header(),
            None, None, None, [],
            [
                [
                    [0, message, [is_bold, is_italic, is_strikethrough,
                                  is_underlined]]
                ],
                []
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
