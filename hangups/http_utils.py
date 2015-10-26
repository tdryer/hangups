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

FetchResponse = collections.namedtuple('FetchResponse', ['code', 'body',
                                                         'cookies'])


@asyncio.coroutine
def fetch(method, url, params=None, headers=None, cookies=None, data=None,
          connector=None):
    """Make an HTTP request.

    If the request times out or a encounters a connection issue, it will be
    retried MAX_RETRIES times before finally raising hangups.NetworkError.

    Returns FetchResponse.
    """
    logger.debug('Sending request %s %s:\n%r', method, url, data)
    error_msg = None
    for retry_num in range(MAX_RETRIES):
        try:
            res = yield from asyncio.wait_for(aiohttp.request(
                method, url, params=params, headers=headers, cookies=cookies,
                data=data, connector=connector
            ), CONNECT_TIMEOUT)
            body = yield from asyncio.wait_for(res.read(), REQUEST_TIMEOUT)
            logger.debug('Received response %d %s:\n%r', res.status,
                         res.reason, body)
        except asyncio.TimeoutError:
            error_msg = 'Request timed out'
        except aiohttp.ClientError as e:
            error_msg = 'Request connection error: {}'.format(e)
        except aiohttp.ServerDisconnectedError as e:
            error_msg = 'Server disconnected error: {}'.format(e)
        else:
            error_msg = None
            break
        logger.info('Request attempt %d failed: %s', retry_num, error_msg)
    if error_msg:
        logger.info('Request failed after %d attempts', MAX_RETRIES)
        raise exceptions.NetworkError(error_msg)
    if res.status > 200 or res.status < 200:
        logger.info('Request returned unexpected status: %d %s', res.status,
                    res.reason)
        raise exceptions.NetworkError(
            'Request return unexpected status: {}: {}'
            .format(res.status, res.reason)
        )
    cookie_dict = {name: morsel.value for name, morsel in res.cookies.items()}
    return FetchResponse(res.status, body, cookie_dict)
