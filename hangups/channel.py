"""Support for reading messages from the long-polling channel.

Hangouts receives events using a system that appears very close to an App
Engine Channel.
"""

import aiohttp
import asyncio
import logging
import re

from hangups import javascript, http_utils, event, exceptions

logger = logging.getLogger(__name__)
LEN_REGEX = re.compile(r'([0-9]+)\n', re.MULTILINE)
CONNECT_TIMEOUT = 30
# Long-polling requests send heartbeats every 15 seconds, so if we miss two in
# a row, consider the connection dead.
PUSH_TIMEOUT = 30
MAX_READ_BYTES = 1024 * 1024


class UnknownSIDError(exceptions.HangupsError):

    """hangups channel session expired."""

    pass


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

    Returns (SID, email, header_client, gsessionid).
    """
    sid = None
    header_client = None
    gsessionid = None

    p = PushDataParser()
    res = javascript.loads(list(p.get_submissions(res))[0])
    for segment in res:
        num, message = segment
        if num == 0:
            sid = message[1]
        elif message[0] == 'c':
            type_ = message[1][1][0]
            if type_ == 'cfj':
                email, header_client = message[1][1][1].split('/')
            elif type_ == 'ei':
                gsessionid = message[1][1][1]

    return(sid, email, header_client, gsessionid)


class Channel(object):

    """A channel connection that can listen for messages."""

    ##########################################################################
    # Public methods
    ##########################################################################

    def __init__(self, cookies, path, clid, ec, prop, connector):
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
        # True if the on_connect event has been called at least once:
        self._on_connect_called = False
        # Request cookies dictionary:
        self._cookies = cookies
        # Parser for assembling messages:
        self._push_parser = None
        # aiohttp connector for keep-alive:
        self._connector = connector

        # Static channel parameters:
        # '/u/0/talkgadget/_/channel/'
        self._channel_path = path
        # 'A672C650270E1674'
        self._clid_param = clid
        # '["ci:ec",1,1,0,"chat_wcs_20140813.110045_RC2"]\n'
        self._ec_param = ec
        # 'aChromeExtension'
        self._prop_param = prop

        # Discovered parameters:
        self._sid_param = None
        self._gsessionid_param = None
        self._email = None
        self._header_client = None

    @property
    def header_client(self):
        return self._header_client

    @property
    def email(self):
        return self._email

    @property
    def is_connected(self):
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
        """Request a new session ID for the push channel.

        Raises hangups.NetworkError.
        """
        logger.info('Requesting new session...')
        url = 'https://talkgadget.google.com{}bind'.format(self._channel_path)
        params = {
            'VER': 8,
            'clid': self._clid_param,
            'ec': self._ec_param,
            'RID': 81187,
            # Required if we want our client to be called "AChromeExtension":
            'prop': self._prop_param,
        }
        try:
            res = yield from http_utils.fetch(
                'post', url, cookies=self._cookies, params=params,
                data='count=0', connector=self._connector
            )
        except exceptions.NetworkError as e:
            raise exceptions.HangupsError('Failed to request SID: {}'.format(e))
        # TODO: Re-write the function we're calling here to use a schema so we
        # can easily catch its failure.
        self._sid_param, self._email, self._header_client, self._gsessionid_param = (
            _parse_sid_response(res.body)
        )
        logger.info('New SID: {}'.format(self._sid_param))
        logger.info('New email: {}'.format(self._email))
        logger.info('New client: {}'.format(self._header_client))
        logger.info('New gsessionid: {}'.format(self._gsessionid_param))

    @asyncio.coroutine
    def _longpoll_request(self):
        """Open a long-polling request and receive push data.

        It's important to use keep-alive so a connection is maintained to the
        specific server that holds the session (likely because of load
        balancing). Without keep-alive, long polling requests will frequently
        fail with 400 "Unknown SID".

        Raises hangups.NetworkError or UnknownSIDError.
        """
        params = {
            'VER': 8,
            'clid': self._clid_param,
            'prop': self._prop_param,
            'ec': self._ec_param,
            'gsessionid': self._gsessionid_param,
            'RID': 'rpc',
            't': 1, # trial
            'SID': self._sid_param,
            'CI': 0,
        }
        URL = 'https://talkgadget.google.com/u/0/talkgadget/_/channel/bind'
        logger.info('Opening new long-polling request')
        try:
            res = yield from asyncio.wait_for(aiohttp.request(
                'get', URL, params=params, cookies=self._cookies,
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
