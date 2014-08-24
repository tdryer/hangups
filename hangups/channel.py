"""Support for reading messages from the long-polling channel.

Hangouts receives events using a system that appears very close to an App
Engine Channel.
"""

from tornado import gen, httpclient
import logging

from hangups import javascript, parsers, http_utils, event

logger = logging.getLogger(__name__)
# Set the connection and request timeouts low so we fail fast when there's a
# network problem.
CONNECT_TIMEOUT = 10
REQUEST_TIMEOUT = 10
# Long-polling requests may last ~3-4 minutes.
LP_REQ_TIMEOUT = 60 * 5
# Long-polling requests send heartbeats every 15 seconds, so if we miss two in
# a row, consider the connection dead.
LP_DATA_TIMEOUT = 30


def _parse_sid_response(res):
    """Parse response format for request for new channel SID.

    Returns (SID, header_client, gsessionid).
    """
    sid = None
    header_client = None
    gsessionid = None

    p = parsers.PushDataParser()
    res = javascript.loads(list(p.get_submissions(res))[0])
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


class Channel(object):

    """A channel connection that can listen for messages."""

    ##########################################################################
    # Public methods
    ##########################################################################

    def __init__(self, cookies, path, clid, ec, prop):
        """Create a new channel."""

        # Event fired when channel connects with arguments ():
        self.on_connect = event.Event('Channel.on_connect')
        # Event fired when channel reconnects with arguments ():
        self.on_reconnect = event.Event('Channel.on_reconnect')
        # Event fired when channel disconnects with arguments ():
        self.on_disconnect = event.Event('Channel.on_disconnect')
        # Event fired when a channel message is received with arguments
        # (message_type, message):
        self.on_message = event.Event('Channel.on_message')

        # True if the channel is currently connected:
        self._is_connected = False
        # True if the on_connect event has been called at least once:
        self._on_connect_called = False
        # Request cookies dictionary:
        self._cookies = cookies
        # Parser for assembling messages:
        self._push_parser = None

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

    @gen.coroutine
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
                yield http_utils.sleep(backoff_seconds)

            # Request a new SID if we don't have one yet, or the previous one
            # became invalid.
            if need_new_sid:
                # TODO: error handling
                yield self._fetch_channel_sid()
                need_new_sid = False
            # Clear any previous push data, since if there was an error it
            # could contain garbage.
            self._push_parser = parsers.PushDataParser()
            try:
                yield self._longpoll_request()
            except IOError as e:
                # An error occurred, so decrement the number of retries.
                retries -= 1
                if self._is_connected:
                    self._is_connected = False
                    self.on_disconnect.fire()
                logger.warning('Long-polling request failed because of '
                               'IOError: {}'.format(e))
            except httpclient.HTTPError as e:
                # An error occurred, so decrement the number of retries.
                retries -= 1
                if self._is_connected:
                    self._is_connected = False
                    self.on_disconnect.fire()
                if e.code == 400 and e.response.reason == 'Unknown SID':
                    logger.warning('Long-polling request failed because SID '
                                   'became invalid. Will attempt to recover.')
                    need_new_sid = True
                elif e.code == 599:
                    logger.warning('Long-polling request failed because '
                                   'connection was closed. Will attempt to '
                                   'recover.')
                else:
                    logger.warning('Long-polling request failed for unknown '
                                   'reason: {}'.format(e))
                    break # Do not retry.
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

    @gen.coroutine
    def _fetch_channel_sid(self):
        """Request a new session ID for the push channel."""
        logger.info('Requesting new session...')
        url = 'https://talkgadget.google.com{}bind'.format(self._channel_path)
        params = {
            'VER': 8,
            'clid': self._clid_param,
            'ec': self._ec_param,
            'RID': 81187, # TODO: "request ID"? should probably increment
            # Required if we want our client to be called "AChromeExtension":
            'prop': self._prop_param,
        }
        res = yield http_utils.fetch(
            url, method='POST', cookies=self._cookies, params=params,
            data='count=0', connect_timeout=CONNECT_TIMEOUT,
            request_timeout=REQUEST_TIMEOUT
        )
        logger.debug('Fetch SID response:\n{}'.format(res.body))
        if res.code != 200:
            # TODO use better exception
            raise ValueError("SID fetch request failed with {}: {}"
                             .format(res.code, res.raw.read()))
        # TODO: handle errors here
        self._sid_param, _, self._gsessionid_param = (
            _parse_sid_response(res.body)
        )
        logger.info('New SID: {}'.format(self._sid_param))
        logger.info('New gsessionid: {}'.format(self._gsessionid_param))

    @gen.coroutine
    def _longpoll_request(self):
        """Open a long-polling request to receive push events.

        Raises HTTPError or IOError.
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
        res = yield http_utils.longpoll_fetch(
            URL, params=params, cookies=self._cookies,
            streaming_callback=self._on_push_data,
            connect_timeout=CONNECT_TIMEOUT, request_timeout=LP_REQ_TIMEOUT,
            data_timeout=LP_DATA_TIMEOUT
        )
        return res

    def _on_push_data(self, data_bytes):
        """Parse push data and trigger event methods."""
        logger.debug('Received push data:\n{}'.format(data_bytes))

        # This method is only called when the long-polling request was
        # successful, so use it to trigger connection events if necessary.
        if not self._is_connected:
            if self._on_connect_called:
                self._is_connected = True
                self.on_reconnect.fire()
            else:
                self._on_connect_called = True
                self._is_connected = True
                self.on_connect.fire()

        messages = self._push_parser.get_messages(data_bytes)
        for msg_type, msg in messages:
            logger.debug('Received channel message of type {}: {}'
                         .format(msg_type, msg))
            self.on_message.fire(msg_type, msg)
