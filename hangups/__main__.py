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

    @gen.coroutine
    def on_connect(self):
        print('Connection established')
        # Get all events in the past hour
        print('Requesting all events from the past hour')
        now = time.time() * 1000000
        one_hour = 60 * 60 * 1000000
        # TODO: add a proper API for this
        # XXX: doesn't work if there haven't been any events
        events = yield self._syncallnewevents(now - one_hour)

        conversations = {}
        for conversation in events.get('conversation_state', []):
            id_ = conversation['conversation']['id']['id']
            participants = {
                (p['id']['chat_id'], p['id']['gaia_id']): p['fallback_name']
                for p in conversation['conversation']['participant_data']
            }
            conversations[id_] = {
                'participants': participants,
            }

        conversations_list = list(enumerate(conversations.items()))
        if len(conversations_list) == 0:
            print(('No recent activity. '
                   'Interact with a conversation and try again.'))
            sys.exit(1)
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
            # respond to a \time message with the unix time
            if message.text == '\\time':
                yield self.send_message(
                    conversation_id,
                    'The current unix time is {}.'.format(int(time.time()))
                )

    @gen.coroutine
    def on_focus_update(self, conversation_id, user_ids, focus_status,
                        focus_device):
        if conversation_id == self.listen_id:
            user = self.get_user(user_ids[0], user_ids[1])
            print('{} {} the conversation on {}'
                  .format(user.name, focus_status, focus_device))

    @gen.coroutine
    def on_typing_update(self, conversation_id, user_ids, typing_status):
        if conversation_id == self.listen_id:
            user = self.get_user(user_ids[0], user_ids[1])
            print('{} {}'.format(user.name, typing_status))

    @gen.coroutine
    def on_disconnect(self):
        print('Connection lost')


@gen.coroutine
def main():
    """Start an example chat client."""
    cookies = auth.get_auth_stdin('cookies.json')
    client = DemoClient(cookies, 'https://talkgadget.google.com')
    yield client.connect()
    yield client.run_forever()


if __name__ == '__main__':
    logging.basicConfig(filename='hangups.log', level=logging.DEBUG)
    ioloop.IOLoop.instance().run_sync(main)
