User Guide
==========

This section is intended for end-users who want to use the textual user
interface included with hangups.

Running
-------

Once installed, run this command to start hangups::

  hangups

For help with command line arguments, run::

  hangups -h

Logging in
----------

The first time you start hangups, you will need to log in to your Google
account. hangups supports logging in using `OAuth 2.0`_. You will be prompted
to open a link in your browser. Google will prompt you to authorize the
application, and then provide an authorization code. Copy and paste the
authorization code into hangups to complete the process.

After a successful login, hangups will save a refresh token allowing it to
login automatically. By default, the token is saved to a file in an OS-specific
cache directory. The default token file path can be viewed using :code:`hangups
-h`. To specify a different path for the token file, use the
:code:`--token-path` option::

  hangups --token-path /path/to/refresh_token.txt

hangups may be deauthorized from your Google account from the `Google Account
Permissions page`_. hangups will be listed as "iOS device".

.. _OAuth 2.0: http://oauth.net/2/
.. _`Google Account Permissions page`: https://security.google.com/settings/security/permissions

Usage
-----

After connecting, hangups will display the conversations tab, which lists the
names of all the available conversations. Use the up and down arrow keys to
select a conversation, and press :code:`enter` to open it in a new tab.

hangups uses a tabbed interface. The first tab is always the conversations
tab. Once multiple tabs are open, use :code:`ctrl+u` and :code:`ctrl+d` and
move up and down the list of tabs. Use :code:`ctrl+w` to close a tab.

In a conversation tab, type a message and press :code:`enter` to send it, or
use the up and arrows to scroll the list of previous messages.

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

Configuration
-------------

hangups may be configured through both command line arguments and a
configuration file. See the output of `hangups -h` for details on using both of
these methods.

Keybindings are specified using `urwid's format`_, for example: `ctrl e` or
`shift ctrl e`. Some key combinations may be unavailable due to terminal
limitations or conflicts.

.. _urwid's format: http://urwid.org/manual/userinput.html#keyboard-input

Troubleshooting
---------------

hangups can log information that may be useful for troubleshooting a problem.
Run :code:`hangups -h` to view the default log file path.

To specify a custom log file path, run::

  hangups --log /path/to/mylog

To log detailed debugging messages, run::

  hangups -d
