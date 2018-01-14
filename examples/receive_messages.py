"""Example of using hangups to receive chat messages.

Uses the high-level hangups API.
"""

import asyncio

import hangups

from common import run_example


async def receive_messages(client, args):
    print('loading conversation list...')
    user_list, conv_list = (
        await hangups.build_user_conversation_list(client)
    )
    conv_list.on_event.add_observer(on_event)

    print('waiting for chat messages...')
    while True:
        await asyncio.sleep(1)


def on_event(conv_event):
    if isinstance(conv_event, hangups.ChatMessageEvent):
        print('received chat message: {!r}'.format(conv_event.text))


if __name__ == '__main__':
    run_example(receive_messages)
