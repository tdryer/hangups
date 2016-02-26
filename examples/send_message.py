"""Example of using hangups to send a chat message to a conversation."""

import asyncio

import hangups


# ID of the conversation to send the message to. Conversation IDs can be found
# in the hangups debug log by searching for "conversation_id".
CONVERSATION_ID = 'UgyoEJW1M5TLSnPWY494AaABAQ'

# Plain-text content of the message to send.
MESSAGE = 'hello world'

# Path where OAuth refresh token is saved, allowing hangups to remember your
# credentials.
REFRESH_TOKEN_PATH = 'refresh_token.txt'


def main():
    """Main entry point."""

    # Obtain hangups authentication cookies, prompting for username and
    # password from standard in if necessary.
    cookies = hangups.auth.get_auth_stdin(REFRESH_TOKEN_PATH)

    # Instantiate hangups Client instance.
    client = hangups.Client(cookies)

    # Add an observer to the on_connect event to run the send_message coroutine
    # when hangups has finished connecting.
    client.on_connect.add_observer(lambda: asyncio.async(send_message(client)))

    # Start an asyncio event loop by running Client.connect. This will not
    # return until Client.disconnect is called, or hangups becomes
    # disconnected.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.connect())


@asyncio.coroutine
def send_message(client):
    """Send message using connected hangups.Client instance."""

    # Instantiate a SendChatMessageRequest Protocol Buffer message describing
    # the request.
    request = hangups.hangouts_pb2.SendChatMessageRequest(
        request_header=client.get_request_header(),
        event_request_header=hangups.hangouts_pb2.EventRequestHeader(
            conversation_id=hangups.hangouts_pb2.ConversationId(
                id=CONVERSATION_ID
            ),
            client_generated_id=client.get_client_generated_id(),
        ),
        message_content=hangups.hangouts_pb2.MessageContent(
            segment=[hangups.ChatMessageSegment(MESSAGE).serialize()],
        ),
    )

    try:
        # Make the request to the Hangouts API.
        yield from client.send_chat_message(request)
    finally:
        # Disconnect the hangups Client to make client.connect return.
        yield from client.disconnect()


if __name__ == '__main__':
    main()
