"""Utility function for making HTTP requests."""

import aiohttp
import asyncio
import collections
import logging

from hangups import exceptions

logger = logging.getLogger(__name__)
CONNECT_TIMEOUT = 30
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

FetchResponse = collections.namedtuple('FetchResponse', ['code', 'body'])


@asyncio.coroutine
def fetch(method, url, params=None, headers=None, cookies=None, data=None,
          connector=None, proxy=None):
    """Make an HTTP request.

    If the request times out or one encounters a connection issue, it will be
    retried MAX_RETRIES times before finally raising hangups.NetworkError.

    Args:
        method: string, request method
        url: string, target URI
        params: dict, URI parameters
        headers: dict, request header
        cookies: dict, cookies used for the request
        data: dict, request post data
        connector: aiohttp.TCPConnector instance
        proxy: string, proxy url used for the request

    Returns:
        a FetchResponse instance.

    Raises:
        hangups.NetworkError: request invalid or timed out
    """
    logger.debug('Sending request %s %s:\n%r', method, url, data)
    for retry_num in range(MAX_RETRIES):
        try:
            res = yield from asyncio.wait_for(
                aiohttp.request(
                    method, url, params=params, headers=headers,
                    cookies=cookies, data=data, connector=connector,
                    proxy=proxy),
                CONNECT_TIMEOUT)
            body = yield from asyncio.wait_for(res.read(), REQUEST_TIMEOUT)
            logger.debug('Received response %d %s:\n%r', res.status,
                         res.reason, body)
        except asyncio.TimeoutError:
            error_msg = 'Request timed out'
        except aiohttp.ServerDisconnectedError as err:
            error_msg = 'Server disconnected error: {}'.format(err)
        except aiohttp.ClientError as err:
            error_msg = 'Request connection error: {}'.format(err)
        else:
            break
        logger.info('Request attempt %d failed: %s', retry_num, error_msg)
    else:
        logger.info('Request failed after %d attempts', MAX_RETRIES)
        raise exceptions.NetworkError(error_msg)

    if res.status != 200:
        logger.info('Request returned unexpected status: %d %s', res.status,
                    res.reason)
        raise exceptions.NetworkError(
            'Request return unexpected status: {}: {}'
            .format(res.status, res.reason))

    return FetchResponse(res.status, body)
