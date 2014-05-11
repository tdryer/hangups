"""Demo chat client using Hangups."""

import time
import datetime
import logging
from tornado import ioloop, gen

from hangups.client import HangupsClient


class DemoClient(HangupsClient):
    """Demo client for hangups."""

    @gen.coroutine
    def on_connect(self):
        print('Connection established')
        # Get all events in the past hour
        print('Requesting all events from the past hour')
        now = time.time() * 1000000
        one_hour = 60 * 60 * 1000000
        # TODO: add a proper API for this
        # XXX: doesn't work if there haven't been any events
        events = yield self.syncallnewevents(now - one_hour)

        conversations = {}
        for conversation in events['conversation_state']:
            id_ = conversation['conversation']['id']['id']
            participants = {
                (p['id']['chat_id'], p['id']['gaia_id']): p['fallback_name']
                for p in conversation['conversation']['participant_data']
            }
            conversations[id_] = {
                'participants': participants,
            }

        conversations_list = list(enumerate(conversations.items()))
        print('Activity has recently occurred in the conversations:')
        for n, (_, conversation) in conversations_list:
            print(' [{}] {}'.format(
                n, ', '.join(sorted(conversation['participants'].values()))
            ))
        # TODO: do this without blocking the IO loop
        conversation_index = int(input('Select a conversation to listen to: '))
        conversation_id = conversations_list[conversation_index][1][0]
        conversation = conversations_list[conversation_index][1][1]
        print('Now listening to conversation\n')
        self.listen_id = conversation_id

    @gen.coroutine
    def on_message_receive(self, conversation_id, message):
        if conversation_id == self.listen_id:
            user = self.get_user(message.user_chat_id, message.user_gaia_id)
            print('({}) {}: {}'.format(
                datetime.datetime.fromtimestamp(
                    message.timestamp / 1000000
                ).strftime('%I:%M:%S %p'),
                user.name, message.text
            ))

    @gen.coroutine
    def on_disconnect(self):
        print('Connection lost')


def load_cookies_txt():
    """Return cookies dictionary loaded from cookies.txt file.

    Expected format is the same as the body of an HTTP cookie header.
    """
    cookies_str = open('cookies.txt').read()
    cookies_list = [s.split('=', 1) for s in
                    cookies_str.strip('\n').split('; ')]
    return {cookie[0]: cookie[1] for cookie in cookies_list}


@gen.coroutine
def main():
    """Start an example chat client."""
    cookies = load_cookies_txt()
    client = DemoClient(cookies, 'https://talkgadget.google.com')
    yield client.connect()
    yield client.run_forever()


if __name__ == '__main__':
    logging.basicConfig(filename='hangups.log', level=logging.DEBUG)
    ioloop.IOLoop.instance().run_sync(main)
