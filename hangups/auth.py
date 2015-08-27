"""Google login authentication using OAuth 2.0.

Logging into Hangouts using OAuth2 requires a private scope only whitelisted
for certain clients. This module uses the client ID and secret from iOS, so it
will appear to Google to be an iOS device. Access can be revoked from this
page:
    https://security.google.com/settings/security/permissions

For safety of public debugging, this module should not log any user credentials
or tokens.

This code may be debugged by invoking it directly:
    python -m hangups.auth
"""

import requests
import logging
import urllib.parse

logger = logging.getLogger(__name__)
# Set the logging level for requests to at least INFO, since the DEBUG level
# will log sensitive data:
if logging.getLogger('requests').isEnabledFor(logging.DEBUG):
    logging.getLogger('requests').setLevel(logging.INFO)

OAUTH2_SCOPE = 'https://www.google.com/accounts/OAuthLogin'
OAUTH2_CLIENT_ID = '936475272427.apps.googleusercontent.com'
OAUTH2_CLIENT_SECRET = 'KWsJlkaMn1jGLxQpWxMnOox-'
OAUTH2_LOGIN_URL = 'https://accounts.google.com/o/oauth2/auth?{}'.format(
    urllib.parse.urlencode(dict(
        client_id=OAUTH2_CLIENT_ID,
        scope=OAUTH2_SCOPE,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob',
        response_type='code',
    ))
)
OAUTH2_TOKEN_REQUEST_URL = 'https://accounts.google.com/o/oauth2/token'


class GoogleAuthError(Exception):

    """Exception raised when auth fails."""


def _load_oauth2_refresh_token(refresh_token_filename):
    """Return refresh_token loaded from file or None on failure."""
    logger.info('Loading refresh_token from \'%s\'', refresh_token_filename)
    try:
        with open(refresh_token_filename) as f:
            return f.read()
    except IOError as e:
        logger.info('Failed to load refresh_token: %s', e)


def _save_oauth2_refresh_token(refresh_token_filename, refresh_token):
    """Save refresh_token to file, ignoring failure."""
    logger.info('Saving refresh_token to \'%s\'', refresh_token_filename)
    try:
        with open(refresh_token_filename, 'w') as f:
            f.write(refresh_token)
    except IOError as e:
        logger.warning('Failed to save refresh_token: %s', e)
    return refresh_token


def get_auth(get_code_f, refresh_token_filename):
    """Login into Google and return cookies as a dict.

    get_code_f() is called if authorization code is required to log in, and
    should return the code as a string.

    A refresh token is saved/loaded from refresh_token_filename if possible, so
    subsequent logins may not require re-authenticating.

    Raises GoogleAuthError on failure.
    """
    try:
        logger.info('Authenticating with refresh token')
        access_token = _auth_with_refresh_token(refresh_token_filename)
    except GoogleAuthError as e:
        logger.info('Failed to authenticate using refresh token: %s', e)
        logger.info('Authenticating with authorization code')
        access_token = _auth_with_code(get_code_f, refresh_token_filename)
    logger.info('Authentication successful')
    return _get_session_cookies(access_token)


def _auth_with_code(get_code_f, refresh_token_filename):
    """Authenticate using OAuth authentication code.

    Raises GoogleAuthError authentication fails.

    Return access token string.
    """
    # Get authentication code from user.
    auth_code = get_code_f()

    # Make a token request.
    token_request_data = {
        'client_id': OAUTH2_CLIENT_ID,
        'client_secret': OAUTH2_CLIENT_SECRET,
        'code': auth_code,
        'grant_type': 'authorization_code',
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
    }
    r = requests.post(OAUTH2_TOKEN_REQUEST_URL, data=token_request_data)
    res = r.json()

    # If an error occurred, a key 'error' will contain an error code.
    if 'error' in res:
        raise GoogleAuthError('Authorization error: \'{}\''
                              .format(res['error']))

    # Save the refresh token.
    _save_oauth2_refresh_token(refresh_token_filename, res['refresh_token'])

    return res['access_token']


def _auth_with_refresh_token(refresh_token_filename):
    """Authenticate using saved OAuth refresh token.

    Raises GoogleAuthError if refresh token is not found or authentication
    fails.

    Return access token string.
    """
    # Load saved refresh token if present.
    refresh_token = _load_oauth2_refresh_token(refresh_token_filename)
    if refresh_token is None:
        raise GoogleAuthError("Refresh token not found")

    # Make a token request.
    token_request_data = {
        'client_id': OAUTH2_CLIENT_ID,
        'client_secret': OAUTH2_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    r = requests.post(OAUTH2_TOKEN_REQUEST_URL, data=token_request_data)
    res = r.json()

    # If an error occurred, a key 'error' will contain an error code.
    if 'error' in res:
        raise GoogleAuthError('Authorization error: \'{}\''
                              .format(res['error']))

    return res['access_token']


def _get_session_cookies(access_token):
    """Use the access token to get session cookies.

    Return dict of cookies.
    """
    # Prevent ResourceWarning by using context manager to close session
    # connection.
    with requests.Session() as session:
        headers = {'Authorization': 'Bearer {}'.format(access_token)}
        r = session.get(('https://accounts.google.com/accounts/OAuthLogin'
                         '?source=hangups&issueuberauth=1'), headers=headers)
        uberauth = r.text
        r = session.get(('https://accounts.google.com/MergeSession?'
                         'service=mail&'
                         'continue=http://www.google.com&uberauth={}')
                        .format(uberauth), headers=headers)
        return session.cookies.get_dict(domain='.google.com')


def get_auth_stdin(refresh_token_filename):
    """Wrapper for get_auth that prompts the user on stdin."""
    def get_code_f():
        """Prompt for and return credentials."""
        print('To log in, open the following link in a browser and paste the '
              'provided authorization code below:\n')
        print(OAUTH2_LOGIN_URL)
        auth_token = input('\nAuthorization Token: ')
        return auth_token
    return get_auth(get_code_f, refresh_token_filename)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print(get_auth_stdin('oauth2.json'))
