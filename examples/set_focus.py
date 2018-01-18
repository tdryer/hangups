"""Example of using hangups to set focus to a conversation."""

import hangups

from common import run_example


async def set_focus(client, args):
    request = hangups.hangouts_pb2.SetFocusRequest(
        request_header=client.get_request_header(),
        conversation_id=hangups.hangouts_pb2.ConversationId(
            id=args.conversation_id
        ),
        type=hangups.hangouts_pb2.FOCUS_TYPE_FOCUSED,
        timeout_secs=int(args.timeout_secs),
    )
    await client.set_focus(request)


if __name__ == '__main__':
    run_example(set_focus, '--conversation-id', '--timeout-secs')
