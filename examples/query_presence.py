"""Example of using hangups to query presence of a user."""

import hangups

from common import run_example


async def query_presence(client, args):
    request = hangups.hangouts_pb2.QueryPresenceRequest(
        request_header=client.get_request_header(),
        participant_id=[
            hangups.hangouts_pb2.ParticipantId(gaia_id=args.user_id),
        ],
        field_mask=[
            hangups.hangouts_pb2.FIELD_MASK_REACHABLE,
            hangups.hangouts_pb2.FIELD_MASK_AVAILABLE,
            hangups.hangouts_pb2.FIELD_MASK_MOOD,
            hangups.hangouts_pb2.FIELD_MASK_DEVICE,
            hangups.hangouts_pb2.FIELD_MASK_LAST_SEEN,
        ],
    )
    res = await client.query_presence(request)
    print(res)


if __name__ == '__main__':
    run_example(query_presence, '--user-id')
