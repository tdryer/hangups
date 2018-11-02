"""Google login authentication using OAuth 2.0.

Logging into Hangouts using OAuth2 requires a private scope only whitelisted
for certain clients. This module uses the client ID and secret from iOS, so it
will appear to Google to be an iOS device. Access can be revoked from this
page:
    https://security.google.com/settings/security/activity

This module should avoid logging any sensitive login information.

This module may be tested by invoking it directly:
    python -m hangups.auth
"""

import getpass
import logging
import platform
import urllib.parse

import mechanicalsoup
import requests

from hangups import version

logger = logging.getLogger(__name__)
# Set the logging level for requests to at least INFO, since the DEBUG level
# will log sensitive data:
if logging.getLogger('requests').isEnabledFor(logging.DEBUG):
    logging.getLogger('requests').setLevel(logging.INFO)

OAUTH2_CLIENT_ID = '936475272427.apps.googleusercontent.com'
OAUTH2_CLIENT_SECRET = 'KWsJlkaMn1jGLxQpWxMnOox-'
OAUTH2_SCOPES = [
    'https://www.google.com/accounts/OAuthLogin',
    'https://www.googleapis.com/auth/userinfo.email',
]
# Note that '+' separating scopes must not be escaped by urlencode
OAUTH2_LOGIN_URL = (
    'https://accounts.google.com/o/oauth2/programmatic_auth?{}'.format(
        urllib.parse.urlencode(dict(
            scope='+'.join(OAUTH2_SCOPES),
            client_id=OAUTH2_CLIENT_ID,
        ), safe='+')
    )
)
OAUTH2_TOKEN_REQUEST_URL = 'https://accounts.google.com/o/oauth2/token'
FORM_SELECTOR = '#gaia_loginform'
EMAIL_SELECTOR = '#Email'
PASSWORD_SELECTOR = '#Passwd'
VERIFICATION_FORM_SELECTOR = '#challenge'
TOTP_CHALLENGE_SELECTOR = '[action="/signin/challenge/totp/2"]'
PHONE_CHALLENGE_SELECTOR = '[action="/signin/challenge/ipp/4"]'
TOTP_CODE_SELECTOR = '#totpPin'
PHONE_CODE_SELECTOR = '#idvPreregisteredPhonePin'
USER_AGENT = 'hangups/{} ({} {})'.format(
    version.__version__, platform.system(), platform.machine()
)


class GoogleAuthError(Exception):
    """A Google authentication request failed."""


class CredentialsPrompt(object):
    """Callbacks for prompting user for their Google account credentials.

    This implementation prompts the user in a terminal using standard in/out.
    """

    @staticmethod
    def get_email():
        """Prompt for email.

        Returns:
            str: Google account email address.
        """
        print('Sign in with your Google account:')
        return input('Email: ')

    @staticmethod
    def get_password():
        """Prompt for password.

        Returns:
            str: Google account password.
        """
        return getpass.getpass()

    @staticmethod
    def get_verification_code():
        """Prompt for verification code.

        Returns:
            str: Google account verification code.
        """
        return input('Verification code: ')


class RefreshTokenCache(object):
    """File-based cache for refresh token.

    Args:
        FILENAme (str): Path to file where refresh token will be cached.
    """

    def __init__(self, filename):
        self._filename = filename

    def get(self):
        """Get cached refresh token.

        Returns:
            Cached refresh token, or ``None`` on failure.
        """
        logger.info(
            'Loading refresh_token from %s', repr(self._filename)
        )
        try:
            with open(self._filename) as f:
                return f.read()
        except IOError as e:
            logger.info('Failed to load refresh_token: %s', e)

    def set(self, refresh_token):
        """Cache a refresh token, ignoring any failure.

        Args:
            refresh_token (str): Refresh token to cache.
        """
        logger.info('Saving refresh_token to %s', repr(self._filename))
        try:
            with open(self._filename, 'w') as f:
                f.write(refresh_token)
        except IOError as e:
            logger.warning('Failed to save refresh_token: %s', e)


def get_auth(credentials_prompt, refresh_token_cache):
    """Authenticate with Google.

    Args:
        refresh_token_cache (RefreshTokenCache): Cache to use so subsequent
            logins may not require credentials.
        credentials_prompt (CredentialsPrompt): Prompt to use if credentials
            are required to log in.

    Returns:
        dict: Google session cookies.

    Raises:
        GoogleAuthError: If authentication with Google fails.
    """
    with requests.Session() as session:
        session.headers = {'user-agent': USER_AGENT}

        try:
            logger.info('Authenticating with refresh token')
            refresh_token = refresh_token_cache.get()
            if refresh_token is None:
                raise GoogleAuthError("Refresh token not found")
            access_token = _auth_with_refresh_token(session, refresh_token)
        except GoogleAuthError as e:
            logger.info('Failed to authenticate using refresh token: %s', e)
            logger.info('Authenticating with credentials')
            authorization_code = _get_authorization_code(
                session, credentials_prompt
            )
            access_token, refresh_token = _auth_with_code(
                session, authorization_code
            )
            refresh_token_cache.set(refresh_token)

        logger.info('Authentication successful')
        return _get_session_cookies(session, access_token)


def get_auth_stdin(refresh_token_filename):
    """Simple wrapper for :func:`get_auth` that prompts the user using stdin.

    Args:
        refresh_token_filename (str): Path to file where refresh token will be
            cached.

    Raises:
        GoogleAuthError: If authentication with Google fails.
    """
    refresh_token_cache = RefreshTokenCache(refresh_token_filename)
    return get_auth(CredentialsPrompt(), refresh_token_cache)

def get_auth_manual(refresh_token_filename):
    print('Open this URL:')
    print(OAUTH2_LOGIN_URL)

    print('after logging in and reaching the loading screen, open DevTools and copy the Oauth code from Application -> Cookies -> https://accounts.google.com -> oauth_code -> value')

    authorization_code = input('Enter oauth_code cookie value: ')

    with requests.Session() as session:
        session.headers = {'user-agent': USER_AGENT}
        access_token, refresh_token = _auth_with_code(
            session, authorization_code)
        refresh_token_cache = RefreshTokenCache(refresh_token_filename)
        return refresh_token_cache.set(refresh_token)


class Browser(object):
    """Virtual browser for submitting forms and moving between pages.

    Raises GoogleAuthError if URL fails to load.
    """

    def __init__(self, session, url):
        self._session = session
        self._browser = mechanicalsoup.Browser(
            soup_config=dict(features='html.parser'), session=self._session
        )
        try:
            self._page = self._browser.get(url)
            self._page.raise_for_status()
        except requests.RequestException as e:
            raise GoogleAuthError('Failed to load form: {}'.format(e))

    def has_selector(self, selector):
        """Return True if selector matches an element on the current page."""
        return len(self._page.soup.select(selector)) > 0

    def submit_form(self, form_selector, input_dict):
        """Populate and submit a form on the current page.

        Raises GoogleAuthError if form can not be submitted.
        """
        logger.info(
            'Submitting form on page %r', self._page.url.split('?')[0]
        )
        logger.info(
            'Page contains forms: %s',
            [elem.get('id') for elem in self._page.soup.select('form')]
        )
        try:
            form = self._page.soup.select(form_selector)[0]
        except IndexError:
            raise GoogleAuthError(
                'Failed to find form {!r} in page'.format(form_selector)
            )
        logger.info(
            'Page contains inputs: %s',
            [elem.get('id') for elem in form.select('input')]
        )
        for selector, value in input_dict.items():
            try:
                form.select(selector)[0]['value'] = value
            except IndexError:
                raise GoogleAuthError(
                    'Failed to find input {!r} in form'.format(selector)
                )
        try:
            self._page = self._browser.submit(form, self._page.url)
            self._page.raise_for_status()
        except requests.RequestException as e:
            raise GoogleAuthError('Failed to submit form: {}'.format(e))

    def get_cookie(self, name):
        """Return cookie value from the browser session.

        Raises KeyError if cookie is not found.
        """
        return self._session.cookies[name]


def _get_authorization_code(session, credentials_prompt):
    """Get authorization code using Google account credentials.

    Because hangups can't use a real embedded browser, it has to use the
    Browser class to enter the user's credentials and retrieve the
    authorization code, which is placed in a cookie. This is the most fragile
    part of the authentication process, because a change to a login form or an
    unexpected prompt could break it.

    Raises GoogleAuthError authentication fails.

    Returns authorization code string.
    """
    browser = Browser(session, OAUTH2_LOGIN_URL)

    email = credentials_prompt.get_email()
    browser.submit_form(FORM_SELECTOR, {EMAIL_SELECTOR: email})

    password = credentials_prompt.get_password()
    browser.submit_form(FORM_SELECTOR, {PASSWORD_SELECTOR: password})

    if browser.has_selector(TOTP_CHALLENGE_SELECTOR):
        browser.submit_form(TOTP_CHALLENGE_SELECTOR, {})
    elif browser.has_selector(PHONE_CHALLENGE_SELECTOR):
        browser.submit_form(PHONE_CHALLENGE_SELECTOR, {})

    if browser.has_selector(VERIFICATION_FORM_SELECTOR):
        if browser.has_selector(TOTP_CODE_SELECTOR):
            input_selector = TOTP_CODE_SELECTOR
        elif browser.has_selector(PHONE_CODE_SELECTOR):
            input_selector = PHONE_CODE_SELECTOR
        else:
            raise GoogleAuthError('Unknown verification code input')
        verfification_code = credentials_prompt.get_verification_code()
        browser.submit_form(
            VERIFICATION_FORM_SELECTOR, {input_selector: verfification_code}
        )

    try:
        return browser.get_cookie('oauth_code')
    except KeyError:
        raise GoogleAuthError('Authorization code cookie not found')


def _auth_with_refresh_token(session, refresh_token):
    """Authenticate using OAuth refresh token.

    Raises GoogleAuthError if authentication fails.

    Returns access token string.
    """
    # Make a token request.
    token_request_data = {
        'client_id': OAUTH2_CLIENT_ID,
        'client_secret': OAUTH2_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
    }
    res = _make_token_request(session, token_request_data)
    return res['access_token']


def _auth_with_code(session, authorization_code):
    """Authenticate using OAuth authorization code.

    Raises GoogleAuthError if authentication fails.

    Returns access token string and refresh token string.
    """
    # Make a token request.
    token_request_data = {
        'client_id': OAUTH2_CLIENT_ID,
        'client_secret': OAUTH2_CLIENT_SECRET,
        'code': authorization_code,
        'grant_type': 'authorization_code',
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
    }
    res = _make_token_request(session, token_request_data)
    return res['access_token'], res['refresh_token']


def _make_token_request(session, token_request_data):
    """Make OAuth token request.

    Raises GoogleAuthError if authentication fails.

    Returns dict response.
    """
    try:
        r = session.post(OAUTH2_TOKEN_REQUEST_URL, data=token_request_data)
        r.raise_for_status()
    except requests.RequestException as e:
        raise GoogleAuthError('Token request failed: {}'.format(e))
    else:
        res = r.json()
        # If an error occurred, a key 'error' will contain an error code.
        if 'error' in res:
            raise GoogleAuthError(
                'Token request error: {!r}'.format(res['error'])
            )
        return res


def _get_session_cookies(session, access_token):
    """Use the access token to get session cookies.

    Raises GoogleAuthError if session cookies could not be loaded.

    Returns dict of cookies.
    """
    headers = {'Authorization': 'Bearer {}'.format(access_token)}

    try:
        r = session.get(('https://accounts.google.com/accounts/OAuthLogin'
                         '?source=hangups&issueuberauth=1'), headers=headers)
        r.raise_for_status()
    except requests.RequestException as e:
        raise GoogleAuthError('OAuthLogin request failed: {}'.format(e))
    uberauth = r.text

    try:
        r = session.get(('https://accounts.google.com/MergeSession?'
                         'service=mail&'
                         'continue=http://www.google.com&uberauth={}')
                        .format(uberauth), headers=headers)
        r.raise_for_status()
    except requests.RequestException as e:
        raise GoogleAuthError('MergeSession request failed: {}'.format(e))

    cookies = session.cookies.get_dict(domain='.google.com')
    if cookies == {}:
        raise GoogleAuthError('Failed to find session cookies')
    return cookies


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    print(get_auth_stdin('refresh_token.txt'))
