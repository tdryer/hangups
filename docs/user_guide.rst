User Guide
==========

This page is intended for end-users who want to use the textual user interface
included with hangups.

Running
-------

Once installed, run this command to start hangups::

  hangups

For help with command line arguments, run::

  hangups -h

Logging in
----------

The first time you start hangups, you need to log into your Google account.

.. caution::
    Never give your Google account credentials to any application or device
    that you don't trust. Logging into Google grants hangups unrestricted
    access to your account. hangups works this way because Google does not
    provide any other method to access the Hangouts API.

You will be prompted to enter your Google email address, password, and
verification code (if applicable).

If this login method fails, try the manual login method instead::

  hangups --manual-login

After a successful login, hangups will save a refresh token allowing it to
login automatically. By default, the token is saved to a file in an OS-specific
cache directory. The default token file path can be viewed using :code:`hangups
-h`. To specify a different path for the token file, use the
:code:`--token-path` option::

  hangups --token-path /path/to/refresh_token.txt

hangups may be deauthorized from your Google account using the `Google recently
used devices page`_. hangups will be listed as "hangups" (or "iOS" in older
versions).

.. _OAuth 2.0: http://oauth.net/2/
.. _`Google recently used devices page`: https://security.google.com/settings/security/activity

Usage
-----

After connecting, hangups will display the conversations tab, which lists the
names of all the available conversations. Use the up and down arrow keys to
select a conversation, and press :code:`enter` to open it in a new tab.

hangups uses a tabbed interface. The first tab is always the conversations
tab. Once multiple tabs are open, use :code:`ctrl+u` and :code:`ctrl+d` and
move up and down the list of tabs. Use :code:`ctrl+w` to close a tab.

In a conversation tab, type a message and press :code:`enter` to send it, or
use the up and arrows to scroll the list of previous messages. hangups
supports readline commands for editing text. See the `readlike library
documentation`_ for a full list. Note that some of hangouts' bindings
conflict with these key combinations, see the Configuration section on how to
adjust key bindings.

When new messages arrive, hangups will open a conversation tab in the
background, and display the number of unread messages in the tab title. On
Linux (with an appropriate desktop notification service running) and Mac OS X,
hangups will also display a desktop notification. To mark messages as read,
press any key (such as :code:`enter`) while in a conversation tab.

When the network connection is interrupted, hangups will show a "Disconnected"
message in each conversation. When the connection is restored a "Connected"
message is shown, and hangups will attempt to sync any messages that were
missed during the disconnection. If hangups is disconnected for too long, it
will eventually exit.

To exit hangups, press :code:`ctrl+e`.

.. _readlike library documentation: https://pypi.python.org/pypi/readlike

Configuration
-------------

hangups may be configured through both command line arguments and a
configuration file. See the output of `hangups -h` for details on using both of
these methods.

Keybindings are specified using `urwid's format`_, for example: `ctrl e` or
`shift ctrl e`. Some key combinations may be unavailable due to terminal
limitations or conflicts.

.. _urwid's format: http://urwid.org/manual/userinput.html#keyboard-input

Colours are specified using `urwid's colors`_, for example: `dark red` or
`Xresources color1`. Standard Foreground and Background Colors can be found here
for 16 bit palette.

.. _urwid's colors: http://urwid.org/reference/constants.html#standard-background-and-foreground-colors

Constants for 88-Color and 256-Color palettes for `urwid's hcolors`_.

.. _urwid's hcolors: http://urwid.org/manual/displayattributes.html#high-colors


Troubleshooting
---------------

hangups can log information that may be useful for troubleshooting a problem.
Run :code:`hangups -h` to view the default log file path.

To specify a custom log file path, run::

  hangups --log /path/to/mylog

To log detailed debugging messages, run::

  hangups -d
