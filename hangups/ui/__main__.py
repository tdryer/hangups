"""Reference chat client for hangups."""

import appdirs
import asyncio
import configargparse
import contextlib
import logging
import os
import sys
import urwid
import readlike
from bisect import bisect

import hangups
from hangups.ui.emoticon import replace_emoticons
from hangups.ui import notifier
from hangups.ui.utils import get_conv_name, add_color_to_scheme


# hangups used to require a fork of urwid called hangups-urwid which may still
# be installed and create a conflict with the 'urwid' package name. See #198.
if urwid.__version__ == '1.2.2-dev':
    sys.exit('error: hangups-urwid package is installed\n\n'
             'Please uninstall hangups-urwid and urwid, and reinstall '
             'hangups.')


LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
COL_SCHEMES = {
    # Very basic scheme with no colour
    'default': {
        ('active_tab', '', ''),
        ('inactive_tab', 'standout', ''),
        ('msg_date', '', ''),
        ('msg_sender', '', ''),
        ('msg_self', '', ''),
        ('msg_text', '', ''),
        ('msg_text_self', '', ''),
        ('msg_watermark', '', ''),
        ('msg_selected', 'standout', ''),
        ('status_line', 'standout', ''),
        ('tab_background', 'standout', ''),
    },
    'solarized-dark': {
        ('active_tab', 'light gray', 'light blue'),
        ('inactive_tab', 'underline', 'light green'),
        ('msg_date', 'dark cyan', ''),
        ('msg_sender', 'dark blue', ''),
        ('msg_text_self', '', ''),
        ('msg_self', 'dark green', ''),
        ('msg_text', '', ''),
        ('msg_watermark', 'light gray', ''),
        ('msg_selected', 'standout', ''),
        ('status_line', 'standout', ''),
        ('tab_background', 'black,standout,underline', 'light green'),
    },
}
COL_SCHEME_NAMES = (
    'active_tab', 'inactive_tab', 'msg_date', 'msg_sender', 'msg_self',
    'msg_text', 'msg_text_self', 'status_line', 'tab_background'
)

DISCREET_NOTIFICATION = notifier.Notification(
    'hangups', 'Conversation', 'New message'
)


class HangupsDisconnected(Exception):
    """Raised when hangups is disconnected."""


class ChatUI:
    """User interface for hangups."""

    def __init__(self, refresh_token_path, keybindings, palette,
                 palette_colors, datetimefmt, notifier_,
                 discreet_notifications, manual_login, keep_emoticons):
        """Start the user interface."""
        self._keys = keybindings
        self._datetimefmt = datetimefmt
        self._notifier = notifier_
        self._discreet_notifications = discreet_notifications
        self._keep_emoticons = keep_emoticons

        set_terminal_title('hangups')

        # These are populated by on_connect when it's called.
        self._conv_widgets = {}  # {conversation_id: ConversationWidget}
        self._tabbed_window = None  # TabbedWindowWidget
        self._conv_list = None  # hangups.ConversationList
        self._user_list = None  # hangups.UserList
        self._coroutine_queue = CoroutineQueue()
        self._exception = None

        # TODO Add urwid widget for getting auth.
        try:
            cookies = hangups.auth.get_auth_stdin(
                refresh_token_path, manual_login
            )
        except hangups.GoogleAuthError as e:
            sys.exit('Login failed ({})'.format(e))

        self._client = hangups.Client(cookies)
        self._client.on_connect.add_observer(self._on_connect)

        loop = asyncio.get_event_loop()
        loop.set_exception_handler(self._exception_handler)
        try:
            self._urwid_loop = urwid.MainLoop(
                LoadingWidget(), palette, handle_mouse=False,
                input_filter=self._input_filter,
                event_loop=urwid.AsyncioEventLoop(loop=loop)
            )
        except urwid.AttrSpecError as e:
            # Fail gracefully for invalid colour options.
            sys.exit(e)

        self._urwid_loop.screen.set_terminal_properties(colors=palette_colors)
        self._urwid_loop.start()

        coros = [self._connect(), self._coroutine_queue.consume()]

        # Enable bracketed paste mode after the terminal has been switched to
        # the alternate screen (after MainLoop.start() to work around bug
        # 729533 in VTE.
        with bracketed_paste_mode():
            try:
                # Run all the coros, until they all complete or one raises an
                # exception. In the normal case, HangupsDisconnected will be
                # raised.
                loop.run_until_complete(asyncio.gather(*coros))
            except HangupsDisconnected:
                pass
            finally:
                # Clean up urwid.
                self._urwid_loop.stop()

                # Cancel all of the coros, and wait for them to shut down.
                task = asyncio.gather(*coros, return_exceptions=True)
                task.cancel()
                try:
                    loop.run_until_complete(task)
                except asyncio.CancelledError:
                    # In Python 3.7, asyncio.gather no longer swallows
                    # CancelledError, so we need to ignore it.
                    pass

                loop.close()

        # If an exception was stored, raise it now. This is used for exceptions
        # originating in urwid callbacks.
        if self._exception:
            raise self._exception  # pylint: disable=raising-bad-type

    async def _connect(self):
        await self._client.connect()
        raise HangupsDisconnected()

    def _exception_handler(self, _loop, context):
        """Handle exceptions from the asyncio loop."""
        # Start a graceful shutdown.
        self._coroutine_queue.put(self._client.disconnect())

        # Store the exception to be re-raised later. If the context doesn't
        # contain an exception, create one containing the error message.
        default_exception = Exception(context.get('message'))
        self._exception = context.get('exception', default_exception)

    def _input_filter(self, keys, _):
        """Handle global keybindings."""
        if keys == [self._keys['menu']]:
            if self._urwid_loop.widget == self._tabbed_window:
                self._show_menu()
            else:
                self._hide_menu()
        elif keys == [self._keys['quit']]:
            self._coroutine_queue.put(self._client.disconnect())
        else:
            return keys

    def _show_menu(self):
        """Show the overlay menu."""
        # If the current widget in the TabbedWindowWidget has a menu,
        # overlay it on the TabbedWindowWidget.
        current_widget = self._tabbed_window.get_current_widget()
        if hasattr(current_widget, 'get_menu_widget'):
            menu_widget = current_widget.get_menu_widget(self._hide_menu)
            overlay = urwid.Overlay(menu_widget, self._tabbed_window,
                                    align='center', width=('relative', 80),
                                    valign='middle', height=('relative', 80))
            self._urwid_loop.widget = overlay

    def _hide_menu(self):
        """Hide the overlay menu."""
        self._urwid_loop.widget = self._tabbed_window

    def get_conv_widget(self, conv_id):
        """Return an existing or new ConversationWidget."""
        if conv_id not in self._conv_widgets:
            set_title_cb = (lambda widget, title:
                            self._tabbed_window.set_tab(widget, title=title))
            widget = ConversationWidget(
                self._client, self._coroutine_queue,
                self._conv_list.get(conv_id), set_title_cb, self._keys,
                self._datetimefmt, self._keep_emoticons
            )
            self._conv_widgets[conv_id] = widget
        return self._conv_widgets[conv_id]

    def add_conversation_tab(self, conv_id, switch=False):
        """Add conversation tab if not present, and optionally switch to it."""
        conv_widget = self.get_conv_widget(conv_id)
        self._tabbed_window.set_tab(conv_widget, switch=switch,
                                    title=conv_widget.title)

    def on_select_conversation(self, conv_id):
        """Called when the user selects a new conversation to listen to."""
        # switch to new or existing tab for the conversation
        self.add_conversation_tab(conv_id, switch=True)

    async def _on_connect(self):
        """Handle connecting for the first time."""
        self._user_list, self._conv_list = (
            await hangups.build_user_conversation_list(self._client)
        )
        self._conv_list.on_event.add_observer(self._on_event)

        # show the conversation menu
        conv_picker = ConversationPickerWidget(self._conv_list,
                                               self.on_select_conversation,
                                               self._keys)
        self._tabbed_window = TabbedWindowWidget(self._keys)
        self._tabbed_window.set_tab(conv_picker, switch=True,
                                    title='Conversations')
        self._urwid_loop.widget = self._tabbed_window

    def _on_event(self, conv_event):
        """Open conversation tab for new messages & pass events to notifier."""
        conv = self._conv_list.get(conv_event.conversation_id)
        user = conv.get_user(conv_event.user_id)
        show_notification = all((
            isinstance(conv_event, hangups.ChatMessageEvent),
            not user.is_self,
            not conv.is_quiet,
        ))
        if show_notification:
            self.add_conversation_tab(conv_event.conversation_id)
            if self._discreet_notifications:
                notification = DISCREET_NOTIFICATION
            else:
                notification = notifier.Notification(
                    user.full_name, get_conv_name(conv), conv_event.text
                )
            self._notifier.send(notification)


class CoroutineQueue:
    """Coroutine queue for the user interface.

    Urwid executes callback functions for user input rather than coroutines.
    This creates a problem if we need to execute a coroutine in response to
    user input.

    One option is to use asyncio.ensure_future to execute a "fire and forget"
    coroutine. If we do this, exceptions will be logged instead of propagated,
    which can obscure problems.

    This class allows callbacks to place coroutines into a queue, and have them
    executed by another coroutine. Exceptions will be propagated from the
    consume method.
    """

    def __init__(self):
        self._queue = asyncio.Queue()

    def put(self, coro):
        """Put a coroutine in the queue to be executed."""
        # Avoid logging when a coroutine is queued or executed to avoid log
        # spam from coroutines that are started on every keypress.
        assert asyncio.iscoroutine(coro)
        self._queue.put_nowait(coro)

    async def consume(self):
        """Consume coroutines from the queue by executing them."""
        while True:
            coro = await self._queue.get()
            assert asyncio.iscoroutine(coro)
            await coro


class WidgetBase(urwid.WidgetWrap):
    """Base for UI Widgets

    This class overrides the property definition for the method ``keypress`` in
    ``urwid.WidgetWrap``. Using a method that overrides the property saves
    many pylint suppressions.

    Args:
        target: urwid.Widget instance
    """
    def keypress(self, size, key):
        """forward the call"""
        # pylint:disable=not-callable, useless-super-delegation
        return super().keypress(size, key)


class LoadingWidget(WidgetBase):
    """Widget that shows a loading indicator."""

    def __init__(self):
        # show message in the center of the screen
        super().__init__(urwid.Filler(
            urwid.Text('Connecting...', align='center')
        ))


class RenameConversationDialog(WidgetBase):
    """Dialog widget for renaming a conversation."""

    def __init__(self, coroutine_queue, conversation, on_cancel, on_save,
                 keybindings):
        self._coroutine_queue = coroutine_queue
        self._conversation = conversation
        edit = urwid.Edit(edit_text=get_conv_name(conversation))
        items = [
            urwid.Text('Rename conversation:'),
            edit,
            urwid.Button(
                'Save',
                on_press=lambda _: self._rename(edit.edit_text, on_save)
            ),
            urwid.Button('Cancel', on_press=lambda _: on_cancel()),
        ]
        list_walker = urwid.SimpleFocusListWalker(items)
        list_box = ListBox(keybindings, list_walker)
        super().__init__(list_box)

    def _rename(self, name, callback):
        """Rename conversation and call callback."""
        self._coroutine_queue.put(self._conversation.rename(name))
        callback()


class ConversationMenu(WidgetBase):
    """Menu for conversation actions."""

    def __init__(self, coroutine_queue, conversation, close_callback,
                 keybindings):
        rename_dialog = RenameConversationDialog(
            coroutine_queue, conversation,
            lambda: frame.contents.__setitem__('body', (list_box, None)),
            close_callback, keybindings
        )
        items = [
            urwid.Text(
                'Conversation name: {}'.format(get_conv_name(conversation))
            ),
            urwid.Button(
                'Change Conversation Name',
                on_press=lambda _: frame.contents.__setitem__(
                    'body', (rename_dialog, None)
                )
            ),
            urwid.Divider('-'),
            urwid.Button('Back', on_press=lambda _: close_callback()),
        ]
        list_walker = urwid.SimpleFocusListWalker(items)
        list_box = ListBox(keybindings, list_walker)
        frame = urwid.Frame(list_box)
        padding = urwid.Padding(frame, left=1, right=1)
        line_box = urwid.LineBox(padding, title='Conversation Menu')
        super().__init__(line_box)


class ConversationButton(WidgetBase):
    """Button that shows the name and unread message count of conversation."""

    def __init__(self, conversation, on_press):
        conversation.on_event.add_observer(self._on_event)
        # Need to update on watermark notifications as well since no event is
        # received when the user marks messages as read.
        conversation.on_watermark_notification.add_observer(self._on_event)
        self._conversation = conversation
        self._button = urwid.Button(self._get_label(), on_press=on_press,
                                    user_data=conversation.id_)
        super().__init__(self._button)

    def _get_label(self):
        """Return the button's label generated from the conversation."""
        return get_conv_name(self._conversation, show_unread=True)

    def _on_event(self, _):
        """Update the button's label when an event occurs."""
        self._button.set_label(self._get_label())

    @property
    def last_modified(self):
        """Last modified date of conversation, used for sorting."""
        return self._conversation.last_modified


class ConversationListWalker(urwid.SimpleFocusListWalker):
    """ListWalker that maintains a list of ConversationButtons.

    ConversationButtons are kept in order of last modified.
    """

    # pylint: disable=abstract-method

    def __init__(self, conversation_list, on_select):
        self._conversation_list = conversation_list
        self._conversation_list.on_event.add_observer(self._on_event)
        self._on_press = lambda button, conv_id: on_select(conv_id)
        convs = sorted(conversation_list.get_all(), reverse=True,
                       key=lambda c: c.last_modified)
        buttons = [ConversationButton(conv, on_press=self._on_press)
                   for conv in convs]
        super().__init__(buttons)

    def _on_event(self, _):
        """Re-order the conversations when an event occurs."""
        # TODO: handle adding new conversations
        self.sort(key=lambda conv_button: conv_button.last_modified,
                  reverse=True)


class ListBox(WidgetBase):
    """ListBox widget supporting alternate keybindings."""

    def __init__(self, keybindings, list_walker):
        self._keybindings = keybindings
        super().__init__(urwid.ListBox(list_walker))

    def keypress(self, size, key):
        # Handle alternate up/down keybindings
        key = super().keypress(size, key)
        if key == self._keybindings['down']:
            super().keypress(size, 'down')
        elif key == self._keybindings['up']:
            super().keypress(size, 'up')
        elif key == self._keybindings['page_up']:
            super().keypress(size, 'page up')
        elif key == self._keybindings['page_down']:
            super().keypress(size, 'page down')
        else:
            return key


class ConversationPickerWidget(WidgetBase):
    """ListBox widget for picking a conversation from a list."""

    def __init__(self, conversation_list, on_select, keybindings):
        list_walker = ConversationListWalker(conversation_list, on_select)
        list_box = ListBox(keybindings, list_walker)
        widget = urwid.Padding(list_box, left=2, right=2)
        super().__init__(widget)


class ReturnableEdit(urwid.Edit):
    """Edit widget that clears itself and calls a function on return."""

    def __init__(self, on_return, keybindings, caption=None):
        super().__init__(caption=caption, multiline=True)
        self._on_return = on_return
        self._keys = keybindings
        self._paste_mode = False

    def keypress(self, size, key):
        if key == 'begin paste':
            self._paste_mode = True
        elif key == 'end paste':
            self._paste_mode = False
        elif key == 'enter' and not self._paste_mode:
            self._on_return(self.get_edit_text())
            self.set_edit_text('')
        elif key not in self._keys.values() and key in readlike.keys():
            text, pos = readlike.edit(self.edit_text, self.edit_pos, key)
            self.set_edit_text(text)
            self.set_edit_pos(pos)
        else:
            return super().keypress(size, key)


class StatusLineWidget(WidgetBase):
    """Widget for showing status messages.

    If the client is disconnected, show a reconnecting message. If a temporary
    message is showing, show the temporary message. If someone is typing, show
    a typing messages.
    """

    _MESSAGE_DELAY_SECS = 10

    def __init__(self, client, conversation):
        self._typing_statuses = {}
        self._conversation = conversation
        self._conversation.on_event.add_observer(self._on_event)
        self._conversation.on_typing.add_observer(self._on_typing)
        self._widget = urwid.Text('', align='center')
        self._is_connected = True
        self._message = None
        self._message_handle = None
        client.on_disconnect.add_observer(self._on_disconnect)
        client.on_reconnect.add_observer(self._on_reconnect)
        super().__init__(urwid.AttrMap(self._widget, 'status_line'))

    def show_message(self, message_str):
        """Show a temporary message."""
        if self._message_handle is not None:
            self._message_handle.cancel()
        self._message_handle = asyncio.get_event_loop().call_later(
            self._MESSAGE_DELAY_SECS, self._clear_message
        )
        self._message = message_str
        self._update()

    def _clear_message(self):
        """Clear the temporary message."""
        self._message = None
        self._message_handle = None
        self._update()

    def _on_disconnect(self):
        """Show reconnecting message when disconnected."""
        self._is_connected = False
        self._update()

    def _on_reconnect(self):
        """Hide reconnecting message when reconnected."""
        self._is_connected = True
        self._update()

    def _on_event(self, conv_event):
        """Make users stop typing when they send a message."""
        if isinstance(conv_event, hangups.ChatMessageEvent):
            self._typing_statuses[conv_event.user_id] = (
                hangups.TYPING_TYPE_STOPPED
            )
            self._update()

    def _on_typing(self, typing_message):
        """Handle typing updates."""
        self._typing_statuses[typing_message.user_id] = typing_message.status
        self._update()

    def _update(self):
        """Update status text."""
        typing_users = [self._conversation.get_user(user_id)
                        for user_id, status in self._typing_statuses.items()
                        if status == hangups.TYPING_TYPE_STARTED]
        displayed_names = [user.first_name for user in typing_users
                           if not user.is_self]
        if displayed_names:
            typing_message = '{} {} typing...'.format(
                ', '.join(sorted(displayed_names)),
                'is' if len(displayed_names) == 1 else 'are'
            )
        else:
            typing_message = ''

        if not self._is_connected:
            self._widget.set_text("RECONNECTING...")
        elif self._message is not None:
            self._widget.set_text(self._message)
        else:
            self._widget.set_text(typing_message)


class MessageWidget(WidgetBase):

    """Widget for displaying a single message in a conversation."""

    def __init__(self, timestamp, text, datetimefmt, user=None,
                 show_date=False, watermark_users=None):
        # Save the timestamp as an attribute for sorting.
        self.timestamp = timestamp
        text = [
            ('msg_date', self._get_date_str(timestamp, datetimefmt,
                                            show_date=show_date) + ' '),
            ('msg_text_self' if user is not None and user.is_self
             else 'msg_text', text)
        ]
        if user is not None:
            text.insert(1, ('msg_self' if user.is_self else 'msg_sender',
                            user.first_name + ': '))

        if watermark_users is not None and bool(watermark_users):
            sorted_users = sorted([x.first_name for x in watermark_users])
            watermark = "\n[ Seen by {}. ]".format(', '.join(sorted_users))
            text.append(('msg_watermark', watermark))

        self._widget = urwid.SelectableIcon(text, cursor_position=0)
        super().__init__(urwid.AttrMap(
            self._widget, '', {
                # If the widget is focused, map every other display attribute
                # to 'msg_selected' so the entire message is highlighted.
                None: 'msg_selected',
                'msg_date': 'msg_selected',
                'msg_text_self': 'msg_selected',
                'msg_text': 'msg_selected',
                'msg_self': 'msg_selected',
                'msg_sender': 'msg_selected',
                'msg_watermark': 'msg_selected',
            }
        ))

    @staticmethod
    def _get_date_str(timestamp, datetimefmt, show_date=False):
        """Convert UTC datetime into user interface string."""
        fmt = ''
        if show_date:
            fmt += '\n'+datetimefmt.get('date', '')+'\n'
        fmt += datetimefmt.get('time', '')
        return timestamp.astimezone(tz=None).strftime(fmt)

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    @staticmethod
    def from_conversation_event(conversation, conv_event, prev_conv_event,
                                datetimefmt, watermark_users=None):
        """Return MessageWidget representing a ConversationEvent.

        Returns None if the ConversationEvent does not have a widget
        representation.
        """
        user = conversation.get_user(conv_event.user_id)
        # Check whether the previous event occurred on the same day as this
        # event.
        if prev_conv_event is not None:
            is_new_day = (conv_event.timestamp.astimezone(tz=None).date() !=
                          prev_conv_event.timestamp.astimezone(tz=None).date())
        else:
            is_new_day = False
        if isinstance(conv_event, hangups.ChatMessageEvent):
            return MessageWidget(conv_event.timestamp, conv_event.text,
                                 datetimefmt, user, show_date=is_new_day,
                                 watermark_users=watermark_users)
        elif isinstance(conv_event, hangups.RenameEvent):
            if conv_event.new_name == '':
                text = ('{} cleared the conversation name'
                        .format(user.first_name))
            else:
                text = ('{} renamed the conversation to {}'
                        .format(user.first_name, conv_event.new_name))
            return MessageWidget(conv_event.timestamp, text, datetimefmt,
                                 show_date=is_new_day,
                                 watermark_users=watermark_users)
        elif isinstance(conv_event, hangups.MembershipChangeEvent):
            event_users = [conversation.get_user(user_id) for user_id
                           in conv_event.participant_ids]
            names = ', '.join([user.full_name for user in event_users])
            if conv_event.type_ == hangups.MEMBERSHIP_CHANGE_TYPE_JOIN:
                text = ('{} added {} to the conversation'
                        .format(user.first_name, names))
            else:  # LEAVE
                text = ('{} left the conversation'.format(names))
            return MessageWidget(conv_event.timestamp, text, datetimefmt,
                                 show_date=is_new_day,
                                 watermark_users=watermark_users)
        elif isinstance(conv_event, hangups.HangoutEvent):
            text = {
                hangups.HANGOUT_EVENT_TYPE_START: (
                    'A Hangout call is starting.'
                ),
                hangups.HANGOUT_EVENT_TYPE_END: (
                    'A Hangout call ended.'
                ),
                hangups.HANGOUT_EVENT_TYPE_ONGOING: (
                    'A Hangout call is ongoing.'
                ),
            }.get(conv_event.event_type, 'Unknown Hangout call event.')
            return MessageWidget(conv_event.timestamp, text, datetimefmt,
                                 show_date=is_new_day,
                                 watermark_users=watermark_users)
        elif isinstance(conv_event, hangups.GroupLinkSharingModificationEvent):
            status_on = hangups.GROUP_LINK_SHARING_STATUS_ON
            status_text = ('on' if conv_event.new_status == status_on
                           else 'off')
            text = '{} turned {} joining by link.'.format(user.first_name,
                                                          status_text)
            return MessageWidget(conv_event.timestamp, text, datetimefmt,
                                 show_date=is_new_day,
                                 watermark_users=watermark_users)
        else:
            # conv_event is a generic hangups.ConversationEvent.
            text = 'Unknown conversation event'
            return MessageWidget(conv_event.timestamp, text, datetimefmt,
                                 show_date=is_new_day,
                                 watermark_users=watermark_users)


class ConversationEventListWalker(urwid.ListWalker):
    """ListWalker for ConversationEvents.

    The position may be an event ID or POSITION_LOADING.
    """

    POSITION_LOADING = 'loading'
    WATERMARK_FAST_SEARCH_ITEMS = 10

    def __init__(self, coroutine_queue, conversation, datetimefmt):
        self._coroutine_queue = coroutine_queue  # CoroutineQueue
        self._conversation = conversation  # Conversation
        self._is_scrolling = False  # Whether the user is trying to scroll up
        self._is_loading = False  # Whether we're currently loading more events
        self._first_loaded = False  # Whether the first event is loaded
        self._datetimefmt = datetimefmt
        self._watermarked_events = {}  # Users watermarked at a given event

        # Focus position is the first event ID, or POSITION_LOADING.
        self._focus_position = (conversation.events[-1].id_
                                if conversation.events
                                else self.POSITION_LOADING)

        self._conversation.on_event.add_observer(self._handle_event)
        self._conversation.on_watermark_notification.add_observer(
            self._on_watermark_notification
        )
        super().__init__()

    def _handle_event(self, conv_event):
        """Handle updating and scrolling when a new event is added.

        Automatically scroll down to show the new text if the bottom is
        showing. This allows the user to scroll up to read previous messages
        while new messages are arriving.
        """
        if not self._is_scrolling:
            self.set_focus(conv_event.id_)
        else:
            self._modified()

    async def _load(self):
        """Load more events for this conversation."""
        try:
            conv_events = await self._conversation.get_events(
                self._conversation.events[0].id_
            )
        except (IndexError, hangups.NetworkError):
            conv_events = []
        if not conv_events:
            self._first_loaded = True
        if self._focus_position == self.POSITION_LOADING and conv_events:
            # If the loading indicator is still focused, and we loaded more
            # events, set focus on the first new event so the loaded
            # indicator is replaced.
            self.set_focus(conv_events[-1].id_)
        else:
            # Otherwise, still need to invalidate in case the loading
            # indicator is showing but not focused.
            self._modified()
        # Loading events can also update the watermarks.
        self._refresh_watermarked_events()
        self._is_loading = False

    def __getitem__(self, position):
        """Return widget at position or raise IndexError."""
        if position == self.POSITION_LOADING:
            if self._first_loaded:
                # TODO: Show the full date the conversation was created.
                return urwid.Text('No more messages', align='center')
            else:
                # Don't try to load while we're already loading.
                if not self._is_loading and not self._first_loaded:
                    self._is_loading = True
                    self._coroutine_queue.put(self._load())
                return urwid.Text('Loading...', align='center')
        try:
            # When creating the widget, also pass the previous event so a
            # timestamp can be shown if this event occurred on a different day.
            # Get the previous event, or None if it isn't loaded or doesn't
            # exist.
            prev_position = self._get_position(position, prev=True)
            if prev_position == self.POSITION_LOADING:
                prev_event = None
            else:
                prev_event = self._conversation.get_event(prev_position)

            return MessageWidget.from_conversation_event(
                self._conversation, self._conversation.get_event(position),
                prev_event, self._datetimefmt,
                watermark_users=self._watermarked_events.get(position, None)
            )
        except KeyError:
            raise IndexError('Invalid position: {}'.format(position))

    @staticmethod
    def _find_watermark_event(timestamps, timestamp):
        # Look back through the most recent events first.
        back_idx = ConversationEventListWalker.WATERMARK_FAST_SEARCH_ITEMS
        for i, t in list(enumerate(reversed(timestamps[-back_idx:]))):
            if t <= timestamp:
                return len(timestamps) - i - 1

        # Bisect the rest.
        return bisect(timestamps[:-back_idx], timestamp) - 1

    def _refresh_watermarked_events(self):
        self._watermarked_events.clear()
        timestamps = [x.timestamp for x in self._conversation.events]
        for user_id in self._conversation.watermarks:
            user = self._conversation.get_user(user_id)
            # Ignore the current user.
            if user.is_self:
                continue
            # Skip searching if the watermark's event was not loaded yet.
            timestamp = self._conversation.watermarks[user_id]
            if timestamp < timestamps[0]:
                continue
            event_idx = ConversationEventListWalker._find_watermark_event(
                timestamps, timestamp
            )
            if event_idx >= 0:
                event_pos = self._conversation.events[event_idx].id_
                if event_pos not in self._watermarked_events:
                    self._watermarked_events[event_pos] = set()
                self._watermarked_events[event_pos].add(user)

    def _on_watermark_notification(self, _):
        """Update watermarks for this conversation."""
        self._refresh_watermarked_events()
        self._modified()

    def _get_position(self, position, prev=False):
        """Return the next/previous position or raise IndexError."""
        if position == self.POSITION_LOADING:
            if prev:
                raise IndexError('Reached last position')
            else:
                return self._conversation.events[0].id_
        else:
            ev = self._conversation.next_event(position, prev=prev)
            if ev is None:
                if prev:
                    return self.POSITION_LOADING
                else:
                    raise IndexError('Reached first position')
            else:
                return ev.id_

    def next_position(self, position):
        """Return the position below position or raise IndexError."""
        return self._get_position(position)

    def prev_position(self, position):
        """Return the position above position or raise IndexError."""
        return self._get_position(position, prev=True)

    def set_focus(self, position):
        """Set the focus to position or raise IndexError."""
        self._focus_position = position
        self._modified()
        # If we set focus to anywhere but the last position, the user if
        # scrolling up:
        try:
            self.next_position(position)
        except IndexError:
            self._is_scrolling = False
        else:
            self._is_scrolling = True

    def get_focus(self):
        """Return (widget, position) tuple."""
        return (self[self._focus_position], self._focus_position)


class ConversationWidget(WidgetBase):
    """Widget for interacting with a conversation."""

    def __init__(self, client, coroutine_queue, conversation, set_title_cb,
                 keybindings, datetimefmt, keep_emoticons):
        self._client = client
        self._coroutine_queue = coroutine_queue
        self._conversation = conversation
        self._conversation.on_event.add_observer(self._on_event)
        self._conversation.on_watermark_notification.add_observer(
            self._on_watermark_notification
        )
        self._keys = keybindings
        self._keep_emoticons = keep_emoticons

        self.title = ''
        self._set_title_cb = set_title_cb
        self._set_title()

        self._list_walker = ConversationEventListWalker(
            coroutine_queue, conversation, datetimefmt
        )
        self._list_box = ListBox(keybindings, self._list_walker)
        self._status_widget = StatusLineWidget(client, conversation)
        self._widget = urwid.Pile([
            ('weight', 1, self._list_box),
            ('pack', self._status_widget),
            ('pack', ReturnableEdit(self._on_return, keybindings,
                                    caption='Send message: ')),
        ])
        # focus the edit widget by default
        self._widget.focus_position = 2

        # Display any old ConversationEvents already attached to the
        # conversation.
        for event in self._conversation.events:
            self._on_event(event)

        super().__init__(self._widget)

    def get_menu_widget(self, close_callback):
        """Return the menu widget associated with this widget."""
        return ConversationMenu(
            self._coroutine_queue, self._conversation, close_callback,
            self._keys
        )

    def keypress(self, size, key):
        """Handle marking messages as read and keeping client active."""
        # Set the client as active.
        self._coroutine_queue.put(self._client.set_active())

        # Mark the newest event as read.
        self._coroutine_queue.put(self._conversation.update_read_timestamp())

        return super().keypress(size, key)

    def _set_title(self):
        """Update this conversation's tab title."""
        self.title = get_conv_name(self._conversation, show_unread=True,
                                   truncate=True)
        self._set_title_cb(self, self.title)

    def _on_return(self, text):
        """Called when the user presses return on the send message widget."""
        # Ignore if the user hasn't typed a message.
        if not text:
            return
        elif text.startswith('/image') and len(text.split(' ')) == 2:
            # Temporary UI for testing image uploads
            filename = text.split(' ')[1]
            try:
                image_file = open(filename, 'rb')
            except FileNotFoundError:
                message = 'Failed to find image {}'.format(filename)
                self._status_widget.show_message(message)
                return
            text = ''
        else:
            image_file = None
        if not self._keep_emoticons:
            text = replace_emoticons(text)
        segments = hangups.ChatMessageSegment.from_str(text)
        self._coroutine_queue.put(
            self._handle_send_message(
                self._conversation.send_message(
                    segments, image_file=image_file
                )
            )
        )

    async def _handle_send_message(self, coro):
        """Handle showing an error if a message fails to send."""
        try:
            await coro
        except hangups.NetworkError:
            self._status_widget.show_message('Failed to send message')

    def _on_watermark_notification(self, _):
        """Handle watermark changes for this conversation."""
        # Update the unread count in the title.
        self._set_title()

    def _on_event(self, _):
        """Display a new conversation message."""
        # Update the title in case unread count or conversation name changed.
        self._set_title()


class TabbedWindowWidget(WidgetBase):

    """A widget that displays a list of widgets via a tab bar."""

    def __init__(self, keybindings):
        self._widgets = []  # [urwid.Widget]
        self._widget_title = {}  # {urwid.Widget: str}
        self._tab_index = None  # int
        self._keys = keybindings
        self._tabs = urwid.Text('')
        self._frame = urwid.Frame(None)
        super().__init__(urwid.Pile([
            ('pack', urwid.AttrMap(self._tabs, 'tab_background')),
            ('weight', 1, self._frame),
        ]))

    def get_current_widget(self):
        """Return the widget in the current tab."""
        return self._widgets[self._tab_index]

    def _update_tabs(self):
        """Update tab display."""
        text = []
        for num, widget in enumerate(self._widgets):
            palette = ('active_tab' if num == self._tab_index
                       else 'inactive_tab')
            text += [
                (palette, ' {} '.format(self._widget_title[widget])),
                ('tab_background', ' '),
            ]
        self._tabs.set_text(text)
        self._frame.contents['body'] = (self._widgets[self._tab_index], None)

    def keypress(self, size, key):
        """Handle keypresses for changing tabs."""
        key = super().keypress(size, key)
        num_tabs = len(self._widgets)
        if key == self._keys['prev_tab']:
            self._tab_index = (self._tab_index - 1) % num_tabs
            self._update_tabs()
        elif key == self._keys['next_tab']:
            self._tab_index = (self._tab_index + 1) % num_tabs
            self._update_tabs()
        elif key == self._keys['close_tab']:
            # Don't allow closing the Conversations tab
            if self._tab_index > 0:
                curr_tab = self._widgets[self._tab_index]
                self._widgets.remove(curr_tab)
                del self._widget_title[curr_tab]
                self._tab_index -= 1
                self._update_tabs()
        else:
            return key

    def set_tab(self, widget, switch=False, title=None):
        """Add or modify a tab.

        If widget is not a tab, it will be added. If switch is True, switch to
        this tab. If title is given, set the tab's title.
        """
        if widget not in self._widgets:
            self._widgets.append(widget)
            self._widget_title[widget] = ''
        if switch:
            self._tab_index = self._widgets.index(widget)
        if title:
            self._widget_title[widget] = title
        self._update_tabs()


def set_terminal_title(title):
    """Use an xterm escape sequence to set the terminal title."""
    sys.stdout.write("\x1b]2;{}\x07".format(title))


@contextlib.contextmanager
def bracketed_paste_mode():
    """Context manager for enabling/disabling bracketed paste mode."""
    sys.stdout.write('\x1b[?2004h')
    try:
        yield
    finally:
        sys.stdout.write('\x1b[?2004l')


def dir_maker(path):
    """Create a directory if it does not exist."""
    directory = os.path.dirname(path)
    if directory != '' and not os.path.isdir(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            sys.exit('Failed to create directory: {}'.format(e))


NOTIFIER_TYPES = {
    'none': notifier.Notifier,
    'default': notifier.DefaultNotifier,
    'bell': notifier.BellNotifier,
    'dbus': notifier.DbusNotifier,
    'apple': notifier.AppleNotifier,
}


def get_notifier(notification_type, disable_notifications):
    if disable_notifications:
        return notifier.Notifier()
    else:
        return NOTIFIER_TYPES[notification_type]()


def main():
    """Main entry point."""
    # Build default paths for files.
    dirs = appdirs.AppDirs('hangups', 'hangups')
    default_log_path = os.path.join(dirs.user_log_dir, 'hangups.log')
    default_token_path = os.path.join(dirs.user_cache_dir, 'refresh_token.txt')
    default_config_path = 'hangups.conf'
    user_config_path = os.path.join(dirs.user_config_dir, 'hangups.conf')

    # Create a default empty config file if does not exist.
    dir_maker(user_config_path)
    if not os.path.isfile(user_config_path):
        with open(user_config_path, 'a') as cfg:
            cfg.write("")

    parser = configargparse.ArgumentParser(
        prog='hangups', default_config_files=[default_config_path,
                                              user_config_path],
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        add_help=False,  # Disable help so we can add it to the correct group.
    )
    general_group = parser.add_argument_group('General')
    general_group.add('-h', '--help', action='help',
                      help='show this help message and exit')
    general_group.add('--token-path', default=default_token_path,
                      help='path used to store OAuth refresh token')
    general_group.add('--date-format', default='< %y-%m-%d >',
                      help='date format string')
    general_group.add('--time-format', default='(%I:%M:%S %p)',
                      help='time format string')
    general_group.add('-c', '--config', help='configuration file path',
                      is_config_file=True, default=user_config_path)
    general_group.add('-v', '--version', action='version',
                      version='hangups {}'.format(hangups.__version__))
    general_group.add('-d', '--debug', action='store_true',
                      help='log detailed debugging messages')
    general_group.add('--manual-login', action='store_true',
                      help='enable manual login method')
    general_group.add('--log', default=default_log_path, help='log file path')
    general_group.add('--keep-emoticons', action='store_true',
                      help='do not replace emoticons with corresponding emoji')
    key_group = parser.add_argument_group('Keybindings')
    key_group.add('--key-next-tab', default='ctrl d',
                  help='keybinding for next tab')
    key_group.add('--key-prev-tab', default='ctrl u',
                  help='keybinding for previous tab')
    key_group.add('--key-close-tab', default='ctrl w',
                  help='keybinding for close tab')
    key_group.add('--key-quit', default='ctrl e',
                  help='keybinding for quitting')
    key_group.add('--key-menu', default='ctrl n',
                  help='keybinding for context menu')
    key_group.add('--key-up', default='k',
                  help='keybinding for alternate up key')
    key_group.add('--key-down', default='j',
                  help='keybinding for alternate down key')
    key_group.add('--key-page-up', default='ctrl b',
                  help='keybinding for alternate page up')
    key_group.add('--key-page-down', default='ctrl f',
                  help='keybinding for alternate page down')
    notification_group = parser.add_argument_group('Notifications')
    # deprecated in favor of --notification-type=none:
    notification_group.add('-n', '--disable-notifications',
                           action='store_true',
                           help=configargparse.SUPPRESS)
    notification_group.add('-D', '--discreet-notifications',
                           action='store_true',
                           help='hide message details in notifications')
    notification_group.add('--notification-type',
                           choices=sorted(NOTIFIER_TYPES.keys()),
                           default='default',
                           help='type of notifications to create')

    # add color scheme options
    col_group = parser.add_argument_group('Colors')
    col_group.add('--col-scheme', choices=COL_SCHEMES.keys(),
                  default='default', help='colour scheme to use')
    col_group.add('--col-palette-colors', choices=('16', '88', '256'),
                  default=16, help='Amount of available colors')
    for name in COL_SCHEME_NAMES:
        col_group.add('--col-' + name.replace('_', '-') + '-fg',
                      help=name + ' foreground color')
        col_group.add('--col-' + name.replace('_', '-') + '-bg',
                      help=name + ' background color')

    args = parser.parse_args()

    # Create all necessary directories.
    for path in [args.log, args.token_path]:
        dir_maker(path)

    logging.basicConfig(filename=args.log,
                        level=logging.DEBUG if args.debug else logging.WARNING,
                        format=LOG_FORMAT)
    # urwid makes asyncio's debugging logs VERY noisy, so adjust the log level:
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    datetimefmt = {'date': args.date_format,
                   'time': args.time_format}

    # setup color scheme
    palette_colors = int(args.col_palette_colors)

    col_scheme = COL_SCHEMES[args.col_scheme]
    for name in COL_SCHEME_NAMES:
        col_scheme = add_color_to_scheme(col_scheme, name,
                                         getattr(args, 'col_' + name + '_fg'),
                                         getattr(args, 'col_' + name + '_bg'),
                                         palette_colors)

    keybindings = {
        'next_tab': args.key_next_tab,
        'prev_tab': args.key_prev_tab,
        'close_tab': args.key_close_tab,
        'quit': args.key_quit,
        'menu': args.key_menu,
        'up': args.key_up,
        'down': args.key_down,
        'page_up': args.key_page_up,
        'page_down': args.key_page_down,
    }

    notifier_ = get_notifier(
        args.notification_type, args.disable_notifications
    )

    try:
        ChatUI(
            args.token_path, keybindings, col_scheme, palette_colors,
            datetimefmt, notifier_, args.discreet_notifications,
            args.manual_login, args.keep_emoticons
        )
    except KeyboardInterrupt:
        sys.exit('Caught KeyboardInterrupt, exiting abnormally')


if __name__ == '__main__':
    main()
