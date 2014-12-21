hangups
=======

.. image:: https://travis-ci.org/tdryer/hangups.svg?branch=master
    :target: https://travis-ci.org/tdryer/hangups
    :alt: Build Status

.. image:: https://readthedocs.org/projects/hangups/badge/?version=latest
    :target: https://readthedocs.org/projects/hangups/?badge=latest
    :alt: Documentation Status

hangups is the first third-party instant messaging client for `Google
Hangouts`_. It includes both a Python library and a reference client with a
text-based user interface.

Unlike its predecessor Google Talk, Hangouts uses a `proprietary,
non-interoperable protocol`_. hangups is implemented by reverse-engineering
this protocol, which allows it to support features like group messaging that
aren't available in clients that connect via XMPP.

hangups is still in an early stage of development. The reference client is
usable for basic chatting, but the API is undocumented and subject to change.
Bug reports and pull requests are welcome!

.. image:: https://github.com/tdryer/hangups/raw/master/screenshot.png
    :alt: hangups screenshot

.. _Google Hangouts: https://www.google.ca/hangouts/
.. _proprietary, non-interoperable protocol: https://www.eff.org/deeplinks/2013/05/google-abandons-open-standards-instant-messaging

Documentation
-------------

See the documentation for `installation and usage instructions`_.

.. _installation and usage instructions: http://hangups.readthedocs.org/

Projects using hangups
----------------------

- `HangoutsBot`_: Python Whistler Bot
- `HangupsBot`_: Bot for Google Hangouts
- `QHangups`_: Alternative client for Google Hangouts written in PyQt
- `bastardbot`_: A bot to follow and interact with Google Hangouts conversations
- `pickups`_: IRC gateway for hangups (prototype)
- `telepathy-hangups`_: Telepathy bindings for Google Chat via hangups library

.. _HangoutsBot: https://github.com/wardellchandler/HangoutsBot
.. _HangupsBot: https://github.com/xmikos/hangupsbot
.. _QHangups: https://github.com/xmikos/qhangups
.. _bastardbot: https://github.com/elamperti/bastardbot
.. _pickups: https://github.com/mtomwing/pickups
.. _telepathy-hangups: https://github.com/davidedmundson/telepathy-hangups
