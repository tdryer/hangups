# hangups

hangups is a Python library for writing instant messaging clients that
interoperate with [Google Hangouts][2]. hangups also includes a reference
client with a command line user interface.

In May 2013, Google replaced their "Talk" instant messaging product, based on
XMPP, with "Hangouts", which adopted a [proprietary, non-interoperable
protocol][1]. Because of this, hangouts must be implemented by
reverse-engineering. For now it's still possible to connect to Hangouts using
the standard XMPP protocol, but this restricts features like group messaging
that hangups allows.

hangups is working, but is pre-alpha quality. The API will change, and it
shouldn't be relied on for serious work.

![screenshot](screenshot.png)

[1]: https://www.eff.org/deeplinks/2013/05/google-abandons-open-standards-instant-messaging
[2]: https://www.google.ca/hangouts/

## What works

* logging in (with second factor support)
* switching between conversations
* receiving chat messages and other events via push
* sending chat messages

## Running

Python 3.4 is required (Python 3.3 might work but is not tested).

```
pip install -r requirements.txt
py.test
python -m hangups
```

Follow the prompts to log into your Google account. In the Conversations tab,
use arrow keys to scroll through the list of existing conversations, and press
return to select one. In a conversation, use arrow keys to scroll through
messages and to select the "Send message" box. Type a message and press return
to send it. At any time you use use ctrl+d and ctrl+u to switch between tabs.
