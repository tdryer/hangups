"""Example of using hangups to enable group link sharing in a conversation."""

import hangups

from common import run_example


async def enable_group_link_sharing(client, args):
    request = hangups.hangouts_pb2.SetGroupLinkSharingEnabledRequest(
        request_header=client.get_request_header(),
        event_request_header=hangups.hangouts_pb2.EventRequestHeader(
            conversation_id=hangups.hangouts_pb2.ConversationId(
                id=args.conversation_id
            ),
            client_generated_id=client.get_client_generated_id(),
        ),
        group_link_sharing_status=(
            hangups.hangouts_pb2.GROUP_LINK_SHARING_STATUS_ON
        ),
    )
    await client.set_group_link_sharing_enabled(request)
    print('enabled group link sharing for conversation {}'.format(
        args.conversation_id
    ))

    request = hangups.hangouts_pb2.GetGroupConversationUrlRequest(
        request_header=client.get_request_header(),
        conversation_id=hangups.hangouts_pb2.ConversationId(
            id=args.conversation_id,
        )
    )
    response = await client.get_group_conversation_url(request)
    print(response.group_conversation_url)


if __name__ == '__main__':
    run_example(enable_group_link_sharing, '--conversation-id')
