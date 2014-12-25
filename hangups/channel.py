"""Support for reading messages from the long-polling channel.

Hangouts receives events using a system that appears very close to an App
Engine Channel.
"""

import aiohttp
import asyncio
import hashlib
import logging
import re
import time

from hangups import javascript, http_utils, event, exceptions

logger = logging.getLogger(__name__)
LEN_REGEX = re.compile(r'([0-9]+)\n', re.MULTILINE)
ORIGIN_URL = 'https://talkgadget.google.com'
CHANNEL_URL_PREFIX = 'https://0.client-channel.google.com/client-channel/{}'
CONNECT_TIMEOUT = 30
# Long-polling requests send heartbeats every 15 seconds, so if we miss two in
# a row, consider the connection dead.
PUSH_TIMEOUT = 30
MAX_READ_BYTES = 1024 * 1024


class UnknownSIDError(exceptions.HangupsError):

    """hangups channel session expired."""

    pass


def get_authorization_headers(sapisid_cookie):
    """Return authorization headers for API request."""
    # It doesn't seem to matter what the url and time are as long as they are
    # consistent.
    time_msec = int(time.time() * 1000)
    auth_string = '{} {} {}'.format(time_msec, sapisid_cookie, ORIGIN_URL)
    auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()
    sapisidhash = 'SAPISIDHASH {}_{}'.format(time_msec, auth_hash)
    return {
        'authorization': sapisidhash,
        'x-origin': ORIGIN_URL,
        'x-goog-authuser': '0',
    }


def _best_effort_decode(data_bytes):
    """Decode data_bytes into a string using UTF-8.

    If data_bytes cannot be decoded, pop the last byte until it can be or
    return an empty string.
    """
    for end in reversed(range(1, len(data_bytes) + 1)):
        try:
            return data_bytes[0:end].decode()
        except UnicodeDecodeError:
            pass
    return ''


class PushDataParser(object):
    """Parse data from the long-polling endpoint."""

    def __init__(self):
        # Buffer for bytes containing utf-8 text:
        self._buf = b''

    def get_submissions(self, new_data_bytes):
        """Yield submissions generated from received data.

        Responses from the push endpoint consist of a sequence of submissions.
        Each submission is prefixed with its length followed by a newline.

        The buffer may not be decodable as UTF-8 if there's a split multi-byte
        character at the end. To handle this, do a "best effort" decode of the
        buffer to decode as much of it as possible.

        The length is actually the length of the string as reported by
        JavaScript. JavaScript's string length function returns the number of
        code units in the string, represented in UTF-16. We can emulate this by
        encoding everything in UTF-16 and multipling the reported length by 2.

        Note that when encoding a string in UTF-16, Python will prepend a
        byte-order character, so we need to remove the first two bytes.
        """
        self._buf += new_data_bytes

        while True:

            buf_decoded = _best_effort_decode(self._buf)
            buf_utf16 = buf_decoded.encode('utf-16')[2:]

            lengths = LEN_REGEX.findall(buf_decoded)
            if len(lengths) == 0:
                break
            else:
                # Both lengths are in number of bytes in UTF-16 encoding.
                # The length of the submission:
                length = int(lengths[0]) * 2
                # The length of the submission length and newline:
                length_length = len((lengths[0] + '\n').encode('utf-16')[2:])
                if len(buf_utf16) - length_length < length:
                    break

                submission = buf_utf16[length_length:length_length + length]
                yield submission.decode('utf-16')
                # Drop the length and the submission itself from the beginning
                # of the buffer.
                drop_length = (len((lengths[0] + '\n').encode()) +
                               len(submission.decode('utf-16').encode()))
                self._buf = self._buf[drop_length:]


def _parse_sid_response(res):
    """Parse response format for request for new channel SID.

    Example format (after parsing JS):
    [   [0,["c","SID_HERE","",8]],
        [1,[{"gsid":"GSESSIONID_HERE"}]]]

    Returns (SID, gsessionid) tuple.
    """
    res = javascript.loads(list(PushDataParser().get_submissions(res))[0])
    sid = res[0][1][1]
    gsessionid = res[1][1][0]['gsid']
    return (sid, gsessionid)


class Channel(object):

    """A channel connection that can listen for messages."""

    ##########################################################################
    # Public methods
    ##########################################################################

    def __init__(self, cookies, connector):
        """Create a new channel."""

        # Event fired when channel connects with arguments ():
        self.on_connect = event.Event('Channel.on_connect')
        # Event fired when channel reconnects with arguments ():
        self.on_reconnect = event.Event('Channel.on_reconnect')
        # Event fired when channel disconnects with arguments ():
        self.on_disconnect = event.Event('Channel.on_disconnect')
        # Event fired when a channel submission is received with arguments
        # (submission):
        self.on_message = event.Event('Channel.on_message')

        # True if the channel is currently connected:
        self._is_connected = False
        # True if the channel has been subscribed:
        self._is_subscribed = False
        # True if the on_connect event has been called at least once:
        self._on_connect_called = False
        # Request cookies dictionary:
        self._cookies = cookies
        # Parser for assembling messages:
        self._push_parser = None
        # aiohttp connector for keep-alive:
        self._connector = connector

        # Discovered parameters:
        self._sid_param = None
        self._gsessionid_param = None

    @property
    def is_connected(self):
        """Whether the client is currently connected."""
        return self._is_connected

    @asyncio.coroutine
    def listen(self):
        """Listen for messages on the channel.

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
                yield from asyncio.sleep(backoff_seconds)

            # Request a new SID if we don't have one yet, or the previous one
            # became invalid.
            if need_new_sid:
                # TODO: error handling
                yield from self._fetch_channel_sid()
                need_new_sid = False
            # Clear any previous push data, since if there was an error it
            # could contain garbage.
            self._push_parser = PushDataParser()
            try:
                yield from self._longpoll_request()
            except (UnknownSIDError, exceptions.NetworkError) as e:
                logger.warning('Long-polling request failed: {}'.format(e))
                retries -= 1
                if self._is_connected:
                    self._is_connected = False
                    yield from self.on_disconnect.fire()
                if isinstance(e, UnknownSIDError):
                    need_new_sid = True
            else:
                # The connection closed successfully, so reset the number of
                # retries.
                retries = MAX_RETRIES

            # If the request ended with an error, the client must account for
            # messages being dropped during this time.

        logger.error('Ran out of retries for long-polling request')

    ##########################################################################
    # Private methods
    ##########################################################################

    @asyncio.coroutine
    def _fetch_channel_sid(self):
        """Creates a new channel for receiving push data.

        Raises hangups.NetworkError if the channel can not be created.
        """
        logger.info('Requesting new gsessionid and SID...')
        # There's a separate API to get the gsessionid alone that Hangouts for
        # Chrome uses, but if we don't send a gsessionid with this request, it
        # will return a gsessionid as well as the SID.
        res = yield from http_utils.fetch(
            'post', CHANNEL_URL_PREFIX.format('channel/bind'),
            cookies=self._cookies, data='count=0', connector=self._connector,
            headers=get_authorization_headers(self._cookies['SAPISID']),
            params={
                'VER': 8,
                'RID': 81187,
                'ctype': 'hangouts',  # client type
            }
        )
        self._sid_param, self._gsessionid_param = _parse_sid_response(res.body)
        self._is_subscribed = False
        logger.info('New SID: {}'.format(self._sid_param))
        logger.info('New gsessionid: {}'.format(self._gsessionid_param))

    @asyncio.coroutine
    def _subscribe(self):
        """Subscribes the channel to receive relevant events.

        Only needs to be called when a new channel (SID/gsessionid) is opened.
        """

        logger.info('Subscribing channel...')
        timestamp = str(int(time.time() * 1000))
        # Hangouts for Chrome splits this over 2 requests, but it's possible to
        # do everything in one.
        yield from http_utils.fetch(
            'post', CHANNEL_URL_PREFIX.format('channel/bind'),
            cookies=self._cookies, connector=self._connector,
            headers=get_authorization_headers(self._cookies['SAPISID']),
            params={
                'VER': 8,
                'RID': 81188,
                'ctype': 'hangouts',  # client type
                'gsessionid': self._gsessionid_param,
                'SID': self._sid_param,
            },
            data={
                'count': 3,
                'ofs': 0,
                'req0_p': ('{"1":{"1":{"1":{"1":3,"2":2}},"2":{"1":{"1":3,"2":'
                           '2},"2":"","3":"JS","4":"lcsclient"},"3":' +
                           timestamp + ',"4":0,"5":"c1"},"2":{}}'),
                'req1_p': ('{"1":{"1":{"1":{"1":3,"2":2}},"2":{"1":{"1":3,"2":'
                           '2},"2":"","3":"JS","4":"lcsclient"},"3":' +
                           timestamp + ',"4":' + timestamp +
                           ',"5":"c3"},"3":{"1":{"1":"babel"}}}'),
                'req2_p': ('{"1":{"1":{"1":{"1":3,"2":2}},"2":{"1":{"1":3,"2":'
                           '2},"2":"","3":"JS","4":"lcsclient"},"3":' +
                           timestamp + ',"4":' + timestamp +
                           ',"5":"c4"},"3":{"1":{"1":"hangout_invite"}}}'),
            },
        )
        logger.info('Channel is now subscribed')
        self._is_subscribed = True

    @asyncio.coroutine
    def _longpoll_request(self):
        """Open a long-polling request and receive push data.

        This method uses keep-alive to make re-opening the request faster, but
        the remote server will set the "Connection: close" header once an hour.

        Raises hangups.NetworkError or UnknownSIDError.
        """
        params = {
            'VER': 8,
            'gsessionid': self._gsessionid_param,
            'RID': 'rpc',
            't': 1, # trial
            'SID': self._sid_param,
            'CI': 0,
            'ctype': 'hangouts',  # client type
            'TYPE': 'xmlhttp',
        }
        headers = get_authorization_headers(self._cookies['SAPISID'])
        logger.info('Opening new long-polling request')
        try:
            res = yield from asyncio.wait_for(aiohttp.request(
                'get', CHANNEL_URL_PREFIX.format('channel/bind'),
                params=params, cookies=self._cookies, headers=headers,
                connector=self._connector
            ), CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            raise exceptions.NetworkError('Request timed out')
        except aiohttp.errors.ConnectionError as e:
            raise exceptions.NetworkError('Request connection error: {}'
                                          .format(e))
        if res.status == 400 and res.reason == 'Unknown SID':
            raise UnknownSIDError('SID became invalid')
        elif res.status != 200:
            raise exceptions.NetworkError(
                'Request return unexpected status: {}: {}'
                .format(res.status, res.reason)
            )
        while True:
            try:
                chunk = yield from asyncio.wait_for(
                    res.content.read(MAX_READ_BYTES), PUSH_TIMEOUT
                )
            except asyncio.TimeoutError:
                raise exceptions.NetworkError('Request timed out')
            except aiohttp.errors.ConnectionError as e:
                raise exceptions.NetworkError('Request connection error: {}'
                                              .format(e))
            if chunk:
                yield from self._on_push_data(chunk)
            else:
                # Close the response to allow the connection to be reused for
                # the next request.
                res.close()
                break

    @asyncio.coroutine
    def _on_push_data(self, data_bytes):
        """Parse push data and trigger event methods."""
        logger.debug('Received push data:\n{}'.format(data_bytes))

        # Delay subscribing until first byte is received prevent "channel not
        # ready" errors that appear to be caused by a race condition on the
        # server.
        if not self._is_subscribed:
            yield from self._subscribe()

        # This method is only called when the long-polling request was
        # successful, so use it to trigger connection events if necessary.
        if not self._is_connected:
            if self._on_connect_called:
                self._is_connected = True
                yield from self.on_reconnect.fire()
            else:
                self._on_connect_called = True
                self._is_connected = True
                yield from self.on_connect.fire()

        for submission in self._push_parser.get_submissions(data_bytes):
            yield from self.on_message.fire(submission)
