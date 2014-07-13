"""Graphical notifications for the hangups UI.

TODO:
    - Support different notification systems either by allowing NOTIFY_CMD to
    be customized, or by implementing Notifier subclasses.
    - Replace notify-send with something that supports merging notifications.
    - Create notifications for other events like (dis)connection
"""

import logging
import subprocess

logger = logging.getLogger(__name__)
NOTIFY_CMD = ['notify-send', '{sender_name}', '{msg_text}']


class Notifier(object):

    """Receives events from hangups and creates system notifications."""

    def __init__(self, client, conv_list):
        self._conv_list = conv_list  # hangups.ConversationList
        self._client = client  # hangups.Client
        self._client.on_message += self._on_message

    def _on_message(self, client, conv_id, user_id, timestamp, text):
        """Create notification for new messages."""
        conv = self._conv_list.get(conv_id)
        user = conv.get_user(user_id)
        # Ignore messages sent by yourself.
        if not user.is_self:
            cmd = [arg.format(
                sender_name=user.full_name,
                msg_text=text,
            ) for arg in NOTIFY_CMD]
            logger.info('Creating notification with command: {}'.format(cmd))
            # Run the command without blocking, and without a shell. Since the
            # command is a list of arguments, and we're not using a shell, this
            # should be safe.
            subprocess.Popen(cmd)
