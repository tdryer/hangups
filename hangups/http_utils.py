"""HTTP request session."""

import aiohttp
import asyncio
import collections
import hashlib
import logging
import time
import urllib.parse

from hangups import exceptions

logger = logging.getLogger(__name__)
CONNECT_TIMEOUT = 30
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
ORIGIN_URL = 'https://talkgadget.google.com'

FetchResponse = collections.namedtuple('FetchResponse', ['code', 'body'])


class Session(object):
    """Session for making HTTP requests to Google.

    Args:
        cookies (dict): Cookies to authenticate requests with.
        proxy (str): (optional) HTTP proxy URL to use for requests.
    """

    def __init__(self, cookies, proxy=None):
        self._proxy = proxy
        self._session = aiohttp.ClientSession(cookies=cookies)
        sapisid = cookies['SAPISID']
        self._authorization_headers = _get_authorization_headers(sapisid)

    @asyncio.coroutine
    def fetch(self, method, url, params=None, headers=None, data=None):
        """Make an HTTP request.

        Automatically uses configured HTTP proxy, and adds Google authorization
        header and cookies.

        Failures will be retried MAX_RETRIES times before raising NetworkError.

        Args:
            method (str): Request method.
            url (str): Request URL.
            params (dict): (optional) Request query string parameters.
            headers (dict): (optional) Request headers.
            data: (str): (optional) Request body data.

        Returns:
            FetchResponse: Response data.

        Raises:
            NetworkError: If the request fails.
        """
        logger.debug('Sending request %s %s:\n%r', method, url, data)
        for retry_num in range(MAX_RETRIES):
            try:
                res = yield from asyncio.wait_for(
                    self.fetch_raw(
                        method, url, params=params, headers=headers, data=data,
                    ),
                    CONNECT_TIMEOUT)
                try:
                    body = yield from asyncio.wait_for(
                        res.read(), REQUEST_TIMEOUT)
                finally:
                    res.release()
                logger.debug('Received response %d %s:\n%r',
                             res.status, res.reason, body)
            except asyncio.TimeoutError:
                error_msg = 'Request timed out'
            except aiohttp.ServerDisconnectedError as err:
                error_msg = 'Server disconnected error: {}'.format(err)
            except (aiohttp.ClientError, ValueError) as err:
                error_msg = 'Request connection error: {}'.format(err)
            else:
                break
            logger.info('Request attempt %d failed: %s', retry_num, error_msg)
        else:
            logger.info('Request failed after %d attempts', MAX_RETRIES)
            raise exceptions.NetworkError(error_msg)

        if res.status != 200:
            logger.info('Request returned unexpected status: %d %s',
                        res.status, res.reason)
            raise exceptions.NetworkError(
                'Request return unexpected status: {}: {}'
                .format(res.status, res.reason)
            )

        return FetchResponse(res.status, body)

    @asyncio.coroutine
    def fetch_raw(self, method, url, params=None, headers=None, data=None):
        """Make an HTTP request using aiohttp directly.

        Automatically uses configured HTTP proxy, and adds Google authorization
        header and cookies.

        Args:
            method (str): Request method.
            url (str): Request URL.
            params (dict): (optional) Request query string parameters.
            headers (dict): (optional) Request headers.
            data: (str): (optional) Request body data.

        Returns:
            aiohttp.ClientResponse: HTTP response.

        Raises:
            See ``aiohttp.ClientSession.request``.
        """
        # Ensure we don't accidentally send the authorization header to a
        # non-Google domain:
        assert urllib.parse.urlparse(url).hostname.endswith('.google.com')
        headers = headers or {}
        headers.update(self._authorization_headers)
        return (yield from self._session.request(
            method, url, params=params, headers=headers, data=data,
            proxy=self._proxy
        ))

    def close(self):
        """Close the underlying aiohttp.ClientSession."""
        self._session.close()


def _get_authorization_headers(sapisid_cookie):
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
