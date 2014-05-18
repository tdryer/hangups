"""Abstract class for writing chat clients."""

from collections import namedtuple
from tornado import ioloop, gen, httpclient, httputil
import hashlib
import http.cookies
import json
import logging
import random
import re
import time

from hangups import javascript, longpoll


logger = logging.getLogger(__name__)


Conversation = namedtuple('Conversation', ['id_', 'user_list', 'message_list'])
Message = namedtuple('Message', ['text', 'timestamp', 'user_gaia_id',
                                 'user_chat_id'])
User = namedtuple('User', ['chat_id', 'gaia_id', 'name'])


@gen.coroutine
def _fetch(url, method='GET', params=None, headers=None, cookies=None,
           data=None, streaming_callback=None):
    """Wrapper for tornado.httpclient.AsyncHTTPClient.fetch."""
    if headers is None:
        headers = {}
    if params is not None:
        url = httputil.url_concat(url, params)
    if cookies is not None:
        # abuse SimpleCookie to escape our cookies for us
        simple_cookies = http.cookies.SimpleCookie(cookies)
        headers['cookie'] = '; '.join(val.output(header='')[1:]
                                      for val in simple_cookies.values())
    http_client = httpclient.AsyncHTTPClient()
    # set the timeout nice and nice for long-polling
    res = yield http_client.fetch(httpclient.HTTPRequest(
        httputil.url_concat(url, params), method=method,
        headers=httputil.HTTPHeaders(headers), body=data,
        streaming_callback=streaming_callback, request_timeout=60*60
    ))
    return res


class HangupsClient(object):
    """Abstract class for writing chat clients.

    Designed to allow building a chat client by subclassing the abstract
    methods. If __init__ is subclassed, super().__init__() must be called.
    """

    def __init__(self):
        self._cookies = None
        self._origin_url = None
        self._push_parser = None

        # (chat_id, gaia_id) -> User instance
        self._users = {}
        # conversation_id -> Conversation instance
        self._conversations = {}

        # discovered automatically:

        self._initial_conversations = None
        self._initial_contacts = None
        # the api key sent with every request
        self._api_key = None
        # fields sent in request headers
        self._header_date = None
        self._header_version = None
        self._header_id = None
        self._header_client = None
        # parameters related talkgadget channel requests
        self._channel_path = None
        self._gsessionid = None
        self._clid = None
        self._channel_ec_param = None
        self._channel_prop_param = None
        self._channel_session_id = None

    ##########################################################################
    # Abstract methods
    ##########################################################################

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        """Abstract method called when a new message is received."""
        pass

    @gen.coroutine
    def on_focus_update(self, conversation_id, user_ids, focus_status,
                        focus_device):
        """Abstract method called when conversation focus changes."""
        pass

    @gen.coroutine
    def on_typing_update(self, conversation_id, user_ids, typing_status):
        """Abstract method called when someone starts or stops typing."""
        pass

    @gen.coroutine
    def on_connect(self, conversations, contacts):
        """Abstract method called when push connection is established."""
        pass

    @gen.coroutine
    def on_disconnect(self):
        """Abstract method called when push connection is disconnected."""
        pass

    ##########################################################################
    # Public methods
    ##########################################################################

    def get_user(self, chat_id, gaia_id):
        """Return a User instance from its ids.

        Raises KeyError if the user does not exist.
        """
        # TODO: we could also make a separate query if the user is not cached
        try:
            return self._users[(chat_id, gaia_id)]
        except KeyError:
            return User(0, 0, 'Unknown User')

    @gen.coroutine
    def send_message(self, conversation_id, text):
        """Send a message to a conversation."""
        yield self._sendchatmessage(conversation_id, text)

    @gen.coroutine
    def connect(self, cookies, origin_url='https://talkgadget.google.com'):
        """Initialize to gather connection parameters."""
        self._cookies = cookies
        self._origin_url = origin_url
        yield self._init_talkgadget_1()
        yield self._init_talkgadget_2()

    @gen.coroutine
    def run_forever(self):
        """Block forever to receive chat events."""
        url = 'https://talkgadget.google.com/u/0/talkgadget/_/channel/bind'
        params = {
            'VER': 8,
            'clid': self._clid,
            'prop': self._channel_prop_param,
            'ec': self._channel_ec_param,
            'gsessionid': self._gsessionid,
            'RID': 'rpc',
            't': 1, # trial
            'SID': self._channel_session_id,
            'CI': 0,
        }
        def streaming_callback(data):
            """Make the callback run a coroutine with exception handling."""
            future = self._on_push_data(data)
            ioloop.IOLoop.instance().add_future(future, lambda f: f.result())

        is_connected = False
        MIN_CONNECT_TIME = 60
        # time we last tried to connect in seconds
        last_connect_time = 0

        while True:
            # If it's been too short a time since we last connected, assume
            # something has gone wrong.
            if time.time() - last_connect_time < MIN_CONNECT_TIME:
                logging.error('Disconnecting because last long-polling '
                              'request was too short.')
                break
            else:
                logging.info('Opening new long-polling request')
            last_connect_time = time.time()

            self._push_parser = longpoll.PushDataParser()
            fetch_future = _fetch(url, params=params, cookies=self._cookies,
                                  streaming_callback=streaming_callback)
            # TODO: At this join we are "connected", but we don't know if the
            # request was successful.
            if not is_connected:
                yield self.on_connect(self._initial_conversations,
                                      self._initial_contacts)
                is_connected = True

            # Wait for response to finish.
            try:
                yield fetch_future
            except httpclient.HTTPError as e:
                logging.error('Long-polling request failed: {}'.format(e))
                break

        yield self.on_disconnect()

    ##########################################################################
    # Private methods
    ##########################################################################

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
        res = yield _fetch(url, cookies=self._cookies, params=params,
                           headers=headers)
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
                data_dict[data['key']] = data['data']
            except ValueError as e:
                # not everything will be parsable, but we don't care
                logger.debug('Failed to parse JavaScript: {}\n{}'.format(e, data))

        # TODO: handle errors here
        self._api_key = data_dict['ds:7'][0][2]
        self._header_date = data_dict['ds:2'][0][4]
        self._header_version = data_dict['ds:2'][0][6]
        self._header_id = data_dict['ds:4'][0][7]
        self._channel_path = data_dict['ds:4'][0][1]
        self._gsessionid = data_dict['ds:4'][0][3]
        self._clid = data_dict['ds:4'][0][7]
        self._channel_ec_param = data_dict['ds:4'][0][4]
        self._channel_prop_param = data_dict['ds:4'][0][5]

        # build dict of conversations and their participants
        self._initial_conversations = {}
        conversations = data_dict['ds:19'][0][3]
        for c in conversations:
            id_ = c[1][0][0]
            participants = c[1][13]
            self._initial_conversations[id_] = {'participants': []}
            for p in participants:
                user_ids = tuple(p[0])
                self._initial_conversations[id_]['participants'].append(
                    user_ids
                )
        logging.info('Found {} conversations'
                     .format(len(self._initial_conversations)))

        # build dict of contacts and their names
        self._initial_contacts = {}
        contacts_main = data_dict['ds:21'][0]
        # contacts_main[2] has some, but the format is slightly different
        contacts = (contacts_main[4][2] + contacts_main[5][2] +
                    contacts_main[6][2] + contacts_main[7][2] +
                    contacts_main[8][2])
        for c in contacts:
            user_ids = tuple(c[0][8])
            full_name = c[0][9][1]
            first_name = c[0][9][2]
            self._initial_contacts[user_ids] = {
                'first_name': first_name,
                'full_name': full_name,
            }
        logging.info('Found {} contacts'.format(len(self._initial_contacts)))

        # add self to the contacts
        self_contact = data_dict['ds:20'][0][2]
        self._initial_contacts[tuple(self_contact[8])] = {
            'first_name': self_contact[9][2],
            'full_name': self_contact[9][1],
        }

    @gen.coroutine
    def _init_talkgadget_2(self):
        """Make second talkgadget request and parse response."""
        url = 'https://talkgadget.google.com{}bind'.format(self._channel_path)
        params = {
            'VER': 8,
            'clid': self._clid,
            'prop': self._channel_prop_param,
            'ec': self._channel_ec_param,
            'gsessionid': self._gsessionid,
            'RID': 81187, # TODO
            'CVER': 1,
            't': 1, # trial
        }
        res = yield _fetch(url, method='POST', cookies=self._cookies,
                           params=params, data='count=0')
        logger.debug('Second talkgadget request result:\n{}'.format(res.body))
        if res.code != 200:
            raise ValueError("Second talkgadget request failed with {}: {}"
                             .format(res.code, res.raw.read()))
        p = longpoll.PushDataParser()
        res = javascript.loads(list(p.get_submissions(res.body.decode()))[0])
        # TODO: handle errors here
        val = res[3][1][1][1][1] # ex. foo@bar.com/AChromeExtensionBEEFBEEF
        self._header_client = val.split('/')[1] # ex. AChromeExtensionwBEEFBEEF
        self._channel_session_id = res[0][1][1]

    @gen.coroutine
    def _on_push_data(self, data_bytes):
        """Parse push data and call self._on_submsg for each submessage."""
        logger.debug('Received push data:\n{}'.format(data_bytes))

        message = None
        conversation_id = None

        # Process all new data before making any callbacks, so we won't make
        # any redundant requests for data.
        for event in self._push_parser.get_events(data_bytes.decode()):

            event_type = event['event_type']
            if event_type == 'chat_message':
                message = Message(text=event['text'],
                                  user_chat_id=event['sender_ids'][0],
                                  user_gaia_id=event['sender_ids'][1],
                                  timestamp=event['timestamp'])
                conversation_id = event['conversation_id']
            elif event_type == 'conversation_update':
                # TODO: this may be higher-level functionality than we want
                conversation = Conversation(
                    id_=event['conversation_id'],
                    user_list=event['participants'].keys(),
                    message_list=[]
                )
                if event['conversation_id'] not in self._conversations:
                    self._conversations[event['conversation_id']] = conversation
                    logger.info('Found new conversation: {}'
                                .format(conversation))
                else:
                    logger.info('Found existing conversation')
                for (chat_id, gaia_id), name in event['participants'].items():
                    user = User(chat_id=chat_id, gaia_id=gaia_id,
                                name=name)
                    if (chat_id, gaia_id) not in self._users:
                        self._users[(chat_id, gaia_id)] = user
                        logger.info('Added new user: {}'.format(user))
                    else:
                        logger.info('Found existing user')
            elif event_type == 'focus_update':
                yield self.on_focus_update(
                    event['conversation_id'], event['user_ids'],
                    event['focus_status'], event['focus_device']
                )
            elif event_type == 'typing_update':
                yield self.on_typing_update(
                    event['conversation_id'], event['user_ids'],
                    event['typing_status']
                )

        # Make callbacks for new data.
        if message is not None:
            yield self.on_message_receive(conversation_id, message)

    def _get_authorization_header(self):
        """Return autorization header for chat API request."""
        # technically, it doesn't matter what the url and time are
        time_msec = int(time.time() * 1000)
        auth_string = '{} {} {}'.format(time_msec, self._get_cookie("SAPISID"),
                                        self._origin_url)
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

    @gen.coroutine
    def _request(self, endpoint, body_json):
        """Make chat API request."""
        url = 'https://clients6.google.com/chat/v1/{}'.format(endpoint)
        headers = {
            'authorization': self._get_authorization_header(),
            'x-origin': self._origin_url,
            'x-goog-authuser': '0',
            'content-type': 'application/json+protobuf',
        }
        required_cookies = ['SAPISID', 'HSID', 'SSID', 'APISID', 'SID']
        cookies = {cookie: self._get_cookie(cookie)
                   for cookie in required_cookies}
        params = {
            'key': self._api_key,
            'alt': 'json', # json or protojson
        }
        res = yield _fetch(url, method='POST', headers=headers,
                           cookies=cookies, params=params,
                           data=json.dumps(body_json))
        logger.debug('Response to request for {} was {}:\n{}'
                     .format(endpoint, res.code, res.body))
        if res.code != 200:
            raise ValueError('Request to {} endpoint failed with {}: {}'
                             .format(endpoint, res.code, res.body.decode()))
        return res

    @gen.coroutine
    def _getselfinfo(self):
        """Return information about your account."""
        res = yield self._request('contacts/getselfinfo', [
            self._get_request_header(),
            [], []
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def _setfocus(self, conversation_id):
        """Set focus (occurs whenever you give focus to a client)."""
        res = yield self._request('conversations/setfocus', [
            self._get_request_header(),
            [conversation_id],
            1,
            20
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def _searchentities(self, search_string, max_results):
        """Search for people."""
        res = yield self._request('contacts/searchentities', [
            self._get_request_header(),
            [],
            search_string,
            max_results
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def _querypresence(self, chat_id):
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
    def _getentitybyid(self, chat_id_list):
        """Return information about a list of contacts."""
        res = yield self._request('contacts/getentitybyid', [
            self._get_request_header(),
            None,
            [[str(chat_id)] for chat_id in chat_id_list],
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def _getconversation(self, conversation_id, num_events,
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
    def _syncallnewevents(self, after_timestamp):
        """List all events occuring at or after timestamp."""
        res = yield self._request('conversations/syncallnewevents', [
            self._get_request_header(),
            after_timestamp,
            [], None, [], False, [],
            1048576
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def _syncrecentconversations(self):
        """List the contents of recent conversations, including messages.

        Similar to syncallnewevents, but appears to return a limited number of
        conversations (20) rather than all conversations in a given date range.
        """
        res = yield self._request('conversations/syncrecentconversations', [
            self._get_request_header(),
        ])
        return json.loads(res.body.decode())

    @gen.coroutine
    def _sendchatmessage(self, conversation_id, message, is_bold=False,
                         is_italic=False, is_strikethrough=False,
                         is_underlined=False):
        """Send a chat message to a conversation."""
        client_generated_id = random.randint(0, 2**32)
        res = yield self._request('conversations/sendchatmessage', [
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
        ])
        return json.loads(res.body.decode())
