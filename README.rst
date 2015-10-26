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

- `HangupsBot`_: Bot for Google Hangouts
- `Hubot Hangouts Adapter`_: Hubot adapter using hangups
- `QHangups`_: Alternative client for Google Hangouts written in PyQt
- `Ubuntu Hangups`_: Unofficial Google Hangouts client for Ubuntu Touch
- `bastardbot`_: A bot to follow and interact with Google Hangouts conversations
- `hangoutsbot/hangoutsbot`_: Google Hangouts bot
- `hangups.el`_: Hangouts interface for Emacs
- `pickups`_: IRC gateway for hangups (prototype)
- `telepathy-hangups`_: Telepathy bindings for Google Chat via hangups library
- `wardellchandler/HangoutsBot`_: Python 3 Bot for Hangouts

.. _HangupsBot: https://github.com/xmikos/hangupsbot
.. _Hubot Hangouts Adapter: https://github.com/groupby/hubot-hangups
.. _QHangups: https://github.com/xmikos/qhangups
.. _Ubuntu Hangups: https://github.com/tim-sueberkrueb/ubuntu-hangups
.. _bastardbot: https://github.com/elamperti/bastardbot
.. _hangoutsbot/hangoutsbot: https://github.com/hangoutsbot/hangoutsbot
.. _hangups.el: https://github.com/jtamagnan/hangups.el
.. _pickups: https://github.com/mtomwing/pickups
.. _telepathy-hangups: https://github.com/davidedmundson/telepathy-hangups
.. _wardellchandler/HangoutsBot: https://github.com/wardellchandler/HangoutsBot

Related projects
----------------

- `Hangish`_: A Google Hangouts native client for Sailfish
- `hangupsjs`_: Port of hangups to Node.js
- `hangover`_: The first native Mac OS X client for Google Hangouts

.. _Hangish: https://github.com/rogora/hangish
.. _hangupsjs: https://github.com/algesten/hangupsjs
.. _hangover: https://github.com/psobot/hangover
