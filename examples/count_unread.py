#!/usr/bin/env python3

"""Example of using hangups to count the number of unread messages."""

import sys
import os
import asyncio
import hangups

# Path where OAuth refresh token is saved, allowing hangups to remember your
# credentials.
REFRESH_TOKEN_PATH = os.path.expanduser('~/.cache/hangups/refresh_token.txt')


def main():
    """Main entry point."""

    try:
        # Obtain hangups authentication cookies, raising an error if not found.

        def handler ( *x, **y ) :
            raise hangups.auth.GoogleAuthError('Could not find refresh token file')

        cookies = hangups.auth.get_auth(handler , REFRESH_TOKEN_PATH)

        # Instantiate hangups Client instance.
        client = hangups.Client(cookies)

        # Add an observer to the on_connect event to run the
        # retrieve_count coroutine when hangups has finished
        # connecting.
        client.on_connect.add_observer(lambda: asyncio.async(
            retrieve_count(client)
        ))

        # Start an asyncio event loop by running Client.connect. This will not
        # return until Client.disconnect is called, or hangups becomes
        # disconnected.
        loop = asyncio.get_event_loop()
        loop.run_until_complete(client.connect())

    except hangups.auth.GoogleAuthError as e :
        print( '?' )


def num_unread ( conv ) :
    return len([conv_event for conv_event in conv.unread_events if
        isinstance(conv_event, hangups.ChatMessageEvent) and
        not conv.get_user(conv_event.user_id).is_self])

@asyncio.coroutine
def retrieve_count(client):

    try:
        users, conversations = yield from hangups.build_user_conversation_list(client)
        count = sum( map( num_unread , conversations.get_all( )))
        print( count )

    finally:
        # Disconnect the hangups Client to make client.connect return.
        yield from client.disconnect()


if __name__ == '__main__':
    main()
