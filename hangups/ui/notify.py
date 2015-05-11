"""Graphical notifications for the hangups UI.

TODO:
    - Support other notification systems (like terminal bell).
    - Support notify-osd's merged notifications. It appears this would require
    using a dbus library so that each notification comes from the same process.
    - Create notifications for other events like (dis)connection
"""

import html
import logging
import re
import subprocess
import sys

import hangups
from hangups.ui.utils import get_conv_name

logger = logging.getLogger(__name__)
if sys.platform == 'darwin':
    NOTIFY_CMD = [
        'osascript', '-e',
        ('display notification "{msg_text}" with '
         'title "{convo_name}" '
         'subtitle "{sender_name}"'),
    ]
    NOTIFY_ESCAPER = lambda s: s.replace('"', '\\"')
else:
    NOTIFY_CMD = [
        'gdbus', 'call', '--session', '--dest',
        'org.freedesktop.Notifications', '--object-path',
        '/org/freedesktop/Notifications', '--method',
        'org.freedesktop.Notifications.Notify', 'hangups', '{replaces_id}', '',
        '{sender_name}', '{msg_text}', '[]', '{{}}', ' -1'
    ]
    def NOTIFY_ESCAPER(text):
        """Escape text for passing into gdbus."""
        # Prevent the notifier from interpreting markup:
        res = html.escape(text, quote=False)
        # Prevent issues with how gdbus parses gvariants:
        res = res.replace('\\', '\\\\')
        res = res.replace('"', '\\u0022')
        res = res.replace('\'', '\\u0027')
        return res
RESULT_RE = re.compile(r'\(uint32 ([\d]+),\)')


class Notifier(object):

    """Receives events from hangups and creates system notifications.

    This uses the gdbus utility to create freedesktop.org notifications. If a
    new notification is created while a previous one is still open, the
    previous notification is instantly replaced.
    """

    def __init__(self, conv_list):
        self._conv_list = conv_list  # hangups.ConversationList
        self._conv_list.on_event.add_observer(self._on_event)
        self._replaces_id = 0

    def _on_event(self, conv_event):
        """Create notification for new messages."""
        conv = self._conv_list.get(conv_event.conversation_id)
        user = conv.get_user(conv_event.user_id)
        # Ignore non-messages or messages sent by yourself.
        show_notification = all((
            isinstance(conv_event, hangups.ChatMessageEvent),
            not user.is_self,
            not conv.is_quiet,
        ))
        if show_notification:
            # We have to escape angle brackets because freedesktop.org
            # notifications support markup.
            cmd = [arg.format(
                sender_name=NOTIFY_ESCAPER(user.full_name),
                msg_text=NOTIFY_ESCAPER(conv_event.text),
                replaces_id=self._replaces_id,
                convo_name=NOTIFY_ESCAPER(get_conv_name(conv)),
            ) for arg in NOTIFY_CMD]

            # Run the notification and parse out the replaces_id. Since the
            # command is a list of arguments, and we're not using a shell, this
            # should be safe.
            logger.info('Creating notification with command: {}'.format(cmd))
            try:
                output = subprocess.check_output(
                    cmd, stderr=subprocess.STDOUT
                ).decode()
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                # Only log this at INFO level to prevent log spam when gdbus
                # isn't available.
                logger.info('Notification command failed: {}'.format(e))
                return
            try:
                self._replaces_id = RESULT_RE.match(output).groups()[0]
            except (AttributeError, IndexError) as e:
                logger.warning('Failed to parse notification command '
                               'result: {}'.format(e))
