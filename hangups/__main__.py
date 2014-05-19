"""Demo chat client using Hangups."""

from tornado import ioloop, gen
import datetime
import logging
import sys
import time
import curses
import sys
from contextlib import contextmanager

from hangups.client import HangupsClient
from hangups import auth


class DemoClient(HangupsClient):
    """Demo client for hangups."""

    def __init__(self, term):
        super().__init__()

        # ID of the conversation to listen to
        self.conversation_id = None
        self.contacts = None

        self.term = term
        self.picker_window = ConversationPicker(term)
        self.conv_window = ConversationWindow(
            term, send_message_f=self.on_send_message
        )
        self.current_window = self.picker_window

    def get_contact_name(self, user_ids):
        """Return the name of a contact."""
        return self.contacts[user_ids]['first_name']

    @gen.coroutine
    def on_send_message(self, text):
        """Called by ConversationWindow when the user sends a message."""
        yield self.send_message(self.conversation_id, text)

    @gen.coroutine
    def on_connect(self, conversations, contacts):
        # send each keypress to the current window
        def on_stdin(fd, events):
            s = sys.stdin.read(1)
            future = self.current_window.keypress(s)
            ioloop.IOLoop.instance().add_future(future, lambda f: f.result())
        ioloop.IOLoop.instance().add_handler(1, on_stdin,
                                             ioloop.IOLoop.READ)

        conv_ids = list(conversations.keys())
        conv_names = []
        for num, conv_id in enumerate(conv_ids):
            first_names = [contacts[user_ids]['first_name']
                           for user_ids in
                           conversations[conv_id]['participants']]
            conv_names.append(', '.join(sorted(first_names)))
        # TODO: this blocks the IO loop
        #num = int(input('Select a conversation: '))
        #num = 0
        selection = yield self.picker_window.get_selection(conv_names)
        self.conversation_id = conv_ids[selection]

        self.current_window = self.conv_window
        self.current_window.draw()

        self.contacts = contacts

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        if conversation_id == self.conversation_id:
            user_ids = (message.user_chat_id, message.user_gaia_id)
            self.conv_window.push_line('({}) {}: {}'.format(
                datetime.datetime.fromtimestamp(
                    message.timestamp / 1000000
                ).strftime('%I:%M:%S %p'), self.get_contact_name(user_ids),
                message.text
            ))
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
            self.conv_window.push_line('{} {} the conversation on {}'
                  .format(self.get_contact_name(user_ids), focus_status,
                          focus_device))

    @gen.coroutine
    def on_typing_update(self, conversation_id, user_ids, typing_status):
        if conversation_id == self.conversation_id:
            self.conv_window.push_line('{} {}'.format(self.get_contact_name(user_ids),
                                 typing_status))

    @gen.coroutine
    def on_disconnect(self):
        self.conv_window.push_line('Connection lost')


class ConversationWindow(object):

    def __init__(self, term, send_message_f):
        self.term = term
        self.lines = []
        self.text = ''
        self.send_message_f = send_message_f

    @gen.coroutine
    def keypress(self, char):
        if char == '\r': # return
            yield self.send_message_f(self.text)
            self.text = ''
        if char == '\x7f': # backspace
            self.text = self.text[:-1]
        else:
            self.text += char
        self.draw()

    def draw(self):
        self.term.clear()
        self.term.move(0, 0)
        self.term.text('Conversation'.ljust(self.term.width))

        line_num = len(self.lines) - 1
        for y in reversed(range(1, self.term.height - 1)):
            if line_num < 0:
                break
            self.term.move(0, y)
            self.term.text(self.lines[line_num][:self.term.width])
            line_num -= 1

        self.term.move(0, self.term.height - 1)
        self.term.text(': ' + self.text)

    def push_line(self, line):
        self.lines.append(line)
        self.draw()


class ConversationPicker(object):

    def __init__(self, term):
        self.conversation_names = []
        self.selection = 0
        self.term = term

        self._get_selection_callback = None

    @gen.coroutine
    def keypress(self, char):
        if char == 'j':
            self.selection += 1
        elif char == 'k':
            self.selection -= 1
        elif char == '\r':
            self._get_selection_callback(self.selection)

        if self.selection < 0:
            self.selection = 0
        elif self.selection >= len(self.conversation_names):
            self.selection = len(self.conversation_names) - 1
        self.draw()

    def draw(self):
        self.term.clear()
        self.term.move(0, 0)
        self.term.text('Conversations\n')
        for num, conversation_name in enumerate(self.conversation_names):
            selected = num == self.selection
            line = (' > ' if selected else '   ') + conversation_name
            line = line.ljust(self.term.width)
            self.term.text(line)

    @gen.coroutine
    def get_selection(self, conversation_names):
        self.conversation_names = conversation_names
        self.draw()
        self._get_selection_callback = yield gen.Callback('get_selection')
        selection = yield gen.Wait('get_selection')
        return selection



class Terminal(object):

    def __init__(self):
        self._stdscr = curses.initscr()

    @contextmanager
    def fullscreen(self):
        try:
            self.enter_fullscreen()
            yield
        finally:
            self.exit_fullscreen()

    def enter_fullscreen(self):
        #curses.noecho() # do not echo keys
        #curses.cbreak() # don't wait for enter
        curses.curs_set(0) # make cursor invisible
        self._stdscr.erase()
        self._stdscr.refresh()

    def exit_fullscreen(self):
        #curses.nocbreak()
        #stdscr.keypad(0)
        #curses.echo()
        curses.endwin()

    def text(self, string):
        self._stdscr.addstr(string)
        self._stdscr.refresh()

    def move(self, x, y):
        self._stdscr.move(y, x)

    def clear(self):
        self._stdscr.erase()
        self._stdscr.refresh()

    @property
    def width(self):
        return self._stdscr.getmaxyx()[1]

    @property
    def height(self):
        return self._stdscr.getmaxyx()[0]


@gen.coroutine
def main():
    """Start an example chat client."""
    term = Terminal()
    with term.fullscreen():
        client = DemoClient(term)
        # TODO: make this use curses
        cookies = auth.get_auth_stdin('cookies.json')
        yield client.connect(cookies)
        yield client.run_forever()


if __name__ == '__main__':
    logging.basicConfig(filename='hangups.log', level=logging.DEBUG)
    ioloop.IOLoop.instance().run_sync(main)
