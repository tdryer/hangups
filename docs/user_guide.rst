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

The first time you start hangups, you will be prompted to log into your Google
account with your email and password. If your account requires 2-step
verification, you will also be prompted for a PIN. After a successful login,
hangups will be able to log in automatically after starting.

hangups will only send your credentials to Google, and only session cookies
will be stored locally. By default, session cookies are stored in a file in an
OS-specific cache directory. The default cookie file location can be viewed
using :code:`hangups -h`. To specify a different cookie file, use the cookies
option::

  hangups --cookies /path/to/mycookies.json

If hangups is unable to access your account, try logging in through a browser
first, and try again.

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
configuration file. See the output of `hangups -h` for details.

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
