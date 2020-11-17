hangups
=======

.. image:: https://github.com/tdryer/hangups/workflows/CI/badge.svg
    :target: https://github.com/tdryer/hangups/actions?query=workflow%3ACI+branch%3Amaster
    :alt: CI Status

.. image:: https://readthedocs.org/projects/hangups/badge/?version=latest
    :target: https://hangups.readthedocs.io/
    :alt: Documentation Status

.. image:: https://snapcraft.io//hangups/badge.svg
    :target: https://snapcraft.io/hangups
    :alt: Snap Status

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

.. _installation and usage instructions: https://hangups.readthedocs.io/

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
- `jabber-hangouts-transport`_: A Jabber/XMPP transport/gateway to Hangouts.
- `ovkulkarni/hangoutsbot`_: Google Hangouts Bot using SQL
- `defund/pearl`_: Google Hangouts bot framework
- `HangupsDroid`_: Unofficial Google Hangouts client for Android
- `chat-archive`_: Easy to use offline chat archive
- `SoulSen/Hanger`_: Modern, Simple, Asynchronous bot framework for Google Hangouts

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
.. _jabber-hangouts-transport: https://github.com/ZeWaren/jabber-hangouts-transport
.. _ovkulkarni/hangoutsbot: https://github.com/ovkulkarni/hangoutsbot
.. _defund/pearl: https://github.com/defund/pearl
.. _HangupsDroid: https://github.com/Rudloff/hangupsdroid
.. _chat-archive: https://github.com/xolox/python-chat-archive
.. _SoulSen/Hanger: https://github.com/SoulSen/Hanger

Related projects
----------------

- `Hangish`_: A Google Hangouts native client for Sailfish
- `Hangups-UWP`_: Hangups client for Universal Windows Platform
- `Parrot`_: The next generation messenger
- `WTalk`_: Client library and desktop client for Google Hangouts written in C#
- `YakYak`_: Desktop client for Google Hangouts
- `go-hangups`_: Port of hangups to Go
- `hangover`_: The first native Mac OS X client for Google Hangouts
- `hangups-rs`_: Port of hangups to Rust
- `hangupsjs`_: Port of hangups to Node.js
- `purple-hangouts`_: Hangouts plugin for libpurple
- `slangouts`_: A Hangouts/Slack bridge

.. _Hangish: https://github.com/rogora/hangish
.. _Hangups-UWP: https://github.com/kfechter/Hangups-UWP
.. _Parrot: https://github.com/avaidyam/Parrot
.. _WTalk: https://github.com/madagaga/WTalk
.. _YakYak: https://github.com/yakyak/yakyak
.. _go-hangups: https://github.com/gpavlidi/go-hangups
.. _hangover: https://github.com/psobot/hangover
.. _hangups-rs: https://github.com/tdryer/hangups-rs
.. _hangupsjs: https://github.com/algesten/hangupsjs
.. _purple-hangouts: https://github.com/EionRobb/purple-hangouts
.. _slangouts: https://github.com/gpavlidi/slangouts
