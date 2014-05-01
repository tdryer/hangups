import random
import json
import requests
import time
import hashlib


class HangupsClient(object):

    def __init__(self, cookies, origin_url, key, request_header):
        self._cookies = cookies
        self._origin_url = origin_url
        self._key = key
        self._request_header = request_header

    def _get_authorization_header(self):
        # technically, it doesn't matter what the url and time are
        time_msec = int(time.time() * 1000)
        auth_string = '{} {} {}'.format(time_msec, self._get_cookie("SAPISID"),
                                        self._origin_url)
        auth_hash = hashlib.sha1(auth_string).hexdigest()
        return 'SAPISIDHASH {}_{}'.format(time_msec, auth_hash)

    def _get_cookie(self, name):
        try:
            return self._cookies[name]
        except KeyError:
            raise KeyError("Cookie '{}' is required".format(name))

    def _get_request_header(self):
        return self._request_header

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
            'key': self._key,
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


def load_key_txt():
    """Return key parameter loaded from key.txt file."""
    return open('key.txt').read().strip('\n')


def load_request_header_json():
    """Return request header json loaded from request_header.json."""
    return json.load(open('request_header.json'))


def main():
    """Make a chat request."""
    cookies = load_cookies_txt()
    hangups = HangupsClient(cookies, 'https://talkgadget.google.com',
                            load_key_txt(), load_request_header_json())

    # Get all events in the past hour
    now = time.time() * 1000000
    one_hour = 60 * 60 * 1000000
    print json.dumps(hangups.syncallnewevents(now - one_hour), indent=4)


if __name__ == '__main__':
    main()
