"""Google auth using OAuth2.0

This module logs the refresh_token, which can be revoked from
 https://security.google.com/settings/security/permissions.
The authorization is shown as "iOS device".

This code may be debugged by invoking it directly:
    python -m hangups.auth
"""

import requests
import logging
import json

logger = logging.getLogger(__name__)

OAUTH2_LOGIN_URL = (
    'https://accounts.google.com/o/oauth2/auth?'
    'scope=https://www.google.com/accounts/OAuthLogin%20https://www.googleapis'
    '.com/auth/userinfo.email&'
    'redirect_uri=urn:ietf:wg:oauth:2.0:oob&response_type=code&'
    'client_id=936475272427.apps.googleusercontent.com'
)
CLIENT_ID = '936475272427.apps.googleusercontent.com'
CLIENT_SECRET = 'KWsJlkaMn1jGLxQpWxMnOox-'


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


def _load_oauth2_refresh_token(oauth2_refresh_token_filename):
    """Return refresh_token loaded from file or None on failure."""
    logger.info('Attempting to load refresh_token from %s',
                oauth2_refresh_token_filename)
    try:
        with open(oauth2_refresh_token_filename) as f:
            refresh_token = f.read()
            logger.info('Using saved refresh_token: %s', refresh_token)
            return refresh_token
    except (IOError, ValueError):
        logger.info('Failed to load saved refresh_token')


def _save_oauth2_refresh_token(oauth2_refresh_token_filename, refresh_token):
    """Save refresh_token to file, ignoring failure."""
    logger.info('Attempting to save auth refresh_token to %s',
                oauth2_refresh_token_filename)
    try:
        with open(oauth2_refresh_token_filename, 'w') as f:
            f.write(refresh_token)
        logger.info('refresh_token saved')
    except IOError as e:
        logger.warning('Failed to save refresh_token: %s', e)
    return refresh_token


def get_auth(get_credentials_f, oauth2_refresh_token_filename):
    """Login into Google and return oauth2 as a dict.

    get_credentials_f() is called if credentials are required to log in, and
    should return oauth auth_token.

    The oauth2 are saved/loaded from oauth2_refresh_token_filename if possible,
    so credentials may not be necessary.

    Raises GoogleAuthError on failure.
    """
    refresh_token = _load_oauth2_refresh_token(oauth2_refresh_token_filename)
    auth_code = None

    if refresh_token is None:
        auth_code = get_credentials_f()

    session = requests.Session()

    if refresh_token:
        data = {'refresh_token': refresh_token, 'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET, 'grant_type': 'refresh_token'}
    else:
        data = {'code': auth_code, 'client_id': CLIENT_ID,
                'client_secret': CLIENT_SECRET,
                'grant_type': 'authorization_code',
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob'}

    r = session.post('https://accounts.google.com/o/oauth2/token', data=data)
    js = r.json()

    if 'refresh_token' in js:
        refresh_token = js['refresh_token']
        _save_oauth2_refresh_token(oauth2_refresh_token_filename,
                                   refresh_token)

    headers = {'Authorization': 'Bearer {}'.format(js['access_token'])}
    r = session.get(('https://accounts.google.com/accounts/OAuthLogin'
                     '?source=hangups&issueuberauth=1'), headers=headers)

    uberauth = r.text
    r = session.get('https://accounts.google.com/MergeSession')
    r = session.get(('https://accounts.google.com/MergeSession?'
                     'service=mail&continue=http://www.google.com&uberauth={}'
                    ).format(uberauth), headers=headers)

    oauth2 = _extract_cookies(session)
    return oauth2


def get_auth_stdin(oauth2_refresh_token_filename):
    """Wrapper for get_auth that prompts the user on stdin."""
    def get_credentials_f():
        """Prompt for and return credentials."""
        print("Please open the following URL in a browser")
        print(OAUTH2_LOGIN_URL)
        auth_token = input('Auth Token: ')
        return auth_token

    return get_auth(get_credentials_f, oauth2_refresh_token_filename)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print(get_auth_stdin('oauth2.json'))
