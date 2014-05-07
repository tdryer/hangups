"""Hangups - open client for the undocumented Hangouts chat API."""

import re
import random
import json
import requests
import time
import hashlib
import datetime

from hangups import javascript, longpoll


class HangupsClient(object):

    def __init__(self, cookies, origin_url):
        self._cookies = cookies
        self._origin_url = origin_url

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

        # make initialization requests
        self._init_talkgadget_1()
        self._init_talkgadget_2()

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
        res = requests.get(url, cookies=self._cookies, params=params,
                           headers=headers)
        if res.status_code != 200:
            raise ValueError("First talkgadget request failed")
        res = res.text

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
                pass # not everything will be parsable, but we don't care

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
        res = requests.post(url, cookies=self._cookies, params=params,
                            data='count=0', stream=True)
        if res.status_code != 200:
            raise ValueError("Second talkgadget request failed with {}: {}"
                             .format(res.status_code, res.raw.read()))
        res = list(longpoll.load(res.raw))[0]
        val = res[3][1][1][1][1] # ex. foo@bar.com/AChromeExtensionBEEFBEEF
        self.header_client = val.split('/')[1] # ex. AChromeExtensionwBEEFBEEF
        self.channel_session_id = res[0][1][1]

    def _receive_push_events(self):
        """Open channel to receive push events."""
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
        res = requests.get(url, params=params, cookies=self._cookies,
                           stream=True)
        if res.status_code != 200:
            raise ValueError('Push channel request returned {}: {}'
                             .format(res.status_code, res.raw.read()))
        for message in longpoll.load(res.raw):
            yield message

    def _get_authorization_header(self):
        # technically, it doesn't matter what the url and time are
        time_msec = int(time.time() * 1000)
        auth_string = '{} {} {}'.format(time_msec, self._get_cookie("SAPISID"),
                                        self._origin_url)
        auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()
        return 'SAPISIDHASH {}_{}'.format(time_msec, auth_hash)

    def _get_cookie(self, name):
        try:
            return self._cookies[name]
        except KeyError:
            raise KeyError("Cookie '{}' is required".format(name))

    def _get_request_header(self):
        return [
            [3, 3, self.header_version, self.header_date],
            [self.header_client, self.header_id],
            None,
            "en"
        ]

    def _request(self, endpoint, body_json):
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
        return requests.post(url, headers=headers, cookies=cookies,
                             params=params, data=json.dumps(body_json))

    def getselfinfo(self):
        """Return information about your account."""
        res = self._request('contacts/getselfinfo', [
            self._get_request_header(),
            [], []
        ])
        return json.loads(res.text)

    def setfocus(self, conversation_id):
        """Set focus (occurs whenever you give focus to a client)."""
        res = self._request('conversations/setfocus', [
            self._get_request_header(),
            [conversation_id],
            1,
            20
        ])
        return json.loads(res.text)

    def searchentities(self, search_string, max_results):
        """Search for people."""
        res = self._request('contacts/searchentities', [
            self._get_request_header(),
            [],
            search_string,
            max_results
        ])
        return json.loads(res.text)

    def querypresence(self, chat_id):
        """Check someone's presence status."""
        res = self._request('presence/querypresence', [
            self._get_request_header(),
            [
                [chat_id]
            ],
            [1, 2, 5, 7, 8]
        ])
        return json.loads(res.text)

    def getentitybyid(self, chat_id_list):
        """Return information about a list of contacts."""
        res = self._request('contacts/getentitybyid', [
            self._get_request_header(),
            None,
            [[str(chat_id)] for chat_id in chat_id_list],
        ])
        return json.loads(res.text)

    def getconversation(self, conversation_id, num_events,
                        storage_continuation_token, event_timestamp):
        """Return data about a conversation.

        Seems to require both a timestamp and a token from a previous event
        """
        res = self._request('conversations/getconversation', [
            self._get_request_header(),
            [
                [conversation_id], [], []
            ],
            True, True, None, num_events,
            [None, storage_continuation_token, event_timestamp]
        ])
        return json.loads(res.text)

    def syncallnewevents(self, after_timestamp):
        """List all events occuring at or after timestamp."""
        res = self._request('conversations/syncallnewevents', [
            self._get_request_header(),
            after_timestamp,
            [], None, [], False, [],
            1048576
        ])
        return json.loads(res.text)

    def sendchatmessage(self, conversation_id, message, is_bold=False,
                        is_italic=False, is_strikethrough=False,
                        is_underlined=False):
        """Send a chat message to a conversation."""
        client_generated_id = random.randint(0, 2**32)
        res = self._request('conversations/sendchatmessage', [
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
        return json.loads(res.text)


def load_cookies_txt():
    """Return cookies dictionary loaded from cookies.txt file.

    Expected format is the same as the body of an HTTP cookie header.
    """
    cookies_str = open('cookies.txt').read()
    cookies_list = [s.split('=', 1) for s in
                    cookies_str.strip('\n').split('; ')]
    return {cookie[0]: cookie[1] for cookie in cookies_list}


def main():
    """Make a chat request."""
    cookies = load_cookies_txt()
    hangups = HangupsClient(cookies, 'https://talkgadget.google.com')

    # Get all events in the past hour
    now = time.time() * 1000000
    one_hour = 60 * 60 * 1000000
    events = hangups.syncallnewevents(now - one_hour)

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
        print(' [{}] {}'
              .format(n,
                      ', '.join(sorted(conversation['participants'].values()))))
    conversation_index = int(input('Select a conversation to listen to: '))
    conversation_id = conversations_list[conversation_index][1][0]
    conversation = conversations_list[conversation_index][1][1]
    print('Now listening to conversation\n')

    for msg in hangups._receive_push_events():
        msg = longpoll.parse_message(msg)
        if 'payload_type' in msg and msg['payload_type'] == 'list':
            for submsg in longpoll.parse_list_payload(msg['payload']):
                if submsg['conversation_id'] == conversation_id:
                    print('({}) {}: {}'.format(
                        datetime.datetime.fromtimestamp(
                            submsg['timestamp'] / 1000000
                        ).strftime('%I:%M:%S %p'),
                        conversation['participants'][submsg['sender_ids']],
                        submsg['text']
                    ))

    print('Connection closed')


if __name__ == '__main__':
    main()
