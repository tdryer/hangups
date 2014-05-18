"""Demo chat client using Hangups."""

from tornado import ioloop, gen
import datetime
import logging
import sys
import time

from hangups.client import HangupsClient
from hangups import auth


class DemoClient(HangupsClient):
    """Demo client for hangups."""

    def __init__(self):
        super().__init__()

        # ID of the conversation to listen to
        self.conversation_id = None

    @gen.coroutine
    def on_connect(self, conversations, contacts):
        print('Connection established')
        conv_ids = list(conversations.keys())
        for num, conv_id in enumerate(conv_ids):
            first_names = [contacts[user_ids]['first_name']
                           for user_ids in
                           conversations[conv_id]['participants']]
            print(' [{}] {}'.format(num, ', '.join(sorted(first_names))))
        if len(conv_ids) == 0:
            print('No conversations. Start one and try again.')
            sys.exit(1)
        # TODO: this blocks the IO loop
        num = int(input('Select a conversation: '))
        self.conversation_id = conv_ids[num]

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        if conversation_id == self.conversation_id:
            user = self.get_user(message.user_chat_id, message.user_gaia_id)
            print('({}) {}: {}'.format(
                datetime.datetime.fromtimestamp(
                    message.timestamp / 1000000
                ).strftime('%I:%M:%S %p'),
                user.name, message.text
            ))
            # respond to a \time message with the unix time
            if message.text == '\\time':
                yield self.send_message(
                    conversation_id,
                    'The current unix time is {}.'.format(int(time.time()))
                )

    @gen.coroutine
    def on_focus_update(self, conversation_id, user_ids, focus_status,
                        focus_device):
        if conversation_id == self.conversation_id:
            user = self.get_user(user_ids[0], user_ids[1])
            print('{} {} the conversation on {}'
                  .format(user.name, focus_status, focus_device))

    @gen.coroutine
    def on_typing_update(self, conversation_id, user_ids, typing_status):
        if conversation_id == self.conversation_id:
            user = self.get_user(user_ids[0], user_ids[1])
            print('{} {}'.format(user.name, typing_status))

    @gen.coroutine
    def on_disconnect(self):
        print('Connection lost')


@gen.coroutine
def main():
    """Start an example chat client."""
    client = DemoClient()
    cookies = auth.get_auth_stdin('cookies.json')
    yield client.connect(cookies)
    yield client.run_forever()


if __name__ == '__main__':
    logging.basicConfig(filename='hangups.log', level=logging.DEBUG)
    ioloop.IOLoop.instance().run_sync(main)
