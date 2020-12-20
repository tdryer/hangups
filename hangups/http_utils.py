"""HTTP request session."""

import asyncio
import collections
import hashlib
import logging
import time
import urllib.parse

import aiohttp
import async_timeout

from hangups import exceptions

logger = logging.getLogger(__name__)
CONNECT_TIMEOUT = 30
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
ORIGIN_URL = 'https://hangouts.google.com'

FetchResponse = collections.namedtuple('FetchResponse', ['code', 'body'])


class Session:
    """Session for making HTTP requests to Google.

    Args:
        cookies (dict): Cookies to authenticate requests with.
        proxy (str): (optional) HTTP proxy URL to use for requests.
    """

    def __init__(self, cookies, proxy=None):
        self._proxy = proxy
        # The server does not support quoting cookie values (see #498).
        cookie_jar = aiohttp.CookieJar(quote_cookie=False)
        timeout = aiohttp.ClientTimeout(connect=CONNECT_TIMEOUT)
        self._session = aiohttp.ClientSession(
            cookies=cookies, cookie_jar=cookie_jar, timeout=timeout
        )
        sapisid = cookies['SAPISID']
        self._authorization_headers = _get_authorization_headers(sapisid)

    async def fetch(self, method, url, params=None, headers=None, data=None):
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
                async with self.fetch_raw(method, url, params=params,
                                          headers=headers, data=data) as res:
                    async with async_timeout.timeout(REQUEST_TIMEOUT):
                        body = await res.read()
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
            aiohttp._RequestContextManager: ContextManager for a HTTP response.

        Raises:
            See ``aiohttp.ClientSession.request``.
        """
        # Ensure we don't accidentally send the authorization header to a
        # non-Google domain:
        if not urllib.parse.urlparse(url).hostname.endswith('.google.com'):
            raise Exception('expected google.com domain')

        headers = headers or {}
        headers.update(self._authorization_headers)
        return self._session.request(
            method, url, params=params, headers=headers, data=data,
            proxy=self._proxy
        )

    async def close(self):
        """Close the underlying aiohttp.ClientSession."""
        await self._session.close()


def _get_authorization_headers(sapisid_cookie):
    """Return authorization headers for API request."""
    # It doesn't seem to matter what the url and time are as long as they are
    # consistent.
    time_sec = int(time.time())
    auth_string = '{} {} {}'.format(time_sec, sapisid_cookie, ORIGIN_URL)
    auth_hash = hashlib.sha1(auth_string.encode()).hexdigest()
    sapisidhash = 'SAPISIDHASH {}_{}'.format(time_sec, auth_hash)
    return {
        'authorization': sapisidhash,
        'origin': ORIGIN_URL,
        'x-goog-authuser': '0',
    }
