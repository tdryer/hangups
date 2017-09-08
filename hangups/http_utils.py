"""Utility function for making HTTP requests."""

import aiohttp
import asyncio
import collections
import logging
import urllib.parse

from hangups import exceptions, channel

logger = logging.getLogger(__name__)
CONNECT_TIMEOUT = 30
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

FetchResponse = collections.namedtuple('FetchResponse', ['code', 'body'])


class Session(object):
    """Session container to file http requests

    Args:
        cookies: dict, initial cookies for authentication
        proxy: string, proxy url used for the request
    """
    def __init__(self, cookies=None, proxy=None):
        self._proxy = proxy
        self._session = aiohttp.ClientSession(cookies=cookies)

    @property
    def cookies(self):
        """get all cookies of the session

        Returns:
            dict, cookie name as key and cookie value as data
        """
        return {cookie.key: cookie.value
                for cookie in self._session.cookie_jar}

    def close(self):
        """forward the call to the aiohttp.ClientSession"""
        self._session.close()

    def _get_cookie(self, name):
        """get a cookie or raise an error for a missing one

        Args:
            name: string, the requested cookie name

        Returns:
            string, requested cookie value

        Raises:
            KeyError: the requested cookie was not set by the server
        """
        for cookie in self._session.cookie_jar:
            if cookie.key == name:
                return cookie.value
        raise KeyError("Cookie '{}' is required".format(name))

    def _update_request(self, url, kwargs):
        """add authorization header for google and set the proxy

        Args:
            url: string, target URI
            kwargs: dict, may contain the key `headers`

        Returns:
            dict, updated kwargs with auth in the header and configured proxy

        Raises:
            ValueError: the given url is not valid
        """
        hostname = urllib.parse.urlparse(url).hostname
        if hostname is None:
            raise ValueError('The given URI "%s" is not valid' % url)

        if hostname.endswith('google.com'):
            kwargs['headers'] = kwargs.get('headers') or {}
            kwargs['headers'].update(
                channel.get_authorization_headers(self._get_cookie('SAPISID')))
        kwargs.setdefault('proxy', self._proxy)
        return kwargs

    @asyncio.coroutine
    def request(self, method, url, **kwargs):
        """perform a http request with authorization header for google

        Args:
            method: string, HTTP request method
            url: string, target URI
            kwargs: dict, see ``aiohttp.ClientSession.request``

        Returns:
            aiohttp.ClientResponse instance

        Raises:
            see ``aiohttp.ClientSession.request``
        """
        kwargs = self._update_request(url, kwargs)
        return (yield from self._session.request(method, url, **kwargs))

    @asyncio.coroutine
    def get(self, url, **kwargs):
        """perform a http GET request with authorization header for google

        Args:
            url: string, target URI
            kwargs: dict, see ``aiohttp.ClientSession.get``

        Returns:
            aiohttp.ClientResponse instance

        Raises:
            see ``aiohttp.ClientSession.request``
        """
        # pylint:disable=arguments-differ
        kwargs = self._update_request(url, kwargs)
        return (yield from self._session.get(url, **kwargs))

    @asyncio.coroutine
    def fetch(self, method, url, params=None, headers=None, data=None):
        """Make an HTTP request.

        If a request times out or one encounters a connection issue, it will be
        retried MAX_RETRIES times before finally raising hangups.NetworkError.

        Args:
            method: string, HTTP request method
            url: string, target URI
            params: dict, URI parameters
            headers: dict, request header
            data: dict, request post data

        Returns:
            a FetchResponse instance.

        Raises:
            hangups.NetworkError: request invalid or timed out
        """
        logger.debug('Sending request %s %s:\n%r', method, url, data)
        for retry_num in range(MAX_RETRIES):
            try:
                res = yield from asyncio.wait_for(
                    self.request(
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
