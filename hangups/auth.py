"""Simple Google auth"""

import requests
import time

# Prepare Requests Session with browser-like User-Agent
session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.132 Safari/537.36'})

def login(email, password):
    """Login to Google and return Response object"""
    r = session.get("https://accounts.google.com/ServiceLogin?passive=true&skipvpage=true&continue=https://talkgadget.google.com/talkgadget/gauth?verify%3Dtrue&authuser=0")
    text = r.text
    galx = r.cookies["GALX"]

    time.sleep(0.1)

    data = {
        "GALX": galx,
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
    text = r.text

    return r

def get_auth_cookies():
    """Return Google auth cookies dictionary"""
    req = requests.Request("GET", "https://talkgadget.google.com")
    mock_req = requests.cookies.MockRequest(req)
    cookies = session.cookies._cookies_for_request(mock_req)
    return {c.name: c.value for c in cookies}
