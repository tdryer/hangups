"""Example of using hangups to create a new group conversation."""

import hangups

from common import run_example


async def send_message(client, args):
    request = hangups.hangouts_pb2.CreateConversationRequest(
        request_header=client.get_request_header(),
        type=hangups.hangouts_pb2.CONVERSATION_TYPE_GROUP,
        client_generated_id=client.get_client_generated_id(),
        invitee_id=[
            hangups.hangouts_pb2.InviteeID(
                gaia_id=gaia_id
            ) for gaia_id in args.gaia_ids.split(",")
        ],
        name=args.conversation_name
    )
    res = await client.create_conversation(request)
    print(res)


# --gaia-ids: list of participant gaia_id, separated by comma (excluding self)
# --conversation-name: the group conversation name to specify/customize
if __name__ == '__main__':
    run_example(send_message, '--gaia-ids', '--conversation-name')
