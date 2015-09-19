"""Reference chat client for hangups."""

import appdirs
import asyncio
import configargparse
import logging
import os
import sys
import urwid
import readlike

import hangups
from hangups.ui.notify import Notifier
from hangups.ui.utils import get_conv_name


LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
MESSAGE_TIME_FORMAT = '(%I:%M:%S %p)'
MESSAGE_DATETIME_FORMAT = '\n< %y-%m-%d >\n(%I:%M:%S %p)'
COL_SCHEMES = {
    # Very basic scheme with no colour
    'default': {
        ('active_tab', '', ''),
        ('inactive_tab', 'standout', ''),
        ('msg_date', '', ''),
        ('msg_sender', '', ''),
        ('msg_text', '', ''),
        ('status_line', 'standout', ''),
        ('tab_background', 'standout', ''),
    },
    'solarized-dark': {
        ('active_tab', 'light gray', 'light blue'),
        ('inactive_tab', 'underline', 'light green'),
        ('msg_date', 'dark cyan', ''),
        ('msg_sender', 'dark blue', ''),
        ('msg_text', '', ''),
        ('status_line', 'standout', ''),
        ('tab_background', 'underline', 'black'),
    },
}


class ChatUI(object):
    """User interface for hangups."""

    def __init__(self, refresh_token_path, keybindings, palette,
                 disable_notifier):
        """Start the user interface."""
        self._keys = keybindings

        set_terminal_title('hangups')

        # These are populated by on_connect when it's called.
        self._conv_widgets = {}  # {conversation_id: ConversationWidget}
        self._tabbed_window = None  # TabbedWindowWidget
        self._conv_list = None  # hangups.ConversationList
        self._user_list = None  # hangups.UserList
        self._notifier = None  # hangups.notify.Notifier
        self._disable_notifier = disable_notifier

        # TODO Add urwid widget for getting auth.
        try:
            cookies = hangups.auth.get_auth_stdin(refresh_token_path)
        except hangups.GoogleAuthError as e:
            sys.exit('Login failed ({})'.format(e))

        self._client = hangups.Client(cookies)
        self._client.on_connect.add_observer(self._on_connect)

        loop = asyncio.get_event_loop()
        self._urwid_loop = urwid.MainLoop(
            LoadingWidget(), palette, handle_mouse=False,
            input_filter=self._input_filter,
            event_loop=urwid.AsyncioEventLoop(loop=loop)
        )

        self._urwid_loop.start()
        try:
            # Returns when the connection is closed.
            loop.run_until_complete(self._client.connect())
        finally:
            # Ensure urwid cleans up properly and doesn't wreck the terminal.
            self._urwid_loop.stop()
            loop.close()

    def _input_filter(self, keys, _):
        """Handle global keybindings."""
        if keys == [self._keys['menu']]:
            if self._urwid_loop.widget == self._tabbed_window:
                self._show_menu()
            else:
                self._hide_menu()
        elif keys == [self._keys['quit']]:
            self._on_quit()
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
            widget = ConversationWidget(self._client,
                                        self._conv_list.get(conv_id),
                                        set_title_cb,
                                        self._keys)
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

    @asyncio.coroutine
    def _on_connect(self):
        """Handle connecting for the first time."""
        self._user_list, self._conv_list = (
            yield from hangups.build_user_conversation_list(self._client)
        )
        self._conv_list.on_event.add_observer(self._on_event)
        if not self._disable_notifier:
            self._notifier = Notifier(self._conv_list)
        # show the conversation menu
        conv_picker = ConversationPickerWidget(self._conv_list,
                                               self.on_select_conversation,
                                               self._keys)
        self._tabbed_window = TabbedWindowWidget(self._keys)
        self._tabbed_window.set_tab(conv_picker, switch=True,
                                    title='Conversations')
        self._urwid_loop.widget = self._tabbed_window

    def _on_event(self, conv_event):
        """Open conversation tab for new messages when they arrive."""
        conv = self._conv_list.get(conv_event.conversation_id)
        user = conv.get_user(conv_event.user_id)
        add_tab = all((
            isinstance(conv_event, hangups.ChatMessageEvent),
            not user.is_self,
            not conv.is_quiet,
        ))
        if add_tab:
            self.add_conversation_tab(conv_event.conversation_id)

    def _on_quit(self):
        """Handle the user quitting the application."""
        future = asyncio.async(self._client.disconnect())
        future.add_done_callback(lambda future: future.result())


class LoadingWidget(urwid.WidgetWrap):
    """Widget that shows a loading indicator."""

    def __init__(self):
        # show message in the center of the screen
        super().__init__(urwid.Filler(
            urwid.Text('Connecting...', align='center')
        ))


class RenameConversationDialog(urwid.WidgetWrap):
    """Dialog widget for renaming a conversation."""

    def __init__(self, conversation, on_cancel, on_save):
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
        list_box = urwid.ListBox(list_walker)
        super().__init__(list_box)

    def _rename(self, name, callback):
        """Rename conversation and call callback."""
        future = asyncio.async(self._conversation.rename(name))
        future.add_done_callback(lambda future: future.result())
        callback()


class ConversationMenu(urwid.WidgetWrap):
    """Menu for conversation actions."""

    def __init__(self, conversation, close_callback, keybindings):
        rename_dialog = RenameConversationDialog(
            conversation,
            lambda: frame.contents.__setitem__('body', (list_box, None)),
            close_callback
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
        list_box = urwid.ListBox(list_walker)
        frame = urwid.Frame(list_box)
        padding = urwid.Padding(frame, left=1, right=1)
        line_box = urwid.LineBox(padding, title='Conversation Menu')
        super().__init__(line_box)
        self._keys = keybindings

    def keypress(self, size, key):
        # Handle alternate up/down keybindings
        key = super().keypress(size, key)
        if key == self._keys['down']:
            super().keypress(size, 'down')
        elif key == self._keys['up']:
            super().keypress(size, 'up')
        else:
            return key


class ConversationButton(urwid.WidgetWrap):
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


class ConversationPickerWidget(urwid.WidgetWrap):
    """ListBox widget for picking a conversation from a list."""

    def __init__(self, conversation_list, on_select, keybindings):
        list_walker = ConversationListWalker(conversation_list, on_select)
        list_box = urwid.ListBox(list_walker)
        widget = urwid.Padding(list_box, left=2, right=2)
        super().__init__(widget)
        self._keys = keybindings

    def keypress(self, size, key):
        # Handle alternate up/down keybindings
        key = super().keypress(size, key)
        if key == self._keys['down']:
            super().keypress(size, 'down')
        elif key == self._keys['up']:
            super().keypress(size, 'up')
        else:
            return key


class ReturnableEdit(urwid.Edit):
    """Edit widget that clears itself and calls a function on return."""

    def __init__(self, on_return, keybindings, caption=None):
        super().__init__(caption=caption)
        self._on_return = on_return
        self._keys = keybindings

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == 'enter':
            self._on_return(self.get_edit_text())
            self.set_edit_text('')
        elif key not in self._keys.values() and key in readlike.keys():
            text, pos = readlike.edit(self.edit_text, self.edit_pos, key)
            self.set_edit_text(text)
            self.set_edit_pos(pos)
        else:
            return key


class StatusLineWidget(urwid.WidgetWrap):
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
        super().__init__(urwid.AttrWrap(self._widget, 'status_line'))

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
        typers = [self._conversation.get_user(user_id).first_name
                  for user_id, status in self._typing_statuses.items()
                  if status == hangups.TYPING_TYPE_STARTED]
        if len(typers) > 0:
            typing_message = '{} {} typing...'.format(
                ', '.join(sorted(typers)),
                'is' if len(typers) == 1 else 'are'
            )
        else:
            typing_message = ''

        if not self._is_connected:
            self._widget.set_text("RECONNECTING...")
        elif self._message is not None:
            self._widget.set_text(self._message)
        else:
            self._widget.set_text(typing_message)


class MessageWidget(urwid.WidgetWrap):

    """Widget for displaying a single message in a conversation."""

    def __init__(self, timestamp, text, user=None, show_date=False):
        # Save the timestamp as an attribute for sorting.
        self.timestamp = timestamp
        text = [
            ('msg_date', self._get_date_str(timestamp,
                                            show_date=show_date) + ' '),
            ('msg_text', text)
        ]
        if user is not None:
            text.insert(1, ('msg_sender', user.first_name + ': '))
        self._widget = urwid.Text(text)
        super().__init__(self._widget)

    @staticmethod
    def _get_date_str(timestamp, show_date=False):
        """Convert UTC datetime into user interface string."""
        fmt = MESSAGE_DATETIME_FORMAT if show_date else MESSAGE_TIME_FORMAT
        return timestamp.astimezone(tz=None).strftime(fmt)

    def __lt__(self, other):
        return self.timestamp < other.timestamp

    @staticmethod
    def from_conversation_event(conversation, conv_event, prev_conv_event):
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
            return MessageWidget(conv_event.timestamp, conv_event.text, user,
                                 show_date=is_new_day)
        elif isinstance(conv_event, hangups.RenameEvent):
            if conv_event.new_name == '':
                text = ('{} cleared the conversation name'
                        .format(user.first_name))
            else:
                text = ('{} renamed the conversation to {}'
                        .format(user.first_name, conv_event.new_name))
            return MessageWidget(conv_event.timestamp, text,
                                 show_date=is_new_day)
        elif isinstance(conv_event, hangups.MembershipChangeEvent):
            event_users = [conversation.get_user(user_id) for user_id
                           in conv_event.participant_ids]
            names = ', '.join([user.full_name for user in event_users])
            if conv_event.type_ == hangups.MEMBERSHIP_CHANGE_TYPE_JOIN:
                text = ('{} added {} to the conversation'
                        .format(user.first_name, names))
            else:  # LEAVE
                text = ('{} left the conversation'.format(names))
            return MessageWidget(conv_event.timestamp, text,
                                 show_date=is_new_day)
        else:
            return None


class ConversationEventListWalker(urwid.ListWalker):
    """ListWalker for ConversationEvents.

    The position may be an event ID, POSITION_LOADING, or None.
    """

    POSITION_LOADING = 'loading'

    def __init__(self, conversation):
        self._conversation = conversation  # Conversation
        self._is_scrolling = False  # Whether the user is trying to scroll up
        self._is_loading = False  # Whether we're currently loading more events
        self._first_loaded = False  # Whether the first event is loaded

        # Focus position is the first displayable event ID, or None.
        self._focus_position = next((
            ev.id_ for ev in reversed(conversation.events)
            if self._is_event_displayable(ev)
        ), None)

        self._conversation.on_event.add_observer(self._handle_event)

    def _is_event_displayable(self, conv_event):
        """Return True if the ConversationWidget is displayable."""
        widget = MessageWidget.from_conversation_event(self._conversation,
                                                       conv_event, None)
        return widget is not None

    def _handle_event(self, conv_event):
        """Handle updating and scrolling when a new event is added.

        Automatically scroll down to show the new text if the bottom is
        showing. This allows the user to scroll up to read previous messages
        while new messages are arriving.
        """
        if not self._is_scrolling:
            try:
                _ = self[conv_event.id_]  # Check that it has a widget.
                pos = conv_event.id_
            except IndexError:
                pass  # New event might not have a widget.
            else:
                self.set_focus(pos)
        else:
            self._modified()

    @asyncio.coroutine
    def _load(self):
        """Load more events for this conversation."""
        # Don't try to load while we're already loading.
        if not self._is_loading and not self._first_loaded:
            self._is_loading = True
            try:
                conv_events = yield from self._conversation.get_events(
                    self._conversation.events[0].id_
                )
            except (IndexError, hangups.NetworkError):
                conv_events = []
            if len(conv_events) == 0:
                self._first_loaded = True
            if (self._focus_position == self.POSITION_LOADING and
                    len(conv_events) > 0):
                # If the loading indicator is still focused, and we loaded more
                # events, set focus on the first new event so the loaded
                # indicator is replaced.
                self.set_focus(conv_events[-1].id_)
            else:
                # Otherwise, still need to invalidate in case the loading
                # indicator is showing but not focused.
                self._modified()
            self._is_loading = False

    def __getitem__(self, position):
        """Return widget at position or raise IndexError."""
        if position == self.POSITION_LOADING:
            if self._first_loaded:
                # TODO: Show the full date the conversation was created.
                return urwid.Text('No more messages', align='center')
            future = asyncio.async(self._load())
            future.add_done_callback(lambda future: future.result())
            return urwid.Text('Loading...', align='center')
        # May return None if the event doesn't have a widget representation.
        try:
            # Get the previous displayable event, or None if it isn't loaded or
            # doesn't exist.
            prev_position = self._get_position(position, prev=True)
            if prev_position == self.POSITION_LOADING:
                prev_event = None
            else:
                prev_event = self._conversation.get_event(prev_position)

            # When creating the widget, also pass the previous event so a
            # timestamp can be shown if this event occurred on a different day.
            widget = MessageWidget.from_conversation_event(
                self._conversation, self._conversation.get_event(position),
                prev_event
            )
        except KeyError:
            raise IndexError('Invalid position: {}'.format(position))
        if not widget:
            raise IndexError('Invalid position: {}'.format(position))
        return widget

    def _get_position(self, position, prev=False):
        """Return the next/previous position or raise IndexError."""
        if position == self.POSITION_LOADING:
            if prev:
                raise IndexError('Reached last position')
            else:
                return self._conversation.events[0].id_
        while True:
            ev = self._conversation.next_event(position, prev=prev)
            if ev is None:
                if prev:
                    return self.POSITION_LOADING
                else:
                    raise IndexError('Reached first position')
            # Skip events that aren't represented by a widget and try the next
            # one.
            if self._is_event_displayable(ev):
                return ev.id_
            else:
                position = ev.id_

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
        """Return (widget, position) tuple or (None, None) if empty."""
        if len(self._conversation.events) > 0:
            return (self[self._focus_position], self._focus_position)
        else:
            return (None, None)


class ConversationWidget(urwid.WidgetWrap):
    """Widget for interacting with a conversation."""

    def __init__(self, client, conversation, set_title_cb, keybindings):
        self._client = client
        self._conversation = conversation
        self._conversation.on_event.add_observer(self._on_event)
        self._conversation.on_watermark_notification.add_observer(
            self._on_watermark_notification
        )
        self._keys = keybindings

        self.title = ''
        self._set_title_cb = set_title_cb
        self._set_title()

        self._list_walker = ConversationEventListWalker(conversation)
        self._list_box = urwid.ListBox(self._list_walker)
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
        return ConversationMenu(self._conversation, close_callback, self._keys)

    def keypress(self, size, key):
        """Handle marking messages as read and keeping client active."""
        # Set the client as active.
        future = asyncio.async(self._client.set_active())
        future.add_done_callback(lambda future: future.result())

        # Mark the newest event as read.
        future = asyncio.async(self._conversation.update_read_timestamp())
        future.add_done_callback(lambda future: future.result())

        return super().keypress(size, key)

    def _set_title(self):
        """Update this conversation's tab title."""
        self.title = get_conv_name(self._conversation, show_unread=True,
                                   truncate=True)
        self._set_title_cb(self, self.title)

    def _on_return(self, text):
        """Called when the user presses return on the send message widget."""
        # Ignore if the user hasn't typed a message.
        if len(text) == 0:
            return
        elif text.startswith('/image') and len(text.split(' ')) == 2:
            # Temporary UI for testing image uploads
            filename = text.split(' ')[1]
            image_file = open(filename, 'rb')
            text = ''
        else:
            image_file = None
        # XXX: Exception handling here is still a bit broken. Uncaught
        # exceptions in _on_message_sent will only be logged.
        segments = hangups.ChatMessageSegment.from_str(text)
        asyncio.async(
            self._conversation.send_message(segments, image_file=image_file)
        ).add_done_callback(self._on_message_sent)

    def _on_message_sent(self, future):
        """Handle showing an error if a message fails to send."""
        try:
            future.result()
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


class TabbedWindowWidget(urwid.WidgetWrap):

    """A widget that displays a list of widgets via a tab bar."""

    def __init__(self, keybindings):
        self._widgets = []  # [urwid.Widget]
        self._widget_title = {}  # {urwid.Widget: str}
        self._tab_index = None  # int
        self._keys = keybindings
        self._tabs = urwid.Text('')
        self._frame = urwid.Frame(None)
        super().__init__(urwid.Pile([
            ('pack', urwid.AttrWrap(self._tabs, 'tab_background')),
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
                (palette, ' {} '.format(self._widget_title[widget]).encode()),
                ('tab_background', b' '),
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


def dir_maker(path):
    """Create a directory if it does not exist."""
    directory = os.path.dirname(path)
    if directory != '' and not os.path.isdir(directory):
        try:
            os.makedirs(directory)
        except OSError as e:
            sys.exit('Failed to create directory: {}'.format(e))


def main():
    """Main entry point."""
    # Build default paths for files.
    dirs = appdirs.AppDirs('hangups', 'hangups')
    default_log_path = os.path.join(dirs.user_log_dir, 'hangups.log')
    default_token_path = os.path.join(dirs.user_cache_dir, 'refresh_token.txt')
    default_config_path = os.path.join(dirs.user_config_dir, 'hangups.conf')

    # Create a default empty config file if does not exist.
    dir_maker(default_config_path)
    if not os.path.isfile(default_config_path):
        with open(default_config_path, 'a') as cfg:
            cfg.write("")

    parser = configargparse.ArgumentParser(
        prog='hangups', default_config_files=[default_config_path],
        formatter_class=configargparse.ArgumentDefaultsHelpFormatter,
        add_help=False,  # Disable help so we can add it to the correct group.
    )
    general_group = parser.add_argument_group('General')
    general_group.add('-h', '--help', action='help',
                      help='show this help message and exit')
    general_group.add('--token-path', default=default_token_path,
                      help='path used to store OAuth refresh token')
    general_group.add('--col-scheme', choices=COL_SCHEMES.keys(),
                      default='default', help='colour scheme to use')
    general_group.add('-c', '--config', help='configuration file path',
                      is_config_file=True, default=default_config_path)
    general_group.add('-v', '--version', action='version',
                      version='hangups {}'.format(hangups.__version__))
    general_group.add('-d', '--debug', action='store_true',
                      help='log detailed debugging messages')
    general_group.add('-n', '--disable-notifications', action='store_true',
                      help='disable desktop notifications')
    general_group.add('--log', default=default_log_path, help='log file path')
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
    args = parser.parse_args()

    # Create all necessary directories.
    for path in [args.log, args.token_path]:
        dir_maker(path)

    log_level = logging.DEBUG if args.debug else logging.WARNING
    logging.basicConfig(filename=args.log, level=log_level, format=LOG_FORMAT)
    # urwid makes asyncio's debugging logs VERY noisy, so adjust the log level:
    logging.getLogger('asyncio').setLevel(logging.WARNING)

    try:
        ChatUI(args.token_path, {
            'next_tab': args.key_next_tab,
            'prev_tab': args.key_prev_tab,
            'close_tab': args.key_close_tab,
            'quit': args.key_quit,
            'menu': args.key_menu,
            'up': args.key_up,
            'down': args.key_down
        }, COL_SCHEMES[args.col_scheme], args.disable_notifications)
    except KeyboardInterrupt:
        sys.exit('Caught KeyboardInterrupt, exiting abnormally')
    except:
        # urwid will prevent some exceptions from being printed unless we use
        # print a newline first.
        print('')
        raise


if __name__ == '__main__':
    main()
