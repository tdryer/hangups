"""Demo chat client using Hangups."""

from tornado import ioloop, gen
import logging
import urwid
from itertools import chain
from math import floor, ceil

import hangups


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


class DemoClient(hangups.HangupsClient):
    """Demo client for hangups."""

    def __init__(self, urwid_loop):
        super().__init__()

        self._urwid_loop = urwid_loop

        # {conversation_id: ConversationWidget}
        self._conv_widgets = {}
        # TabbedWindowWidget
        self._tabbed_window = None

        self.contacts = None
        self.conversations = None
        self._self_user_ids = None

    def get_conv_widget(self, conv_id):
        """Return an existing or new ConversationWidget."""
        if conv_id not in self._conv_widgets:
            participants_dict = {
                user_ids: self.contacts[user_ids] for user_ids in
                self.conversations[conv_id]['participants']
            }
            self._conv_widgets[conv_id] = ConversationWidget(
                conv_id, self._self_user_ids, participants_dict,
                self.on_send_message
            )
        return self._conv_widgets[conv_id]

    def get_contact_name(self, user_ids):
        """Return the name of a contact."""
        return self.contacts[user_ids]['first_name']

    def add_conversation_tab(self, conv_id, switch=False):
        """Add conversation tab if not present, and optionally switch to it."""
        conv_widget = self.get_conv_widget(conv_id)
        try:
            index = self._tabbed_window.index(conv_widget)
        except ValueError:
            index = self._tabbed_window.add_tab(conv_widget)
        if switch:
            self._tabbed_window.change_tab(index)

    @gen.coroutine
    def on_select_conversation(self, conv_id):
        """Called when the user selects a new conversation to listen to."""
        # switch to new or existing tab for the conversation
        self.add_conversation_tab(conv_id, switch=True)

    @gen.coroutine
    def on_send_message(self, conv_id, text):
        """Called when the user sends a message to the current conversation."""
        yield self.send_message(conv_id, text)

    @gen.coroutine
    def on_connect(self, conversations, contacts, self_user_ids):
        self.contacts = contacts
        self.conversations = conversations
        self._self_user_ids = self_user_ids

        # populate the contacts dict with users who aren't in our contacts
        required_users = set(chain.from_iterable(
            conversations[conv_id]['participants']
            for conv_id in conversations
        ))
        missing_users = required_users - set(self.contacts)
        if missing_users:
            users = yield self.get_users(missing_users)
            contacts.update(users)

        # show the conversation menu
        self._tabbed_window = TabbedWindowWidget([
            ConversationPickerWidget(self_user_ids, conversations, contacts,
                                     self.on_select_conversation)
        ])
        self._urwid_loop.widget = self._tabbed_window

    @gen.coroutine
    def on_event(self, event):
        """Handle events."""
        # Filter events we don't care about and don't want to open tabs for.
        if type(event) in [hangups.NewMessageEvent,
                           hangups.TypingChangedEvent]:
            conv_widget = self.get_conv_widget(event.conv_id)
            conv_widget.on_event(event)
            # open conversation tab in the background if not already present
            self.add_conversation_tab(event.conv_id)

    @gen.coroutine
    def on_disconnect(self):
        # TODO: handle this
        print('Connection lost')


def get_conv_name(self_user_ids, participants_dict, truncate=False):
    """Return the readable name for a conversation.

    For one-to-one conversations, the name is the full name of the other user.
    For group conversations, the name is a comma-separated list of first names.

    If truncate is true, only show up to two names in a group conversation.
    """
    participants = [p for ids, p in participants_dict.items()
                    if ids != self_user_ids]
    names = sorted(p['first_name'] for p in participants)
    if len(participants) == 1:
        return participants[0]['full_name']
    elif truncate and len(participants) > 2:
        return ', '.join(names[:2] + ['+{}'.format(len(names) - 2)])
    else:
        return ', '.join(names)


class ConversationPickerWidget(urwid.WidgetWrap):
    """Widget for picking a conversation."""

    def __init__(self, self_user_ids, conversations, contacts,
                 select_coroutine):
        self.tab_title = 'Conversations'
        self._select_coroutine = select_coroutine

        # build conversation labels and sort by last modified
        labelled_convs = []
        for conv_id in conversations:
            participants_dict = {user_ids: contacts[user_ids] for user_ids
                                 in conversations[conv_id]['participants']}
            label = get_conv_name(self_user_ids, participants_dict)
            labelled_convs.append({
                'id': conv_id,
                'label': label,
                'last_modified': conversations[conv_id]['last_modified']
            })
        labelled_convs = sorted(labelled_convs, reverse=True,
                                key=lambda c: c['last_modified'])
        buttons = [
            urwid.Button(f['label'], on_press=self._on_press, user_data=f['id'])
            for f in labelled_convs
        ]
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))
        widget = urwid.Padding(listbox, left=2, right=2)
        super().__init__(widget)

    def _on_press(self, button, conv_id):
        """Called when a conversation button is pressed."""
        future = self._select_coroutine(conv_id)
        ioloop.IOLoop.instance().add_future(future, lambda f: f.result())


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

    def __init__(self, participants_dict):
        self._widget = urwid.Text('')
        self._typing_statuses = {}
        self._participants = participants_dict
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

    def on_event(self, event):
        """Handle events."""
        if isinstance(event, hangups.TypingChangedEvent):
            self._typing_statuses[event.user_id] = event.typing_status
        elif isinstance(event, hangups.NewMessageEvent):
            self._typing_statuses[event.sender_id] = 'stopped'

        typers = [self._participants[user_id]['first_name']
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

    def __init__(self, conv_id, self_user_ids, participants_dict,
                 send_message_coroutine):
        self._conv_id = conv_id
        self._participants = participants_dict
        self._send_message_coroutine = send_message_coroutine

        self.tab_title = get_conv_name(self_user_ids, participants_dict,
                                       truncate=True)

        self._list_walker = urwid.SimpleFocusListWalker([])
        self._list_box = urwid.ListBox(self._list_walker)
        self._status_widget = StatusLineWidget(participants_dict)
        self._widget = urwid.Pile([
            ('weight', 1, self._list_box),
            ('pack', self._status_widget),
            ('pack', ReturnableEdit(self._on_return, caption='Send message: ')),
        ])
        # focus the edit widget by default
        self._widget.focus_position = 2
        super().__init__(self._widget)

    def on_event(self, event):
        """Handle events."""
        self._status_widget.on_event(event)
        if isinstance(event, hangups.NewMessageEvent):
            self._display_message(event.timestamp, event.sender_id, event.text)

    def _on_return(self, text):
        """Called when the user presses return on the send message widget."""
        future = self._send_message_coroutine(self._conv_id, text)
        ioloop.IOLoop.instance().add_future(future, lambda f: f.result())

    def _display_message(self, timestamp, user_id, text):
        """Display a new conversation message."""
        # format the message and add it to the list box
        date_str = timestamp.astimezone().strftime('%I:%M:%S %p')
        name = self._participants[user_id]['first_name']
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


@gen.coroutine
def main_coroutine():
    """Start an example chat client."""
    # prepare urwid UI
    top_widget = urwid.Filler(urwid.Text('loading...'))
    tornado_loop = urwid.TornadoEventLoop(ioloop.IOLoop.instance())
    loop = urwid.MainLoop(top_widget, URWID_PALETTE, event_loop=tornado_loop)

    # start the chat client
    client = DemoClient(loop)
    # TODO urwid widget for getting auth
    cookies = hangups.auth.get_auth_stdin('cookies.json')
    yield client.connect(cookies)
    future = client.run_forever()
    ioloop.IOLoop.instance().add_future(future, lambda f: f.result())

    # start urwid
    loop.run()


def main():
    """Main entry point."""
    logging.basicConfig(
        filename='hangups.log', level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    try:
        ioloop.IOLoop.instance().run_sync(main_coroutine)
    except KeyboardInterrupt:
        pass
    except:
        # XXX this is needed to get exceptions out of urwid for some reason
        print('')
        raise


if __name__ == '__main__':
    main()
