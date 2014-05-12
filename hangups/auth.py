"""Simple Google auth

TODO:
    - Use a custom exception for errors
    - Add a cache so login can be saved
    - Remove the global session instance
    - Define API that allows the GUI layer to prompt for credentials including
      PIN if necessary
    - Port everything from requests to Tornado httpclient (will be tricky
      because of cookies)
"""

import requests
import logging
import getpass
import re


logger = logging.getLogger(__name__)


# Prepare Requests Session with browser-like User-Agent
session = requests.Session()
session.headers.update({'User-Agent': (
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/34.0.1847.132 Safari/537.36'
)})


FORM_RE = re.compile("id=\"(.+?)\"[\s]+value='(.+?)'",re.MULTILINE)

def get_galx_token():
    """Retrieve GALX token necessary for Google auth."""
    r = session.get((
        "https://accounts.google.com/ServiceLogin?passive=true&skipvpage=true"
        "&continue=https://talkgadget.google.com/talkgadget/"
        "gauth?verify%3Dtrue&authuser=0"
    ))
    if r.status_code != 200:
        raise ValueError('Failed to get GALX token: request returned {}'
                         .format(r.status_code))
    try:
        galx = r.cookies["GALX"]
    except KeyError:
        raise ValueError('Failed to get GALX token: cookie was not present')
    return galx


def send_credentials(email, password, galx_token):
    data = {
        "GALX": galx_token,
        "continue": "https://talkgadget.google.com/talkgadget/gauth?verify=true",
        "skipvpage": "true",
        "_utf8": "☃",
        "bgresponse": "js_disabled",
        "pstMsg": "0",
        "dnConn": "",
        "checkConnection": "",
        "checkedDomains": "youtube",
        "Email": email,
        "Passwd": password,
        "signIn": "Přihlásit se",
        "PersistentCookie": "yes",
        "rmShown": "1"
    }
    r = session.post("https://accounts.google.com/ServiceLoginAuth", data=data)
    logger.info('ServiceLoginAuth response: {} {}'
                .format(r.status_code, r.url))
    if (r.status_code == 200 and
            r.url == 'https://talkgadget.google.com/talkgadget/gauth?verify=true&pli=1'):
        # login success, no second factor
        pass
    elif (r.status_code == 200 and
          r.url.startswith('https://accounts.google.com/SecondFactor')):
        # If credentials are correct, but 2FA is required, returns redirect to
        # SecondFactor.
        form_values = dict(FORM_RE.findall(r.text))
        try:
            timestamp = form_values['timeStmp']
            sec_token = form_values['secTok']
        except KeyError:
            raise ValueError(
                'Failed to extract timestamp and sec_token from form.'
            )
        pin = input('Enter PIN: ')
        send_second_factor(pin, timestamp, sec_token)
    else:
        # something else happened
        raise ValueError('Login failed for unknown reason')


def send_second_factor(pin, timestamp, sec_token):
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
    logger.info('SecondFactor response: {} {}'
                .format(r.status_code, r.url))
    # on error, redirects to ServiceLogin
    if (r.status_code == 200 and
        r.url == 'https://www.google.com/settings/personalinfo'):
        pass # success
    else:
        raise ValueError('Section factor failed')


def get_auth_cookies():
    """Return Google auth cookies dictionary"""
    req = requests.Request("GET", "https://talkgadget.google.com")
    mock_req = requests.cookies.MockRequest(req)
    cookies = session.cookies._cookies_for_request(mock_req)
    return {c.name: c.value for c in cookies}


def login(email, password):
    """Login to Google and return cookie dict."""
    galx = get_galx_token()
    send_credentials(email, password, galx)
    return get_auth_cookies()


def demo():
    """Google login demo."""
    logging.basicConfig(level=logging.DEBUG)
    email = input('Email: ')
    password = getpass.getpass()
    print(login(email, password))


if __name__ == '__main__':
    demo()
