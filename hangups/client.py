"""Abstract class for writing chat clients."""

from tornado import gen, httpclient, ioloop
import hashlib
import json
import logging
import random
import re
import time

from hangups import javascript, parsers, exceptions, http_utils, channel, event

logger = logging.getLogger(__name__)
ORIGIN_URL = 'https://talkgadget.google.com'
# Set the connection and request timeouts low so we fail fast when there's a
# network problem.
CONNECT_TIMEOUT = 10
REQUEST_TIMEOUT = 10


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
        self._client.on_message.add_observer(self._on_message)
        self._client.on_typing.add_observer(self._on_typing)
        self._client.on_focus.add_observer(self._on_focus)
        self._client.on_conversation.add_observer(self._on_conversation)

    def _on_message(self, chat_message):
        """Route on_message event to appropriate Conversation."""
        self.get(chat_message.conv_id).on_message.fire(chat_message)

    def _on_typing(self, typing_message):
        """Route on_typing event to appropriate Conversation."""
        self.get(typing_message.conv_id).on_typing.fire(typing_message)

    def _on_focus(self, focus_message):
        """Route on_focus event to appropriate Conversation."""
        self.get(focus_message.conv_id).on_focus.fire(focus_message)

    def _on_conversation(self, conversation_message):
        """Route on_conversation event to appropriate Conversation."""
        self.get(conversation_message.conv_id).on_conversation.fire(
            conversation_message
        )

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

    def __init__(self, client, id_, users, last_modified, chat_name,
                 chat_messages):
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
        # Event fired when a user changes focus on a conversation with
        # arguments (focus_message).
        self.on_focus = event.Event('Conversation.on_focus')
        # Event fired when a conversation updates with arguments
        # (conversation_message).
        self.on_conversation = event.Event('Conversation.on_conversation')


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
        user = parsers.User(id_=user_id, full_name='UNKNOWN',
                            first_name='UNKNOWN',
                            is_self=(user_id == self._self_user_id))
        self._users[user_id] = user
        return user

    @gen.coroutine
    def _request_users(self, user_id_list):
        """Make request for a list of users by ID."""
        res = yield self._client.getentitybyid([user_id.chat_id for user_id
                                                in user_id_list])
        for entity in res['entity']:
            try:
                user = _parse_user_entity(entity)
            except ValueError as e:
                logger.warning('Failed to parse user entity: {}: {}'
                               .format(e, entity))
            else:
                user_id = parsers.UserID(chat_id=user['chat_id'],
                                         gaia_id=user['gaia_id'])
                self._users[user_id] = parsers.User(
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

        # Event fired when the client connects for the first time with
        # arguments ().
        self.on_connect = event.Event('Client.on_connect')
        # Event fired when the client reconnects after being disconnected with
        # arguments ().
        self.on_reconnect = event.Event('Client.on_reconnect')
        # Event fired when the client is disconnected with arguments ().
        self.on_disconnect = event.Event('Client.on_disconnect')
        # Event fired when a new message arrives with arguments (chat_message).
        self.on_message = event.Event('Client.on_message')
        # Event fired when a user starts or stops typing with arguments
        # (typing_message).
        self.on_typing = event.Event('Client.on_typing')
        # Event fired when a user changes focus on a conversation with
        # arguments (focus_message).
        self.on_focus = event.Event('Client.on_focus')
        # Event fired when a conversation updates with arguments
        # (conversation_message).
        self.on_conversation = event.Event('Client.on_conversation')

        self._cookies = cookies
        self._sync_timestamp = None  # datetime.datetime

        # These are instantiated after ConnectionEvent:
        self.initial_users = None # {UserID: User}
        self.self_user_id = None # UserID
        self.initial_conversations = None # {conv_id: Conversation}

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
        for conversation in conversation_state:
            events = conversation[2]
            for msg in events:
                try:
                    chat_message = parsers.parse_chat_message([msg])
                except exceptions.ParseError as e:
                    logger.warning('Failed to parse message: {}'.format(e))
                except exceptions.ParseNotImplementedError as e:
                    logger.info('Failed to parse message: {}'.format(e))
                else:
                    # Workaround for syncallnewevents timestamp being
                    # inclusive:
                    if chat_message.timestamp > self._sync_timestamp:
                        self.on_message.fire(chat_message)

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

        # build dict of conversations and their participants
        initial_conversations = {}
        self.initial_users = {} # {UserID: User}

        # add self to the contacts
        self_contact = data_dict['ds:20'][0][2]
        self.self_user_id = parsers.UserID(chat_id=self_contact[8][0],
                                           gaia_id=self_contact[8][1])
        self.initial_users[self.self_user_id] = parsers.User(
            id_=self.self_user_id, full_name=self_contact[9][1],
            first_name=self_contact[9][2], is_self=True
        )

        conversations = data_dict['ds:19'][0][3]
        for c in conversations:
            id_ = c[1][0][0]
            participants = c[1][13]
            last_modified = c[1][3][12]
            # With every converstion, we get a list of up to 20 of the most
            # recent messages, sorted oldest to newest.
            messages = []
            for raw_message in c[2]:
                try:
                    chat_message = parsers.parse_chat_message([raw_message])
                except exceptions.ParseError as e:
                    logger.warning('Failed to parse message: {}'.format(e))
                except exceptions.ParseNotImplementedError as e:
                    logger.info('Failed to parse message: {}'.format(e))
                else:
                    messages.append(chat_message)
            initial_conversations[id_] = {
                'participants': [],
                'last_modified': last_modified,
                'name': c[1][2],
                'messages': messages,
            }
            # Add the participants for this conversation.
            for p in participants:
                user_id = parsers.UserID(chat_id=p[0][0], gaia_id=p[0][1])
                initial_conversations[id_]['participants'].append(
                    user_id
                )
                # Add the participant to our list of contacts as a fallback, in
                # case they can't be found later by other methods.
                # TODO We should note who these users are and try to request
                # them.
                # p[1] can be a full name, None, or out of range.
                try:
                    display_name = p[1]
                except IndexError:
                    display_name = None
                if display_name is None:
                    display_name = 'Unknown'
                self.initial_users[user_id] = parsers.User(
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
            user_id = parsers.UserID(chat_id=c[0][8][0], gaia_id=c[0][8][1])
            self.initial_users[user_id] = parsers.User(
                id_=user_id, full_name=c[0][9][1], first_name=c[0][9][2],
                is_self=(user_id == self.self_user_id)
            )

        # Create a dict of the known conversations.
        self.initial_conversations = {conv_id: Conversation(
            self, conv_id, [self.initial_users[user_id] for user_id
                            in conv_info['participants']],
            conv_info['last_modified'], conv_info['name'],
            conv_info['messages'],
        ) for conv_id, conv_info in initial_conversations.items()}

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

    def _on_push_data(self, msg_type, msg):
        """Parse channel messages and call the appropriate event."""
        parsed_msg = parsers.parse_message(msg_type, msg)
        # Update the sync timestamp:
        if isinstance(parsed_msg, parsers.ChatMessage):
            self._sync_timestamp = parsed_msg.timestamp
        # Fire the appropriate event:
        handler = {
            parsers.ChatMessage: self.on_message,
            parsers.FocusStatusMessage: self.on_focus,
            parsers.TypingStatusMessage: self.on_typing,
            parsers.ConversationStatusMessage: self.on_conversation,
        }.get(parsed_msg.__class__, None)
        if handler is not None:
            handler.fire(parsed_msg)

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
