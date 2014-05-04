# hangups

In May 2013 Google replaced their "Talk" instant messaging product, based on
XMPP, with "Hangouts", [which adopted a proprietary, non-interoperable
protocol](https://www.eff.org/deeplinks/2013/05/google-abandons-open-standards-instant-messaging).
For now it's still possible to connect to Hangouts over XMPP using a
third-party client like Pidgin, but features including group messaging are not
available.

hangups aims to be an open client for the undocumented Hangouts chat API.

## Status

* has basic Python methods for calling some API endpoints
* polling for events works
* sending chat messages to a conversation works
* login is not implemented, can be worked around by copying cookies from a
  browser
* recieving push events is not implemented (only polling)

## Running

Python 3.4 is required (earlier Python 3.x might work but is not tested).

`cookies.txt` is required to authenticate with Google. Copy your Google cookies
into this file. You can copy them directly from a request header.

```
python -m hangups
```
