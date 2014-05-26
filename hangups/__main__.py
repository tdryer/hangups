"""Demo chat client using Hangups."""

from tornado import ioloop, gen
from datetime import datetime
import logging
import time
import urwid
from itertools import chain

from hangups.client import HangupsClient
from hangups import auth


URWID_PALETTE = [
    ('header', 'bold', 'default'),
    ('msg_date', 'dark blue', 'default'),
    ('msg_sender', 'dark blue', 'default'),
    ('msg_text', '', 'default'),
]


class DemoClient(HangupsClient):
    """Demo client for hangups."""

    def __init__(self, urwid_loop):
        super().__init__()

        self._urwid_loop = urwid_loop
        self.conv_widget = None

        # ID of the conversation to listen to
        self.conversation_id = None
        self.contacts = None
        self.conversations = None

    def get_contact_name(self, user_ids):
        """Return the name of a contact."""
        return self.contacts[user_ids]['first_name']

    @gen.coroutine
    def on_select_conversation(self, conv_id):
        """Called when the user selects a new conversation to listen to."""
        self.conversation_id = conv_id

        # show the conversation view
        participants_dict = {user_ids: self.contacts[user_ids] for user_ids
                             in self.conversations[conv_id]['participants']}
        self.conv_widget = ConversationWidget(participants_dict,
                                              self.on_send_message)
        self._urwid_loop.widget = self.conv_widget

    @gen.coroutine
    def on_send_message(self, text):
        """Called when the user sends a message to the current conversation."""
        yield self.send_message(self.conversation_id, text)

    @gen.coroutine
    def on_connect(self, conversations, contacts, self_user_ids):
        self.contacts = contacts
        self.conversations = conversations

        # populate the contacts dict with users who aren't in our contacts
        required_users = set(chain.from_iterable(
            conversations[conv_id]['participants']
            for conv_id in conversations
        ))
        missing_users = required_users - set(self.contacts)
        if missing_users:
            users = yield self.get_users(missing_users)
            contacts.update(users)

        # build dict of conv ID -> conv name
        conv_dict = {}
        for conv_id in conversations.keys():
            conv_dict[conv_id] = ', '.join(
                self.get_contact_name(user_ids) for user_ids in
                conversations[conv_id]['participants']
                if user_ids != self_user_ids
            )

        # show the conversation menu
        # TODO: the widget class should handle formatting the conv names
        self._urwid_loop.widget = ConversationPickerWidget(
            conv_dict, self.on_select_conversation
        )

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        if conversation_id == self.conversation_id:
            user_ids = (message.user_chat_id, message.user_gaia_id)
            self.conv_widget.display_message(message)

            # respond to a \time message with the unix time
            if message.text == '\\time':
                yield self.send_message(
                    conversation_id,
                    'Hi {}, the current unix time is {}.'
                    .format(self.get_contact_name(user_ids), int(time.time()))
                )

    @gen.coroutine
    def on_focus_update(self, conversation_id, user_ids, focus_status,
                        focus_device):
        if conversation_id == self.conversation_id:
            pass # TODO implement displaying this in the ConversationWidget

    @gen.coroutine
    def on_typing_update(self, conversation_id, user_ids, typing_status):
        if conversation_id == self.conversation_id:
            pass # TODO implement displaying this in the ConversationWidget

    @gen.coroutine
    def on_disconnect(self):
        print('Connection lost')


class ConversationPickerWidget(urwid.WidgetWrap):
    """Widget for picking a conversation."""

    def __init__(self, conv_dict, select_coroutine):
        self._select_coroutine = select_coroutine
        header = urwid.Text(('header', 'Conversations'), align='center')
        buttons = [urwid.Button(conv_name, on_press=self._on_press,
                                user_data=conv_id)
                   for conv_id, conv_name in conv_dict.items()]
        listbox = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))
        widget = urwid.Pile([
            ('pack', header),
            ('weight', 1, urwid.Padding(listbox, left=2, right=2))
        ])
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

class ConversationWidget(urwid.WidgetWrap):
    """Widget for interacting with a conversation."""

    def __init__(self, participants_dict, send_message_coroutine):
        self._participants = participants_dict
        self._send_message_coroutine = send_message_coroutine

        names_str = ', '.join(p['first_name']
                              for p in participants_dict.values())
        title = 'Conversation: {}'.format(names_str)
        self._list_walker = urwid.SimpleFocusListWalker([])
        self._list_box = urwid.ListBox(self._list_walker)
        self._widget = urwid.Pile([
            ('pack', urwid.Text(('header', title), align='center')),
            ('weight', 1, self._list_box),
            ('pack', ReturnableEdit(self._on_return, caption='Send message: ')),
        ])
        # focus the edit widget by default
        self._widget.focus_position = 2
        super().__init__(self._widget)

    def _on_return(self, text):
        """Called when the user presses return on the send message widget."""
        future = self._send_message_coroutine(text)
        ioloop.IOLoop.instance().add_future(future, lambda f: f.result())

    def display_message(self, message):
        """Display a new conversation message."""
        # format the message
        date_int = message.timestamp / 1000000
        date_str = datetime.fromtimestamp(date_int).strftime('%I:%M:%S %p')
        user_ids = (message.user_chat_id, message.user_gaia_id)
        name = self._participants[user_ids]['first_name']

        # add the message to the list box
        self._list_walker.append(urwid.Text([
            ('msg_date', '(' + date_str + ') '),
            ('msg_sender', name + ': '),
            ('msg_text', message.text)
        ]))

        # scroll down to the new message
        self._list_box.set_focus(len(self._list_walker) - 1)


@gen.coroutine
def main():
    """Start an example chat client."""
    # prepare urwid UI
    top_widget = urwid.Filler(urwid.Text('loading...'))
    tornado_loop = urwid.TornadoEventLoop(ioloop.IOLoop.instance())
    loop = urwid.MainLoop(top_widget, URWID_PALETTE, event_loop=tornado_loop)

    # start the chat client
    client = DemoClient(loop)
    # TODO urwid widget for getting auth
    cookies = auth.get_auth_stdin('cookies.json')
    yield client.connect(cookies)
    future = client.run_forever()
    ioloop.IOLoop.instance().add_future(future, lambda f: f.result())

    # start urwid
    loop.run()


if __name__ == '__main__':
    logging.basicConfig(filename='hangups.log', level=logging.DEBUG)
    try:
        ioloop.IOLoop.instance().run_sync(main)
    except KeyboardInterrupt:
        pass
    except:
        # XXX this is needed to get exceptions out of urwid for some reason
        print('')
        raise
