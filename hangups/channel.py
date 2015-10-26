"""Client for Google's BrowserChannel protocol.

BrowserChannel allows simulating a bidirectional socket in a web browser using
long-polling requests. It is used by the Hangouts web client to receive state
updates from the server. The "forward channel" sends "maps" (dictionaries) to
the server. The "backwards channel" receives "arrays" (lists) from the server.

Google provides a JavaScript BrowserChannel client as part of closure-library:
http://google.github.io/closure-library/api/class_goog_net_BrowserChannel.html

Source code is available here:
https://github.com/google/closure-library/blob/master/closure/goog/net/browserchannel.js

Unofficial protocol documentation is available here:
https://web.archive.org/web/20121226064550/http://code.google.com/p/libevent-browserchannel-server/wiki/BrowserChannelProtocol
"""

import aiohttp
import asyncio
import hashlib
import json
import logging
import re
import time

from hangups import http_utils, event, exceptions

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


class ChunkParser(object):
    """Parse data from the backward channel into chunks.

    Responses from the backward channel consist of a sequence of chunks which
    are streamed to the client. Each chunk is prefixed with its length,
    followed by a newline. The length allows the client to identify when the
    entire chunk has been received.
    """

    def __init__(self):
        # Buffer for bytes containing utf-8 text:
        self._buf = b''

    def get_chunks(self, new_data_bytes):
        """Yield chunks generated from received data.

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
    res = json.loads(list(ChunkParser().get_chunks(res))[0])
    sid = res[0][1][1]
    gsessionid = res[1][1][0]['gsid']
    return (sid, gsessionid)


class Channel(object):
    """BrowserChannel client."""

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
        # Event fired when an array is received with arguments (array):
        self.on_receive_array = event.Event('Channel.on_receive_array')

        # True if the channel is currently connected:
        self._is_connected = False
        # True if the on_connect event has been called at least once:
        self._on_connect_called = False
        # Request cookies dictionary:
        self._cookies = cookies
        # Parser for assembling messages:
        self._chunk_parser = None
        # aiohttp connector for keep-alive:
        self._connector = connector

        # Discovered parameters:
        self._sid_param = None
        self._gsessionid_param = None

    @property
    def is_connected(self):
        """Whether the channel is currently connected."""
        return self._is_connected

    @asyncio.coroutine
    def listen(self):
        """Listen for messages on the backwards channel.

        This method only returns when the connection has been closed due to an
        error.
        """
        MAX_RETRIES = 5  # maximum number of times to retry after a failure
        retries = MAX_RETRIES  # number of remaining retries
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
                yield from self._fetch_channel_sid()
                need_new_sid = False
            # Clear any previous push data, since if there was an error it
            # could contain garbage.
            self._chunk_parser = ChunkParser()
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

    @asyncio.coroutine
    def send_maps(self, map_list):
        """Sends a request to the server containing maps (dicts)."""
        params = {
            'VER': 8,  # channel protocol version
            'RID': 81188,  # request identifier
            'ctype': 'hangouts',  # client type
        }
        if self._gsessionid_param is not None:
            params['gsessionid'] = self._gsessionid_param
        if self._sid_param is not None:
            params['SID'] = self._sid_param
        data_dict = dict(count=len(map_list), ofs=0)
        for map_num, map_ in enumerate(map_list):
            for map_key, map_val in map_.items():
                data_dict['req{}_{}'.format(map_num, map_key)] = map_val
        res = yield from http_utils.fetch(
            'post', CHANNEL_URL_PREFIX.format('channel/bind'),
            cookies=self._cookies, connector=self._connector,
            headers=get_authorization_headers(self._cookies['SAPISID']),
            params=params, data=data_dict,
        )
        return res

    ##########################################################################
    # Private methods
    ##########################################################################

    @asyncio.coroutine
    def _fetch_channel_sid(self):
        """Creates a new channel for receiving push data.

        Sending an empty forward channel request will create a new channel on
        the server.

        There's a separate API to get the gsessionid alone that Hangouts for
        Chrome uses, but if we don't send a gsessionid with this request, it
        will return a gsessionid as well as the SID.

        Raises hangups.NetworkError if the channel can not be created.
        """
        logger.info('Requesting new gsessionid and SID...')
        # Set SID and gsessionid to None so they aren't sent in by send_maps.
        self._sid_param = None
        self._gsessionid_param = None
        res = yield from self.send_maps([])
        self._sid_param, self._gsessionid_param = _parse_sid_response(res.body)
        logger.info('New SID: {}'.format(self._sid_param))
        logger.info('New gsessionid: {}'.format(self._gsessionid_param))

    @asyncio.coroutine
    def _longpoll_request(self):
        """Open a long-polling request and receive arrays.

        This method uses keep-alive to make re-opening the request faster, but
        the remote server will set the "Connection: close" header once an hour.

        Raises hangups.NetworkError or UnknownSIDError.
        """
        params = {
            'VER': 8,  # channel protocol version
            'gsessionid': self._gsessionid_param,
            'RID': 'rpc',  # request identifier
            't': 1,  # trial
            'SID': self._sid_param,  # session ID
            'CI': 0,  # 0 if streaming/chunked requests should be used
            'ctype': 'hangouts',  # client type
            'TYPE': 'xmlhttp',  # type of request
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
        except aiohttp.ClientError as e:
            raise exceptions.NetworkError('Request connection error: {}'
                                          .format(e))
        except aiohttp.ServerDisconnectedError as e:
            raise exceptions.NetworkError('Server disconnected error: {}'
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
            except aiohttp.ClientError as e:
                raise exceptions.NetworkError('Request connection error: {}'
                                              .format(e))
            except aiohttp.ServerDisconnectedError as e:
                raise exceptions.NetworkError('Server disconnected error: {}'
                                              .format(e))
            except asyncio.CancelledError:
                # Prevent ResourceWarning when channel is disconnected.
                res.close()
                raise
            if chunk:
                yield from self._on_push_data(chunk)
            else:
                # Close the response to allow the connection to be reused for
                # the next request.
                res.close()
                break

    @asyncio.coroutine
    def _on_push_data(self, data_bytes):
        """Parse push data and trigger events."""
        logger.debug('Received chunk:\n{}'.format(data_bytes))
        for chunk in self._chunk_parser.get_chunks(data_bytes):

            # Consider the channel connected once the first chunk is received.
            if not self._is_connected:
                if self._on_connect_called:
                    self._is_connected = True
                    yield from self.on_reconnect.fire()
                else:
                    self._on_connect_called = True
                    self._is_connected = True
                    yield from self.on_connect.fire()

            # chunk contains a container array
            container_array = json.loads(chunk)
            # container array is an array of inner arrays
            for inner_array in container_array:
                # inner_array always contains 2 elements, the array_id and the
                # data_array.
                array_id, data_array = inner_array
                logger.debug('Chunk contains data array with id %r:\n%r',
                             array_id, data_array)
                yield from self.on_receive_array.fire(data_array)
