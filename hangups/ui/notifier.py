"""Notifications for the hangups UI."""

import collections
import html
import logging
import re
import subprocess
import sys


logger = logging.getLogger(__name__)


Notification = collections.namedtuple('Notification', [
    'title', 'subtitle', 'message'
])


class Notifier:
    """Sends a desktop notification.

    This base class just discards the notification.
    """

    def send(self, notification):
        """Send a notification."""


class DefaultNotifier(Notifier):
    """Notifier that picks the best implementation for the current platform."""

    def __init__(self):
        # TODO: Make this smarter.
        if sys.platform == 'darwin':
            self._notifier = AppleNotifier()
        else:
            self._notifier = DbusNotifier()

    def send(self, notification):
        self._notifier.send(notification)


class BellNotifier(Notifier):
    """Notifier that rings the terminal bell."""

    def send(self, notification):
        sys.stdout.write('\a')


class DbusNotifier(Notifier):
    """Notifier that creates a freedesktop.org notification.

    The gdbus utility is used to avoid dependency on a DBus library.

    If a new notification is created while a previous one is still open, the
    previous notification is instantly replaced (see replaces_id).
    """
    NOTIFY_CMD = [
        'gdbus', 'call', '--session', '--dest',
        'org.freedesktop.Notifications', '--object-path',
        '/org/freedesktop/Notifications', '--method',
        'org.freedesktop.Notifications.Notify', 'hangups', '{replaces_id}', '',
        '{summary}', '{body}', '[]', '{{}}', ' -1'
    ]
    RESULT_RE = re.compile(r'\(uint32 ([\d]+),\)')

    def __init__(self):
        self._replaces_id = 0

    def send(self, notification):
        output = _run_command(self.NOTIFY_CMD, dict(
            summary=self._escape(notification.title),
            body=self._escape(notification.message),
            replaces_id=self._replaces_id,
        ))
        try:
            self._replaces_id = self.RESULT_RE.match(output).groups()[0]
        except (AttributeError, IndexError) as e:
            logger.info(
                'Failed to parse notification command result: %s', e
            )

    @staticmethod
    def _escape(text):
        # Escape HTML-style markup:
        res = html.escape(text, quote=False)
        # Escape other characters that cause issues with how gdbus parses
        # gvariants:
        res = res.replace('\\', '\\\\')
        res = res.replace('"', '\\u0022')
        res = res.replace('\'', '\\u0027')
        return res


class AppleNotifier(Notifier):
    """Notifier that displays an Apple macOS notification.

    The osascript utility is used to display a notification using AppleScript.
    """

    NOTIFY_CMD = [
        'osascript', '-e',
        ('display notification "{message}" with '
         'title "{title}" '
         'subtitle "{subtitle}"'),
    ]

    def send(self, notification):
        _run_command(self.NOTIFY_CMD, dict(
            title=self._escape(notification.title),
            subtitle=self._escape(notification.subtitle),
            message=self._escape(notification.message),
        ))

    @staticmethod
    def _escape(text):
        # Escape double quotes:
        return text.replace('"', '\\"')


def _run_command(args, format_values):
    cmd = [arg.format(**format_values) for arg in args]
    logger.info('Creating notification with command: %s', cmd)
    try:
        # Intentionally avoid using a shell to avoid a shell injection attack.
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # Only log at INFO level to prevent spam when command isn't available.
        logger.info('Notification command failed: %s', e)
        return ''
