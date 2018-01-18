"""Example of using hangups to get conversation messages."""

import hangups

from common import run_example


async def get_conversation(client, args):
    request = hangups.hangouts_pb2.GetConversationRequest(
        request_header=client.get_request_header(),
        conversation_spec=hangups.hangouts_pb2.ConversationSpec(
            conversation_id=hangups.hangouts_pb2.ConversationId(
                id=args.conversation_id
            ),
        ),
        include_event=True,
        max_events_per_conversation=10,
    )
    res = await client.get_conversation(request)
    print(res)


if __name__ == '__main__':
    run_example(get_conversation, '--conversation-id')
