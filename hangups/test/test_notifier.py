import subprocess
import unittest.mock

from hangups.ui import notifier


NOTIFICATION = notifier.Notification(
    'John Cleese', 'Cheese Shop', 'How about a little red Leicester?'
)
MOCK_DBUS = unittest.mock.patch(
    'subprocess.check_output', autospec=True, return_value=b'(uint32 7,)\n'
)
MOCK_APPLE = unittest.mock.patch(
    'subprocess.check_output', autospec=True, return_value=b''
)


def test_bell_notifier(capsys):
    notifier.BellNotifier().send(NOTIFICATION)
    assert capsys.readouterr() == ('\a', '')


def test_dbus_notifier():
    with MOCK_DBUS as check_output:
        notifier.DbusNotifier().send(NOTIFICATION)
    check_output.assert_called_once_with([
        'gdbus', 'call', '--session',
        '--dest', 'org.freedesktop.Notifications',
        '--object-path', '/org/freedesktop/Notifications',
        '--method', 'org.freedesktop.Notifications.Notify',
        'hangups', '0', '', 'John Cleese', 'How about a little red Leicester?',
        '[]', '{}', ' -1'
    ], stderr=subprocess.STDOUT)


def test_dbus_notifier_replaces_id():
    dbus_notifier = notifier.DbusNotifier()
    with MOCK_DBUS as check_output:
        dbus_notifier.send(NOTIFICATION)
        assert check_output.call_args[0][0][10] == '0'
        dbus_notifier.send(NOTIFICATION)
        assert check_output.call_args[0][0][10] == '7'


def test_dbus_notifier_escaping():
    evil_notification = notifier.Notification(
        '<b>title</b> \\ \' "', None, '<b>message</b> \\ \' "'
    )
    with MOCK_DBUS as check_output:
        notifier.DbusNotifier().send(evil_notification)
    assert check_output.call_args[0][0][12:14] == [
        '&lt;b&gt;title&lt;/b&gt; \\\\ \\u0027 \\u0022',
        '&lt;b&gt;message&lt;/b&gt; \\\\ \\u0027 \\u0022',
    ]


def test_apple_notifier():
    with MOCK_APPLE as check_output:
        notifier.AppleNotifier().send(NOTIFICATION)
    check_output.assert_called_once_with([
        'osascript', '-e',
        'display notification "How about a little red Leicester?" '
        'with title "John Cleese" subtitle "Cheese Shop"'
    ], stderr=subprocess.STDOUT)


def test_apple_notifier_escaping():
    evil_notification = notifier.Notification(
        'title "', 'subtitle "', 'message "'
    )
    with MOCK_APPLE as check_output:
        notifier.AppleNotifier().send(evil_notification)
    assert check_output.call_args[0][0][2] == (
        'display notification "message \\"" '
        'with title "title \\"" subtitle "subtitle \\""'
    )


def test_default_notifier():
    default_notifier = notifier.DefaultNotifier()
    # pylint: disable=protected-access
    mock_send = unittest.mock.patch.object(
        default_notifier._notifier, 'send', autospec=True
    )
    with mock_send as send:
        default_notifier.send(NOTIFICATION)
    send.assert_called_once_with(NOTIFICATION)
