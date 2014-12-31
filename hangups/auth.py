"""Simple Google auth supporting second factor.

This module should not log user credentials.

This code may be debugged by invoking it directly:
    python -m hangups.auth
"""

import robobrowser
import requests
import logging
import getpass
import json


logger = logging.getLogger(__name__)
LOGIN_URL = 'https://accounts.google.com/ServiceLogin'
SECONDFACTOR_URL = 'https://accounts.google.com/SecondFactor'


class GoogleAuthError(Exception):

    """Exception raised when auth fails."""


def _extract_cookies(session):
    """Extract auth cookies from the session to a dict."""
    # Just using all the cookies from the session doesn't work in the second
    # factor case.
    req = requests.Request("GET", "https://talkgadget.google.com")
    mock_req = requests.cookies.MockRequest(req)
    cookies = session.cookies._cookies_for_request(mock_req)
    return {c.name: c.value for c in cookies}


def _load_cookies(cookie_filename):
    """Return cookies loaded from file or None on failure."""
    logger.info('Attempting to load auth cookies from {}'
                .format(cookie_filename))
    try:
        with open(cookie_filename) as f:
            cookies = json.load(f)
            # TODO: Verify that the saved cookies are still valid and ignore
            # them if they are not.
            logger.info('Using saved auth cookies')
            return cookies
    except (IOError, ValueError):
        logger.info('Failed to load saved auth cookies')


def _save_cookies(cookie_filename, cookies):
    """Save cookies to file, ignoring failure."""
    logger.info('Attempting to save auth cookies to {}'
                .format(cookie_filename))
    try:
        with open(cookie_filename, 'w') as f:
            json.dump(cookies, f)
        logger.info('Auth cookies saved')
    except IOError as e:
        logger.warning('Failed to save auth cookies: {}'.format(e))
    return cookies


def _login(get_credentials_f, get_pin_f):
    """Login to Google and return logged in session."""
    logger.info('Starting Google login...')
    browser = robobrowser.RoboBrowser()

    browser.open(LOGIN_URL)
    if browser.response.status_code != 200:
        raise GoogleAuthError('Login form returned code {}'
                              .format(browser.response.status_code))
    form = browser.get_form(id='gaia_loginform')
    if form is None:
        raise GoogleAuthError('Failed to find login form')
    email, password = get_credentials_f()
    try:
        form['Email'] = email
    except KeyError:
        raise GoogleAuthError('Failed to find email field')
    try:
        form['Passwd'] = password
    except KeyError:
        raise GoogleAuthError('Failed to find password field')
    logger.info('Submitting login form...')
    browser.submit_form(form)

    if browser.response.url == SECONDFACTOR_URL:
        logger.info('Login requires second factor')
        form = browser.get_form(id='gaia_secondfactorform')
        if form is None:
            raise GoogleAuthError('Failed to find secondfactor form')
        pin = get_pin_f()
        try:
            form['smsUserPin'] = pin
        except KeyError:
            raise GoogleAuthError('Failed to find second factor PIN field')
        logger.info('Submitting second factor form...')
        try:
            # The form contains multiple submit inputs, so we need to specify
            # the correct one.
            browser.submit_form(form, submit=form['smsVerifyPin'])
        except KeyError:
            raise GoogleAuthError(
                'Failed to find second factor submission field')
    else:
        logger.info('Login does not require second factor')

    # Verify that the login was successful by checking the presence of a
    # cookie.
    if 'SSID' not in _extract_cookies(browser.session):
        raise GoogleAuthError('Login failed')
    return browser.session


def get_auth(get_credentials_f, get_pin_f, cookie_filename):
    """Login into Google and return cookies as a dict.

    get_credentials_f() is called if credentials are required to log in, and
    should return (email, password). get_pin_f() is called if a pin is required
    to log in, and should return the pin.

    The cookies are saved/loaded from cookie_filename if possible, so
    credentials may not be necessary.

    Raises GoogleAuthError on failure.
    """
    cookies = _load_cookies(cookie_filename)
    if cookies is not None:
        return cookies
    session = _login(get_credentials_f, get_pin_f)
    cookies = _extract_cookies(session)
    _save_cookies(cookie_filename, cookies)
    return cookies


def get_auth_stdin(cookie_filename):
    """Wrapper for get_auth that prompts the user on stdin."""
    def get_credentials_f():
        """Prompt for and return credentials."""
        email = input('Email: ')
        password = getpass.getpass()
        return (email, password)
    def get_pin_f():
        """Prompt for and return PIN."""
        return input('PIN: ')
    return get_auth(get_credentials_f, get_pin_f, cookie_filename)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print(get_auth_stdin('cookies.json'))
