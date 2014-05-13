"""Simple Google auth supporting second factor.

Be careful not to log user credentials here.
"""

import requests
import logging
import getpass
import re
import json


logger = logging.getLogger(__name__)
FORM_RE = re.compile("id=\"(.+?)\"[\s]+value='(.+?)'",re.MULTILINE)
BROWSER_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/34.0.1847.132 Safari/537.36'
)


class GoogleAuthError(Exception): pass
"""Exception raised when auth fails."""


def _get_galx_token(session):
    """Retrieve GALX token necessary for Google auth."""
    r = session.get((
        "https://accounts.google.com/ServiceLogin?passive=true&skipvpage=true"
        "&continue=https://talkgadget.google.com/talkgadget/"
        "gauth?verify%3Dtrue&authuser=0"
    ))
    if r.status_code != 200:
        raise GoogleAuthError('Failed to get GALX token: request returned {}'
                              .format(r.status_code))
    try:
        galx = r.cookies["GALX"]
    except KeyError:
        raise GoogleAuthError(
            'Failed to get GALX token: cookie was not present'
        )
    return galx


def _send_credentials(session, email, password, galx_token, get_pin_f):
    """Send credentials to Google and return auth cookies."""
    data = {
        "GALX": galx_token,
        "continue": ('https://talkgadget.google.com/talkgadget/'
                     'gauth?verify=true'),
        "skipvpage": 'true',
        "_utf8": '☃',
        "bgresponse": 'js_disabled',
        "pstMsg": '0',
        "dnConn": '',
        "checkConnection": '',
        "checkedDomains": 'youtube',
        "Email": email,
        "Passwd": password,
        "signIn": 'Přihlásit se',
        "PersistentCookie": 'yes',
        "rmShown": '1'
    }
    r = session.post('https://accounts.google.com/ServiceLoginAuth', data=data)
    logger.debug('ServiceLoginAuth response: {} {}'
                 .format(r.status_code, r.url))
    SUCCESS_URL = ('https://talkgadget.google.com/'
                   'talkgadget/gauth?verify=true&pli=1')
    SECONDFACTOR_URL = 'https://accounts.google.com/SecondFactor'
    if r.status_code == 200 and r.url == SUCCESS_URL:
        pass # login success, no second factor
    elif r.status_code == 200 and r.url.startswith(SECONDFACTOR_URL):
        # If credentials are correct, but 2FA is required, it returns redirect
        # to SecondFactor. We have to parse some values out of the form.
        form_values = dict(FORM_RE.findall(r.text))
        try:
            timestamp = form_values['timeStmp']
            sec_token = form_values['secTok']
        except KeyError:
            raise GoogleAuthError(
                'Failed to extract timestamp and sec_token from form.'
            )
        _send_second_factor(session, get_pin_f(), timestamp, sec_token)
    else:
        # something else happened
        raise GoogleAuthError('Login failed for unknown reason')


def _send_second_factor(session, pin, timestamp, sec_token):
    """Send second factor to Google."""
    data = {
        'checkedDomains': 'youtube',
        'checkConnection': 'youtube:73:0',
        'pstMsg': '1',
        'timeStmp': timestamp,
        'secTok': sec_token,
        'smsToken': '',
        'smsUserPin': pin,
        'smsVerifyPin': 'Verify',
        'PersistentOptionSelection': '1',
        'PersistentCookie': 'on',
    }
    r = session.post('https://accounts.google.com/SecondFactor', data=data)
    logger.debug('SecondFactor response: {} {}'
                 .format(r.status_code, r.url))
    SUCCESS_URL = 'https://www.google.com/settings/personalinfo'
    if r.status_code == 200 and r.url == SUCCESS_URL:
        pass # success
    else:
        raise GoogleAuthError('Second factor failed')


def _get_auth_cookies(session):
    """Extract auth cookies from the session."""
    # Just using all the cookies from the session doesn't work in the second
    # factor case.
    req = requests.Request("GET", "https://talkgadget.google.com")
    mock_req = requests.cookies.MockRequest(req)
    cookies = session.cookies._cookies_for_request(mock_req)
    return {c.name: c.value for c in cookies}


def _verify_auth(cookies):
    """Return True if auth cookies are still valid."""
    # TODO: fix this
    # The set of cookies we end up with makes choosing a test URL tricky. I
    # haven't found one what works with and without 2FA.
    return True
    #URL = 'https://clients6.google.com/chat/v1/contacts/getselfinfo'
    #r = requests.post(URL, cookies=cookies, data='')
    #if r.status_code == 401: # unauthorized
    #    logger.info('Auth verification failed: {} {}'
    #                .format(r.status_code, r.url))
    #    return False
    #else:
    #    logger.info('Auth verification succeeded')
    #    return True


def get_auth(get_credentials_f, get_pin_f, cookie_filename):
    """Login into Google and return auth cookies.

    get_credentials_f() is called if credentials are required to log in, and
    should return (email, password). get_pin_f() is called if a pin is required
    to log in, and should return the pin.

    The cookies are saved/loaded from cookie_filename if possible, so
    credentials may not be necessary.

    Raises GoogleAuthError on failure.
    """
    logger.info('Attempting to load auth cookies from {}'
                .format(cookie_filename))
    try:
        with open(cookie_filename) as f:
            cookies = json.load(f)
            if _verify_auth(cookies):
                logger.info('Using saved auth cookies')
                return cookies
            else:
                logger.info('Saved auth cookies failed to verify')
    except (IOError, ValueError):
        logger.info('Failed to load saved auth cookies')

    # Prepare Requests Session with browser-like User-Agent
    session = requests.Session()
    session.headers.update({'User-Agent': BROWSER_USER_AGENT})

    email, password = get_credentials_f()
    galx = _get_galx_token(session)
    _send_credentials(session, email, password, galx, get_pin_f)
    cookies = _get_auth_cookies(session)

    logger.info('Attempting to save auth cookies to {}'
                .format(cookie_filename))
    try:
        with open(cookie_filename, 'w') as f:
            json.dump(cookies, f)
        logger.info('Auth cookies saved')
    except IOError as e:
        logger.warning('Failed to save auth cookies: {}'.format(e))
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
