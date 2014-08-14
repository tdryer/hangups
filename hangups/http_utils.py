"""Utility functions for HTTP requests."""

from tornado import gen, concurrent, ioloop, httputil, httpclient
import datetime
import http
import logging

logger = logging.getLogger(__name__)


@concurrent.return_future
def sleep(seconds, callback=None):
    """Return a future that finishes after a given number of seconds."""
    ioloop.IOLoop.instance().add_timeout(datetime.timedelta(seconds=seconds),
                                         callback)


class TimeoutFuture(concurrent.Future):

    """Future that wraps another future so it can be run with a timeout.

    Useful for request timeouts and backoffs.
    """

    def __init__(self, future, timeout_seconds):
        super().__init__()
        future.add_done_callback(self.done_callback)
        sleep(timeout_seconds).add_done_callback(self.done_callback)

    def done_callback(self, future):
        self.set_result(future)


@gen.coroutine
def fetch(url, method='GET', params=None, headers=None, cookies=None,
          data=None, streaming_callback=None, header_callback=None,
          connect_timeout=None, request_timeout=None):
    """Make an HTTP request and return a Future.

    This is mostly just a wrapper for tornado.httpclient, but adds support for
    sending cookies.

    Raises HTTPError and IOError.
    """
    if headers is None:
        headers = {}
    if params is not None:
        url = httputil.url_concat(url, params)
    if cookies is not None:
        # abuse SimpleCookie to escape our cookies for us
        simple_cookies = http.cookies.SimpleCookie(cookies)
        headers['cookie'] = '; '.join(val.output(header='')[1:]
                                      for val in simple_cookies.values())
    http_client = httpclient.AsyncHTTPClient()
    res = yield http_client.fetch(httpclient.HTTPRequest(
        httputil.url_concat(url, params), method=method,
        headers=httputil.HTTPHeaders(headers), body=data,
        streaming_callback=streaming_callback, header_callback=header_callback,
        connect_timeout=connect_timeout, request_timeout=request_timeout
    ))
    return res


@gen.coroutine
def longpoll_fetch(url, method='GET', params=None, headers=None, cookies=None,
                   data=None, streaming_callback=None, connect_timeout=None,
                   request_timeout=None, data_timeout=None):
    """Make a long-polling request and return a Future.

    The future finishes when the request is closed. If the response code is
    2xx, streaming_callback is called with byte data as it arrives.

    The data_timeout is the number of seconds which may elapse with no data
    being received before the connection is considered dead.

    Raises HTTPError and IOError.
    """
    error = False
    new_data = False
    response_code = None  # Persistent state for the header callback

    def _streaming_callback(data):
        """Internal callback for response data."""
        nonlocal error, new_data
        # Call the real streaming_callback only if no error has occurred.
        if error:
            logger.info('Long-polling request ignoring data because of error')
        else:
            logger.info('Long-polling request received data')
            new_data = True
            streaming_callback(data)

    def _header_callback(line):
        """Internal callback for header lines."""
        nonlocal error, response_code
        # If this is the first line of the response, parse it for the response
        # code. An error has occured if the response_code is not 2xx.
        if response_code == None:
            response_code = int(line.split(' ')[1])
            logger.info('Long-polling request received response start, code={}'
                        .format(response_code))
            if response_code >= 300 or response_code < 200:
                error = True

    logger.info('Starting long-polling request: {}'.format(url))
    future = fetch(
        url, method=method, params=params, headers=headers, cookies=cookies,
        data=data, streaming_callback=_streaming_callback,
        header_callback=_header_callback, connect_timeout=connect_timeout,
        request_timeout=request_timeout
    )
    while not future.done():
        # Wait until the request finishes, or the timeout expires, whichever
        # happens first.
        if data_timeout:
            yield TimeoutFuture(future, data_timeout)
        else:
            yield future
        # If the timeout expired and no new data arrived, the request has timed
        # out.
        if new_data or future.done():
            new_data = False
        else:
            logger.info('Long-polling request timed out')
            error = True
            raise IOError('timed out waiting for data')
    logger.info('Long-polling request finished')
    return future.result()
