hangups
=======

.. image:: https://travis-ci.org/tdryer/hangups.svg?branch=master
    :target: https://travis-ci.org/tdryer/hangups
    :alt: Build Status

hangups is the first third-party instant messaging client for `Google
Hangouts`_.

Unlike its predecessor Google Talk, Hangouts uses a `proprietary,
non-interoperable protocol`_. hangups is implemented by reverse-engineering
this protocol, which allows it to support features like group messaging that
aren't available in clients that connect via XMPP.

hangups is still in an early stage of development. It's usable for basic
chatting, but users should keep another client handy. Bug reports, feature
requests, and pull requests are welcome.

.. image:: https://github.com/tdryer/hangups/raw/master/screenshot.png
    :alt: hangups screenshot

.. _Google Hangouts: https://www.google.ca/hangouts/
.. _proprietary, non-interoperable protocol: https://www.eff.org/deeplinks/2013/05/google-abandons-open-standards-instant-messaging


Trying it out
-------------

Python 3.3 or higher is required. To install the latest version of hangups,
run: ::

 pip install hangups

Or check out the repository and run: ::

 python setup.py install

Run ``hangups --help`` to see available options. Start hangups by running
``hangups``.

The first time you start hangups, you will be prompted to log into your Google
account. Your credentials will only be sent to Google, and only session cookies
will be stored locally. If you have trouble logging in, try logging in through
a browser first.

hangups uses a tabbed interface. The first tab is always the conversations list
tab, which lets you use the up/down arrow keys to select an existing
conversation and open it in a new tab by pressing enter. Once you have multiple
tabs open, you can use ctrl+u and ctrl+d and move up and down the list of tabs.

In a conversation tab, type a message and press enter to send it, or use the
up/down arrows to scroll the list of previous messages.
