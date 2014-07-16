"""Demo chat client using Hangups."""

# "unused argument" are unavoidable because of obsub events.
# pylint: disable=W0613

from math import floor, ceil
from tornado import ioloop
import logging
import sys
import urwid

import hangups
from hangups.notify import Notifier


LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
URWID_PALETTE = [
    # ConversationWidget
    ('msg_date', 'dark blue', 'default'),
    ('msg_sender', 'dark blue', 'default'),
    ('msg_text', '', 'default'),
    # TabBarWidget
    ('active_tab', 'light gray', 'light blue'),
    ('inactive_tab', 'underline', 'light green'),
    ('tab_background', 'underline', 'black'),
    ('status_line', '', 'black'),
]


class ChatUI(object):
    """User interface for hangups."""

    def __init__(self):
        """Start the user interface."""
        # These are populated by on_connect when it's called.
        self._conv_widgets = {} # {conversation_id: ConversationWidget}
        self._tabbed_window = None # TabbedWindowWidget
        self._conv_list = None # hangups.ConversationList
        self._user_list = None # hangups.UserList
        self._notifier = None # hangups.notify.Notifier

        # TODO Add urwid widget for getting auth.
        try:
            cookies = hangups.auth.get_auth_stdin('cookies.json')
        except hangups.GoogleAuthError as e:
            print('Login failed ({})'.format(e))
            sys.exit(1)

        self._client = hangups.Client(cookies)
        self._client.on_connect += self._on_connect
        self._client.on_disconnect += self._on_disconnect
        self._client.on_message += self._on_message

        class MyEventLoop(urwid.TornadoEventLoop):
            """Patched Tornado event loop for urwid.

            Patch urwid's TornadoEventLoop to run_sync() our connection
            coroutine rather than calling start(). This "fixes" exception
            handling, causing all uncaught exceptions to be fatal.
            """
            _client = self._client
            def run(self):
                try:
                    ioloop.IOLoop.instance().run_sync(self._client.connect)
                except ioloop.TimeoutError:
                    # Ignore spurious timeout when there's another exception.
                    pass
                # Raise exception if there was one.
                if self._exception:
                    exc, self._exception = self._exception, None
                    raise exc # pylint: disable=E0702

        # Initialize urwid, starting the IOLoop, and block until the IOLoop
        # exits.
        self._urwid_loop = urwid.MainLoop(LoadingWidget(), URWID_PALETTE,
                                          event_loop=MyEventLoop(),
                                          handle_mouse=False)
        self._urwid_loop.run()

    def get_conv_widget(self, conv_id):
        """Return an existing or new ConversationWidget."""
        if conv_id not in self._conv_widgets:
            widget = ConversationWidget(self._conv_list.get(conv_id))
            self._conv_widgets[conv_id] = widget
        return self._conv_widgets[conv_id]

    def add_conversation_tab(self, conv_id, switch=False):
        """Add conversation tab if not present, and optionally switch to it."""
        conv_widget = self.get_conv_widget(conv_id)
        try:
            index = self._tabbed_window.index(conv_widget)
        except ValueError:
            index = self._tabbed_window.add_tab(conv_widget)
        if switch:
            self._tabbed_window.change_tab(index)

    def on_select_conversation(self, conv_id):
        """Called when the user selects a new conversation to listen to."""
        # switch to new or existing tab for the conversation
        self.add_conversation_tab(conv_id, switch=True)

    def _on_connect(self, client):
        """Handle connecting for the first time."""
        self._conv_list = hangups.ConversationList(self._client)
        self._user_list = hangups.UserList(self._client)
        self._notifier = Notifier(self._client, self._conv_list)
        # show the conversation menu
        self._tabbed_window = TabbedWindowWidget([
            ConversationPickerWidget(
                self._conv_list, self.on_select_conversation
            )
        ])
        self._urwid_loop.widget = self._tabbed_window

    def _on_message(self, client, conv_id, user_id, timestamp, text):
        """Open conversation tab for new messages when they arrive."""
        self.add_conversation_tab(conv_id)

    def _on_disconnect(self, client):
        """Handle disconnecting."""
        # TODO: handle this
        print('Connection lost')


def get_conv_name(conv, truncate=False):
    """Return the readable name for a conversation.

    For one-to-one conversations, the name is the full name of the other user.
    For group conversations, the name is a comma-separated list of first names.

    If truncate is true, only show up to two names in a group conversation.
    """
    participants = sorted(user for user in conv.users if not user.is_self)
    names = [user.first_name for user in participants]
    if len(participants) == 1:
        return participants[0].full_name
    elif truncate and len(participants) > 2:
        return ', '.join(names[:2] + ['+{}'.format(len(names) - 2)])
    else:
        return ', '.join(names)


class LoadingWidget(urwid.WidgetWrap):
    """Widget that shows a loading indicator."""

    def __init__(self):
        # show message in the center of the screen
        super().__init__(urwid.Filler(
            urwid.Text('Connecting...', align='center')
        ))


class ConversationPickerWidget(urwid.WidgetWrap):
    """Widget for picking a conversation."""

    def __init__(self, conversation_list, on_select):
        self.tab_title = 'Conversations'
        # Build buttons for selecting conversations ordered by most recently
        # modified first.
        convs = sorted(conversation_list.get_all(), reverse=True,
                       key=lambda c: c.last_modified)
        on_press = lambda button, conv_id: on_select(conv_id)
        buttons = [urwid.Button(get_conv_name(conv), on_press=on_press,
                                user_data=conv.id_)
                   for conv in convs]
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))
        widget = urwid.Padding(listbox, left=2, right=2)
        super().__init__(widget)


class ReturnableEdit(urwid.Edit):
    """Edit widget that clears itself and calls a function on return."""

    def __init__(self, on_return, caption=None):
        super().__init__(caption=caption)
        self._on_return = on_return

    def keypress(self, size, key):
        key = super().keypress(size, key)
        if key == 'enter':
            self._on_return(self.get_edit_text())
            self.set_edit_text('')
        else:
            return key


class StatusLineWidget(urwid.WidgetWrap):
    """Widget for showing typing status."""

    def __init__(self, conversation):
        self._widget = urwid.Text('')
        self._typing_statuses = {}
        self._conversation = conversation
        self._conversation.on_message += self._on_message
        self._conversation.on_typing += self._on_typing
        super().__init__(self._widget)

    def render(self, size, focus=False):
        # custom render function to change background colour
        msg = self._widget.text
        msg = msg if isinstance(msg, bytes) else msg.encode()
        num_padding = (size[0] - len(msg))
        # center the text by putting padding on each side
        padding_left = b' ' * floor(num_padding / 2)
        padding_right = b' ' * ceil(num_padding / 2)
        text = ('status_line', padding_left + msg + padding_right)
        self._widget.set_text(text)
        return super().render(size, focus)

    def _on_message(self, conversation, user_id, timestamp, text):
        """Make users stop typing when they send a message."""
        self._typing_statuses[user_id] = 'stopped'
        self._update()

    def _on_typing(self, conversation, user_id, timestamp, status):
        """Handle typing updates."""
        self._typing_statuses[user_id] = status
        self._update()

    def _update(self):
        """Update list of typers."""
        typers = [self._conversation.get_user(user_id).first_name
                  for user_id, status in self._typing_statuses.items()
                  if status == 'typing']
        if len(typers) > 0:
            msg = '{} {} typing...'.format(
                ', '.join(sorted(typers)),
                'is' if len(typers) == 1 else 'are'
            )
        else:
            msg = ''
        self._widget.set_text(msg)


class ConversationWidget(urwid.WidgetWrap):
    """Widget for interacting with a conversation."""

    def __init__(self, conversation):
        self._conversation = conversation
        self._conversation.on_message += self._on_message

        self.tab_title = get_conv_name(conversation, truncate=True)

        self._list_walker = urwid.SimpleFocusListWalker([])
        self._list_box = urwid.ListBox(self._list_walker)
        self._status_widget = StatusLineWidget(conversation)
        self._widget = urwid.Pile([
            ('weight', 1, self._list_box),
            ('pack', self._status_widget),
            ('pack', ReturnableEdit(self._on_return, caption='Send message: ')),
        ])
        # focus the edit widget by default
        self._widget.focus_position = 2
        super().__init__(self._widget)

    def _on_return(self, text):
        """Called when the user presses return on the send message widget."""
        on_sent = lambda f: f.result()
        self._conversation.send_message(text).add_done_callback(on_sent)

    def _on_message(self, conversation, user_id, timestamp, text):
        """Display a new conversation message."""
        # format the message and add it to the list box
        date_str = timestamp.astimezone().strftime('%I:%M:%S %p')
        name = self._conversation.get_user(user_id).first_name
        self._list_walker.append(urwid.Text([
            ('msg_date', '(' + date_str + ') '),
            ('msg_sender', name + ': '),
            ('msg_text', text)
        ]))

        # scroll down to the new message
        self._list_box.set_focus(len(self._list_walker) - 1)


class TabBarWidget(urwid.WidgetWrap):
    """A horizontal tab bar for switching between a list of items.

    Every item is assumed to have a tab_title property which is used as the
    title for the item's tab.
    """

    def __init__(self, items):
        self._widget = urwid.Text('')
        self._items = items
        self._selected_index = 0
        super().__init__(self._widget)

    def render(self, size, focus=False):
        # TODO: handle overflow
        max_col = size[0]
        text = []
        for num, item in enumerate(self._items):
            palette = ('active_tab' if num == self._selected_index
                       else 'inactive_tab')
            text += [
                (palette, ' {} '.format(item.tab_title).encode()),
                ('tab_background', b' '),
            ]
        text_len = sum(len(t) for a, t in text)
        text.append(('tab_background', b' ' * (max_col - text_len)))
        self._widget.set_text(text)
        return super().render(size, focus)

    def change_tab(self, index):
        """Change to the tab at the given index."""
        self._selected_index = index
        self._invalidate()

    def get_selected_item(self):
        """Return the selected item."""
        return self._items[self._selected_index]

    def get_selected_index(self):
        """Return the index of the selected tab."""
        return self._selected_index

    def get_num_tabs(self):
        """Return the number of tabs."""
        return len(self._items)


class TabbedWindowWidget(urwid.WidgetWrap):
    """A tabbed-window widget for displaying other widgets under a tab bar.

    Every widget is assumed to have a tab_title property which is used as the
    widget's title in the tab bar.
    """

    def __init__(self, widget_list):
        self._window_widget_list = widget_list
        self._frame = urwid.Frame(widget_list[0])
        self._tab_widget = TabBarWidget(widget_list)
        self._widget = urwid.Pile([
            ('pack', self._tab_widget),
            ('weight', 1, self._frame),
        ])
        super().__init__(self._widget)

    def keypress(self, size, key):
        """Handle keypresses for changing tabs."""
        key = super().keypress(size, key)
        # TODO: add a way to close tabs
        if key == 'ctrl u':
            self.change_tab((self._tab_widget.get_selected_index() -
                             1) % self._tab_widget.get_num_tabs())
        elif key == 'ctrl d':
            self.change_tab((self._tab_widget.get_selected_index() +
                             1) % self._tab_widget.get_num_tabs())
        else:
            return key

    def add_tab(self, widget):
        """Add a new tab and return its index."""
        self._window_widget_list.append(widget)
        self._tab_widget._invalidate()
        return self._tab_widget.get_num_tabs() - 1

    def change_tab(self, index):
        """Change to the tab at the given index."""
        self._tab_widget.change_tab(index)
        self._frame.contents['body'] = (self._tab_widget.get_selected_item(),
                                        None)

    def index(self, widget):
        """Return the index of the tab associated with the given widget.

        Raises ValueError if widget is not in the tabbed window."""
        return self._window_widget_list.index(widget)


def main():
    """Main entry point."""
    logging.basicConfig(filename='hangups.log', level=logging.DEBUG,
                        format=LOG_FORMAT)
    try:
        ChatUI()
    except KeyboardInterrupt:
        pass
    except:
        # urwid will prevent some exceptions from being printed unless we use
        # print a newline first.
        print('')
        raise


if __name__ == '__main__':
    main()
