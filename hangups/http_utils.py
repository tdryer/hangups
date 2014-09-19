"""Utility function for making HTTP requests."""

import aiohttp
import asyncio
import collections
import logging

from hangups import exceptions

logger = logging.getLogger(__name__)
CONNECT_TIMEOUT = 10
REQUEST_TIMEOUT = 30

FetchResponse = collections.namedtuple('FetchResponse', ['code', 'body'])


@asyncio.coroutine
def fetch(method, url, params=None, headers=None, cookies=None, data=None,
          connector=None):
    """Make an HTTP request.

    Raises hanups.NetworkError if the request fails.

    TODO: Add automatic retry on failure
    """
    try:
        res = yield from asyncio.wait_for(aiohttp.request(
            method, url, params=params, headers=headers, cookies=cookies,
            data=data, connector=connector
        ), CONNECT_TIMEOUT)
        body = yield from asyncio.wait_for(res.read(), REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        raise exceptions.NetworkError('Request timed out')
    except aiohttp.errors.ConnectionError as e:
        raise exceptions.NetworkError('Request connection error: {}'.format(e))
    if res.status > 200 or res.status < 200:
        raise exceptions.NetworkError('Request return unexpected status: {}: {}'
                                      .format(res.status, res.reason))
    return FetchResponse(res.status, body)
