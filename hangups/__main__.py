"""Hangups - open client for the undocumented Hangouts chat API."""

import re
import random
import json
import time
import hashlib
import datetime
import logging
import http.cookies
from tornado import ioloop, gen, httpclient, httputil
from collections import namedtuple

from hangups import javascript, longpoll


logger = logging.getLogger(__name__)


Conversation = namedtuple('Conversation', ['id_', 'user_list', 'message_list'])
Message = namedtuple('Message', ['text', 'timestamp', 'user_gaia_id',
                                 'user_chat_id'])
User = namedtuple('User', ['chat_id', 'gaia_id', 'name'])


@gen.coroutine
def _fetch(url, method='GET', params=None, headers=None, cookies=None,
           data=None, streaming_callback=None, header_callback=None):
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
        streaming_callback=streaming_callback, header_callback=None,
        request_timeout=60*60
    ))
    return res


class HangupsClient(object):

    def __init__(self, cookies, origin_url):
        self._cookies = cookies
        self._origin_url = origin_url

        self._push_parser = None

        # (chat_id, gaia_id) -> User instance
        self._users = {}
        # conversation_id -> Conversation instance
        self._conversations = {}


        # discovered automatically:

        # the api key sent with every request
        self.api_key = None
        # fields sent in request headers
        self.header_date = None
        self.header_version = None
        self.header_id = None
        self.header_client = None
        # parameters related talkgadget channel requests
        self.channel_path = None
        self.gsessionid = None
        self.clid = None
        self.channel_ec_param = None
        self.channel_prop_param = None
        self.channel_session_id = None

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        """Abstract method called when a new message is received."""
        pass

    @gen.coroutine
    def on_connect(self):
        """Abstract method called when push connection is established."""
        pass

    @gen.coroutine
    def on_disconnect(self):
        """Abstract method called when push connection is disconnected."""
        pass

    @gen.coroutine
    def connect(self):
        """Initialize to gather connection parameters."""
        yield self._init_talkgadget_1()
        yield self._init_talkgadget_2()

    @gen.coroutine
    def run_forever(self):
        """Block forever to receive chat events."""
        url = 'https://talkgadget.google.com/u/0/talkgadget/_/channel/bind'
        params = {
            'VER': 8,
            'clid': self.clid,
            'prop': self.channel_prop_param,
            'ec': self.channel_ec_param,
            'gsessionid': self.gsessionid,
            'RID': 'rpc',
            't': 1, # trial
            'SID': self.channel_session_id,
            'CI': 0,
        }
        # Initialize the parser
        self._push_parser = longpoll.parse_push_data()
        self._push_parser.send(None)
        def streaming_callback(data):
            """Make the callback run a coroutine with exception handling."""
            future = self._on_push_data(data)
            ioloop.IOLoop.instance().add_future(future, lambda f: f.result())
        fetch_future = _fetch(url, params=params, cookies=self._cookies,
                              streaming_callback=streaming_callback,
                              header_callback=gen.Callback('header'))
        # TODO: At this join we are "connected", but we don't know if the
        # request was successful.
        yield self.on_connect()

        # Wait for response to finish.
        yield fetch_future

        # TODO: Re-establish the connection instead of disconnecting.
        yield self.on_disconnect()

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
            except ValueError:
                # not everything will be parsable, but we don't care
                logger.debug('Failed to parse JavaScript:\n{}'.format(data))

        # TODO: handle errors here
        self.api_key = data_dict['ds:7'][0][2]
        self.header_date = data_dict['ds:2'][0][4]
        self.header_version = data_dict['ds:2'][0][6]
        self.header_id = data_dict['ds:4'][0][7]
        self.channel_path = data_dict['ds:4'][0][1]
        self.gsessionid = data_dict['ds:4'][0][3]
        self.clid = data_dict['ds:4'][0][7]
        self.channel_ec_param = data_dict['ds:4'][0][4]
        self.channel_prop_param = data_dict['ds:4'][0][5]

    @gen.coroutine
    def _init_talkgadget_2(self):
        """Make second talkgadget request and parse response."""
        url = 'https://talkgadget.google.com{}bind'.format(self.channel_path)
        params = {
            'VER': 8,
            'clid': self.clid,
            'prop': self.channel_prop_param,
            'ec': self.channel_ec_param,
            'gsessionid': self.gsessionid,
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
        p = longpoll.parse_push_data()
        p.send(None)
        res = javascript.loads(p.send(res.body.decode()))
        # TODO: handle errors here
        val = res[3][1][1][1][1] # ex. foo@bar.com/AChromeExtensionBEEFBEEF
        self.header_client = val.split('/')[1] # ex. AChromeExtensionwBEEFBEEF
        self.channel_session_id = res[0][1][1]

    @gen.coroutine
    def _on_push_data(self, data_bytes):
        """Parse push data and call self._on_submsg for each submessage."""
        event = self._push_parser.send(data_bytes.decode())
        events = [event] if event is not None else []
        while True:
            event = next(self._push_parser)
            if event is None:
                break
            events.append(event)

        message = None
        conversation_id = None

        # Process all new data before making any callbacks, so we won't make
        # any redundant requests for data.
        for event in events:
            msg = longpoll.parse_message(javascript.loads(event))
            if 'payload_type' in msg and msg['payload_type'] == 'list':
                for submsg in longpoll.parse_list_payload(msg['payload']):
                    message = Message(text=submsg['text'],
                                      user_chat_id=submsg['sender_ids'][0],
                                      user_gaia_id=submsg['sender_ids'][1],
                                      timestamp=submsg['timestamp'])
                    conversation_id = submsg['conversation_id']
                    logger.info('Received message: {}'.format(message))

        # Make callbacks for new data.
        if message is not None:
            yield self.on_message_received(conversation_id, message)

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
            [3, 3, self.header_version, self.header_date],
            [self.header_client, self.header_id],
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
            'key': self.api_key,
            'alt': 'json', # json or protojson
        }
        res = yield _fetch(url, method='POST', headers=headers,
                           cookies=cookies, params=params,
                           data=json.dumps(body_json))
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
    def syncallnewevents(self, after_timestamp):
        """List all events occuring at or after timestamp."""
        res = yield self._request('conversations/syncallnewevents', [
            self._get_request_header(),
            after_timestamp,
            [], None, [], False, [],
            1048576
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


def load_cookies_txt():
    """Return cookies dictionary loaded from cookies.txt file.

    Expected format is the same as the body of an HTTP cookie header.
    """
    cookies_str = open('cookies.txt').read()
    cookies_list = [s.split('=', 1) for s in
                    cookies_str.strip('\n').split('; ')]
    return {cookie[0]: cookie[1] for cookie in cookies_list}


class DemoClient(HangupsClient):
    """Demo client for hangups."""

    @gen.coroutine
    def on_connect(self):
        print('Connection established')
        # Get all events in the past hour
        print('Requesting all events from the past hour')
        now = time.time() * 1000000
        one_hour = 60 * 60 * 1000000
        # TODO: add a proper API for this
        # XXX: doesn't work if there haven't been any events
        events = yield self.syncallnewevents(now - one_hour)

        conversations = {}
        for conversation in events['conversation_state']:
            id_ = conversation['conversation']['id']['id']
            participants = {
                (p['id']['chat_id'], p['id']['gaia_id']): p['fallback_name']
                for p in conversation['conversation']['participant_data']
            }
            conversations[id_] = {
                'participants': participants,
            }

        conversations_list = list(enumerate(conversations.items()))
        print('Activity has recently occurred in the conversations:')
        for n, (_, conversation) in conversations_list:
            print(' [{}] {}'.format(
                n, ', '.join(sorted(conversation['participants'].values()))
            ))
        # TODO: do this without blocking the IO loop
        conversation_index = int(input('Select a conversation to listen to: '))
        conversation_id = conversations_list[conversation_index][1][0]
        conversation = conversations_list[conversation_index][1][1]
        print('Now listening to conversation\n')
        self.listen_id = conversation_id

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        if conversation_id == self.listen_id:
            print('({}) {}: {}'.format(
                datetime.datetime.fromtimestamp(
                    message.timestamp / 1000000
                ).strftime('%I:%M:%S %p'),
                message.user_chat_id, # TODO: resolve name
                message.text
            ))

    @gen.coroutine
    def on_disconnect(self):
        print('Connection lost')


@gen.coroutine
def main_coroutine():
    """Make a chat request."""
    logger.info('Initializing HangupsClient')
    cookies = load_cookies_txt()
    client = DemoClient(cookies, 'https://talkgadget.google.com')
    yield client.connect()
    yield client.run_forever()


def main():
    """Start the IO loop."""
    logging.basicConfig(filename='hangups.log', level=logging.DEBUG)
    ioloop.IOLoop.instance().run_sync(main_coroutine)


if __name__ == '__main__':
    main()
