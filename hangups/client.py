"""Abstract class for writing chat clients."""

# "unused argument" are unavoidable because of obsub events.
# pylint: disable=W0613

from obsub import event
from tornado import ioloop, gen, httpclient, httputil, concurrent
import datetime
import hashlib
import http.cookies
import json
import logging
import random
import re
import time

from hangups import javascript, longpoll
from hangups.longpoll import UserID, User


logger = logging.getLogger(__name__)


# Set the connection timeout low so we fail fast when there's a network
# problem.
CONNECT_TIMEOUT = 10
# Set the request timeout high enough for long-polling (the requests last ~3-4
# minutes), but low enough that we find out fast if there's a network problem.
REQUEST_TIMEOUT = 60*5

ORIGIN_URL = 'https://talkgadget.google.com'


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
    res = yield http_client.fetch(httpclient.HTTPRequest(
        httputil.url_concat(url, params), method=method,
        headers=httputil.HTTPHeaders(headers), body=data,
        streaming_callback=streaming_callback, connect_timeout=CONNECT_TIMEOUT,
        request_timeout=REQUEST_TIMEOUT
    ))
    return res


@concurrent.return_future
def _future_sleep(seconds, callback=None):
    """Return a future that finishes after a given number of seconds."""
    ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=seconds),
                                         callback)


def _parse_sid_response(res):
    """Parse response format for request for new channel SID.

    Returns (SID, header_client, gsessionid).
    """
    sid = None
    header_client = None
    gsessionid = None

    p = longpoll.PushDataParser()
    res = javascript.loads(list(p.get_submissions(res.decode()))[0])
    for segment in res:
        num, message = segment
        if num == 0:
            sid = message[1]
        elif message[0] == 'c':
            type_ = message[1][1][0]
            if type_ == 'cfj':
                header_client = message[1][1][1].split('/')[1]
            elif type_ == 'ei':
                gsessionid = message[1][1][1]

    return(sid, header_client, gsessionid)


def _parse_user_entity(entity):
    """Parse entities returned from the getentitybyid endpoint.

    Raises ValueError if the entity cannot be parsed.
    """
    # Known entity types:
    # GAIA: regular user
    # INVALID: entity does not exist
    entity_type = entity.get('entity_type', None)
    if entity_type != 'GAIA':
        raise ValueError('Cannot parse entity with entity type {}'
                         .format(entity_type))
    try:
        chat_id = entity['id']['chat_id']
        gaia_id = entity['id']['gaia_id']
    except KeyError:
        raise ValueError('Cannot determine entity ID')
    properties = entity.get('properties', {})
    return {
        'chat_id': chat_id,
        'gaia_id': gaia_id,
        'first_name': properties.get('first_name', 'UNKNOWN'),
        'full_name': properties.get('display_name', 'UNKNOWN'),
    }


class ConversationList(object):
    """Wrapper around Client that presents a list of Conversations."""

    def __init__(self, client):
        self._client = client
        self._conv_dict = client.initial_conversations
        logger.info('ConversationList initialized with {} conversation(s)'
                    .format(len(self._conv_dict)))
        # Register event handlers:
        self._client.on_message += self._on_message
        self._client.on_typing += self._on_typing
        self._client.on_focus += self._on_focus
        self._client.on_conversation += self._on_conversation

    # TODO: Avoid this routing by adding observers when conversations are
    # created.
    def _on_message(self, client, conv_id, user_id, timestamp, text):
        """Route on_message event to appropriate Conversation."""
        self.get(conv_id).on_message(user_id, timestamp, text)

    def _on_typing(self, client, conv_id, user_id, timestamp, status):
        """Route on_typing event to appropriate Conversation."""
        self.get(conv_id).on_typing(user_id, timestamp, status)

    def _on_focus(self, client, conv_id, user_id, timestamp, status, device):
        """Route on_focus event to appropriate Conversation."""
        self.get(conv_id).on_focus(user_id, timestamp, status, device)

    def _on_conversation(self, client, conv_id, participants):
        """Route on_conversation event to appropriate Conversation."""
        self.get(conv_id).on_conversation(participants)

    def get_all(self):
        """Return list of all Conversations."""
        return list(self._conv_dict.values())

    def get(self, conv_id):
        """Return a Conversation from its ID.

        Raises KeyError if the conversation ID is invalid.
        """
        return self._conv_dict[conv_id]


class Conversation(object):
    """Wrapper around Client for working with a single chat conversation."""

    def __init__(self, client, id_, users, last_modified):
        self._client = client
        self._id = id_ # ConversationID
        self._users = users # [User]
        self._last_modified = last_modified # datetime

    @property
    def id_(self):
        """Return the Conversation's ID."""
        return self._id

    @property
    def users(self):
        """Return the list of Users participating in the Conversation."""
        return list(self._users)

    def get_user(self, user_id):
        """Return a participating use by UserID."""
        # TODO: make self._users a dict instead?
        return [user for user in self._users if user.id_ == user_id][0]

    @property
    def last_modified(self):
        """Return the timestamp of when the conversation was last modified."""
        return self._last_modified

    @gen.coroutine
    def send_message(self, text):
        """Send a message to this conversation."""
        yield self._client.sendchatmessage(self._id, text)

    @event
    def on_message(self, user_id, timestamp, text):
        """Event called when a new message arrives."""
        logger.info('Triggered event Conversation.on_message')

    @event
    def on_typing(self, user_id, timestamp, status):
        """Event called when a user starts or stops typing."""
        logger.info('Triggered event Conversation.on_typing')

    @event
    def on_focus(self, user_id, timestamp, status, device):
        """Event called when a user changes focus on a conversation."""
        logger.info('Triggered event Conversation.on_focus')

    @event
    def on_conversation(self, participants):
        """Event called when a conversation updates."""
        logger.info('Triggered event Conversation.on_conversation')


# TODO: This class isn't really being used yet.
class UserList(object):
    """Allows querying known chat users."""

    def __init__(self, client):
        self._client = client
        self._users = dict(client.initial_users)
        self._self_user_id = client.self_user_id
        logger.info('UserList initialized with {} user(s)'
                    .format(len(self._users)))

    def get_self_id(self):
        """Return UserID of the logged in user."""
        return self._self_user_id

    @gen.coroutine
    def get_self_user(self):
        """Return User who is logged in."""
        yield self.get_users([self._self_user_id])[0]

    @gen.coroutine
    def get_user(self, user_id):
        """Wrapper for get_users for getting a single user."""
        users = yield self.get_users([user_id])
        return users[0]

    @gen.coroutine
    def get_users(self, user_id_list):
        """Gets Users by a list of IDs.

        Returns a dict user_id -> User.

        Until we can find all users reliably, this method will return dummy
        users rather than raising an exception when a user can't be found.
        """
        # Request any new user IDs if necessary
        unknown_user_ids = set(user_id_list) - set(self._users.keys())
        if unknown_user_ids:
            logger.info('Need to request users: {}'.format(unknown_user_ids))
            yield self._request_users(unknown_user_ids)

        # Return Users and add dummies for Users we couldn't find.
        return {user_id: (self._users[user_id] if user_id in self._users
                          else self._make_dummy_user(user_id))
                for user_id in user_id_list}

    def _make_dummy_user(self, user_id):
        """Return a dummy User and add it to the list."""
        logger.info('Creating dummy user for {}'.format(user_id))
        user = User(id_=user_id, full_name='UNKNOWN', first_name='UNKNOWN',
                    is_self=(user_id == self._self_user_id))
        self._users[user_id] = user
        return user

    @gen.coroutine
    def _request_users(self, user_id_list):
        """Make request for a list of users by ID."""
        res = yield self._client._getentitybyid([user_id.chat_id for user_id
                                                 in user_id_list])
        for entity in res['entity']:
            try:
                user = _parse_user_entity(entity)
            except ValueError as e:
                logger.warning('Failed to parse user entity: {}: {}'
                               .format(e, entity))
            else:
                user_id = UserID(chat_id=user['chat_id'],
                                 gaia_id=user['gaia_id'])
                self._users[user_id] = User(
                    id_=user_id, full_name=user['full_name'],
                    first_name=user['first_name'],
                    is_self=(user_id == self._self_user_id)
                )


class Client(object):
    """Instant messaging client for Hangouts.

    Maintains a connections to the servers, emits events, and accepts commands.
    """

    def __init__(self, cookies):
        """Create new client.

        cookies is a dictionary of authentication cookies.
        """
        self._cookies = cookies

        self._push_parser = None

        # These are available after ConnectionEvent:
        self.initial_users = None # {UserID: User}
        self.self_user_id = None # UserID
        self.initial_conversations = None # {conv_id: Conversation}

        # discovered automatically:

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
    # Public methods
    ##########################################################################

    @gen.coroutine
    def connect(self):
        """Connect to the server and receive events."""
        yield self._init_talkgadget_1()
        self.on_connect()
        yield self._run_forever()

    ##########################################################################
    # Events
    ##########################################################################

    @event
    def on_connect(self):
        """Event called when the client connects for the first time."""
        logger.info('Triggered event Client.on_connect')

    @event
    def on_disconnect(self):
        """Event called when the client is disconnected from the server."""
        logger.info('Triggered event Client.on_disconnect')

    @event
    def on_message(self, conv_id, user_id, timestamp, text):
        """Event called when a new message arrives."""
        logger.info('Triggered event Client.on_message')

    @event
    def on_typing(self, conv_id, user_id, timestamp, status):
        """Event called when a user starts or stops typing."""
        logger.info('Triggered event Client.on_typing')

    @event
    def on_focus(self, conv_id, user_id, timestamp, status, device):
        """Event called when a user changes focus on a conversation."""
        logger.info('Triggered event Client.on_focus')

    @event
    def on_conversation(self, conv_id, participants):
        """Event called when a conversation updates."""
        logger.info('Triggered event Client.on_conversation')

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

        # build dict of conversations and their participants
        initial_conversations = {}
        self.initial_users = {} # {UserID: User}

        # add self to the contacts
        self_contact = data_dict['ds:20'][0][2]
        self.self_user_id = UserID(chat_id=self_contact[8][0],
                                   gaia_id=self_contact[8][1])
        self.initial_users[self.self_user_id] = User(
            id_=self.self_user_id, full_name=self_contact[9][1],
            first_name=self_contact[9][2], is_self=True
        )

        conversations = data_dict['ds:19'][0][3]
        for c in conversations:
            id_ = c[1][0][0]
            participants = c[1][13]
            last_modified = c[1][3][12]
            initial_conversations[id_] = {
                'participants': [],
                'last_modified': last_modified,
            }
            for p in participants:
                user_id = UserID(chat_id=p[0][0], gaia_id=p[0][1])
                initial_conversations[id_]['participants'].append(
                    user_id
                )
                # Add the user to our list of contacts if their name is
                # present. This is a hack to deal with some contacts not being
                # found via the other methods.
                # TODO We should note who these users are and try to request
                # them.
                if len(p) > 1:
                    display_name = p[1]
                    self.initial_users[user_id] = User(
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
            user_id = UserID(chat_id=c[0][8][0], gaia_id=c[0][8][1])
            self.initial_users[user_id] = User(
                id_=user_id, full_name=c[0][9][1], first_name=c[0][9][2],
                is_self=(user_id == self.self_user_id)
            )

        # Create a dict of the known conversations.
        self.initial_conversations = {conv_id: Conversation(
            self, conv_id, [self.initial_users[user_id] for user_id
                            in conv_info['participants']],
            conv_info['last_modified'],
        ) for conv_id, conv_info in initial_conversations.items()}

    @gen.coroutine
    def _run_forever(self):
        """Make repeated long-polling requests to receive events.

        This method only returns when the connection has been closed due to an
        error.
        """
        MAX_RETRIES = 5  # maximum number of times to retry after a failure
        retries = MAX_RETRIES # number of remaining retries
        need_new_sid = True  # whether a new SID is needed

        while retries >= 0:
            # After the first failed retry, back off exponentially longer after
            # each attempt.
            if retries + 1 < MAX_RETRIES:
                backoff_seconds = 2 ** (MAX_RETRIES - retries)
                logger.info('Backing off for {} seconds'
                            .format(backoff_seconds))
                yield _future_sleep(backoff_seconds)

            # Request a new SID if we don't have one yet, or the previous one
            # became invalid.
            if need_new_sid:
                # TODO: error handling
                yield self._fetch_channel_sid()
                need_new_sid = False
            # Clear any previous push data, since if there was an error it
            # could contain garbage.
            self._push_parser = longpoll.PushDataParser()
            try:
                yield self._longpoll_request()
            except httpclient.HTTPError as e:
                # An error occurred, so decrement the number of retries.
                retries -= 1
                if e.code == 400 and e.response.reason == 'Unknown SID':
                    logger.error('Long-polling request failed because SID '
                                 'became invalid. Will attempt to recover.')
                    need_new_sid = True
                elif e.code == 599:
                    # TODO: Depending on how the connection is lost, it may
                    # hang for a long time before an exception is raised, so we
                    # need a another way of determining that the connection is
                    # alive.
                    logger.error('Long-polling request failed because '
                                 'connection was closed. Will attempt to '
                                 'recover.')
                else:
                    logger.error('Long-polling request failed for unknown '
                                 'reason: {}'.format(e))
                    break # Do not retry.
            else:
                # The connection closed successfully, so reset the number of
                # retries.
                retries = MAX_RETRIES

            # TODO: If there was an error, messages could be lost in this time.

        logger.error('Ran out of retries for long-polling request')
        self.on_disconnect()

    @gen.coroutine
    def _fetch_channel_sid(self):
        """Request a new session ID for the push channel."""
        logger.info('Requesting new session ID...')
        url = 'https://talkgadget.google.com{}bind'.format(self._channel_path)
        params = {
            'VER': 8,
            'clid': self._clid,
            'ec': self._channel_ec_param,
            'RID': 81187, # TODO: "request ID"? should probably increment
            # Required if we want our client to be called "AChromeExtension":
            'prop': self._channel_prop_param,
        }
        res = yield _fetch(url, method='POST', cookies=self._cookies,
                           params=params, data='count=0')
        logger.debug('Fetch SID response:\n{}'.format(res.body))
        if res.code != 200:
            # TODO use better exception
            raise ValueError("SID fetch request failed with {}: {}"
                             .format(res.code, res.raw.read()))
        # TODO: handle errors here
        self._channel_session_id, self._header_client, self._gsessionid = (
            _parse_sid_response(res.body)
        )
        logger.info('Received new session ID: {}'
                    .format(self._channel_session_id))

    @gen.coroutine
    def _longpoll_request(self):
        """Open a long-polling request to receive push events.

        Raises HTTPError.
        """
        def streaming_callback(data):
            """Make the callback run a coroutine with exception handling."""
            future = self._on_push_data(data)
            ioloop.IOLoop.instance().add_future(future, lambda f: f.result())
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
        URL = 'https://talkgadget.google.com/u/0/talkgadget/_/channel/bind'
        logger.info('Opening new long-polling request')
        res = yield _fetch(URL, params=params, cookies=self._cookies,
                           streaming_callback=streaming_callback)
        return res

    @gen.coroutine
    def _on_push_data(self, data_bytes):
        """Parse push data and trigger events."""
        logger.debug('Received push data:\n{}'.format(data_bytes))
        for event in self._push_parser.get_events(data_bytes.decode()):
            logger.info('Received event: {}'.format(event))
            # TODO: Refactor so *Event classes aren't needed anymore and we
            # don't need this boilerplate.
            if isinstance(event, longpoll.NewMessageEvent):
                self.on_message(event.conv_id, event.sender_id,
                                event.timestamp, event.text)
            elif isinstance(event, longpoll.TypingChangedEvent):
                self.on_typing(event.conv_id, event.user_id, event.timestamp,
                               event.typing_status)
            elif isinstance(event, longpoll.FocusChangedEvent):
                self.on_focus(event.conv_id, event.user_id, event.timestamp,
                              event.focus_status, event.focus_device)
            elif isinstance(event, longpoll.ConvChangedEvent):
                self.on_conversation(event.conv_id, event.participants)

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

    @gen.coroutine
    def _request(self, endpoint, body_json):
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
    def sendchatmessage(self, conversation_id, message, is_bold=False,
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
