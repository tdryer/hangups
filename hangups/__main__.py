"""Demo chat client using Hangups."""

from tornado import ioloop, gen
import datetime
import logging
import time
import urwid

from hangups.client import HangupsClient
from hangups import auth


# TODO: not using these styles yet
URWID_PALETTE = [
    ('header', 'bold', 'default'),
    ('msg_header', 'bold', 'default'),
    ('msg', '', 'default'),
]


class DemoClient(HangupsClient):
    """Demo client for hangups."""

    def __init__(self, urwid_loop):
        super().__init__()

        self._urwid_loop = urwid_loop
        # method for adding lines to the conversation view
        self.add_line = None

        # ID of the conversation to listen to
        self.conversation_id = None
        self.contacts = None

    def get_contact_name(self, user_ids):
        """Return the name of a contact."""
        return self.contacts[user_ids]['first_name']

    @gen.coroutine
    def on_select_conversation(self, conv_id):
        """Called when the user selects a new conversation to listen to."""
        self.conversation_id = conv_id

        # show the conversation view
        widget, self.add_line = conversation_view(
            'TODO conversation name here', self.on_send_message
        )
        self._urwid_loop.widget = widget

    @gen.coroutine
    def on_send_message(self, text):
        """Called when the user sends a message to the current conversation."""
        yield self.send_message(self.conversation_id, text)

    @gen.coroutine
    def on_connect(self, conversations, contacts):
        self.contacts = contacts

        # build dict of conv ID -> conv name
        conv_dict = {}
        for conv_id in conversations.keys():
            conv_dict[conv_id] = ', '.join(
                contacts[user_ids]['first_name'] for user_ids in
                conversations[conv_id]['participants']
            )

        # show the conversation menu
        self._urwid_loop.widget = conversation_menu(
            conv_dict, self.on_select_conversation
        )

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        if conversation_id == self.conversation_id:
            user_ids = (message.user_chat_id, message.user_gaia_id)
            self.add_line(
                '({}) {}: {}'.format(
                    datetime.datetime.fromtimestamp(
                        message.timestamp / 1000000
                    ).strftime('%I:%M:%S %p'), self.get_contact_name(user_ids),
                    message.text
                )
            )
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
            self.add_line(
                '{} {} the conversation on {}'
                .format(self.get_contact_name(user_ids), focus_status,
                        focus_device)
            )

    @gen.coroutine
    def on_typing_update(self, conversation_id, user_ids, typing_status):
        if conversation_id == self.conversation_id:
            self.add_line(
                '{} {}'.format(self.get_contact_name(user_ids), typing_status)
            )

    @gen.coroutine
    def on_disconnect(self):
        print('Connection lost')


def conversation_menu(conv_dict, on_select_coroutine):
    """Return an urwid menu for choosing a conversation."""
    def on_press(button, conv_id):
        future = on_select_coroutine(conv_id)
        ioloop.IOLoop.instance().add_future(future, lambda f: f.result())
    header = urwid.Text('Conversations')
    buttons = [urwid.Button(conv_name, on_press=on_press, user_data=conv_id)
               for num, (conv_id, conv_name) in enumerate(conv_dict.items())]
    listbox = urwid.ListBox(urwid.SimpleFocusListWalker(buttons))
    return urwid.Pile([
        ('pack', header),
        ('weight', 1, urwid.Padding(listbox, left=2, right=2))
    ])


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


def conversation_view(conv_name, on_send_message_coroutine):
    """Return an urwid widget for showing a conversation."""
    def on_return(text):
        future = on_send_message_coroutine(text)
        ioloop.IOLoop.instance().add_future(future, lambda f: f.result())
    line_list = urwid.SimpleFocusListWalker([])
    list_box = urwid.ListBox(line_list)
    def add_line(line):
        line_list.append(urwid.Text(line))
        list_box.set_focus(len(line_list) - 1)
    widget = urwid.Pile([
        ('pack', urwid.Text(('header', 'Conversation: {}'
                             .format(conv_name)), align='center')),
        ('weight', 1, list_box),
        ('pack', ReturnableEdit(on_return, caption='Send message: ')),
    ])
    # focus the Edit widget by default
    widget.focus_position = 2
    return (widget, add_line)


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
    except:
        # XXX this is needed to get exceptions out of urwid for some reason
        print('')
        raise
