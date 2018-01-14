"""Example of using hangups to get recent conversations."""

import hangups

from common import run_example


async def sync_recent_conversations(client, _):
    request = hangups.hangouts_pb2.SyncRecentConversationsRequest(
        request_header=client.get_request_header(),
        max_conversations=20,
        max_events_per_conversation=1,
        sync_filter=[hangups.hangouts_pb2.SYNC_FILTER_INBOX],
    )
    res = await client.sync_recent_conversations(request)

    # Sort the returned conversations by recency.
    conv_states = sorted(
        res.conversation_state,
        key=lambda conv_state: (
            conv_state.conversation.self_conversation_state.sort_timestamp
        ),
        reverse=True
    )

    # Print the list of conversations and their participants.
    for conv_state in conv_states:
        if conv_state.conversation.name:
            conv_name = repr(conv_state.conversation.name)
        else:
            conv_name = 'Unnamed Hangout'
        print(' - {} ({})'.format(conv_name, conv_state.conversation_id.id))
        for participant in conv_state.conversation.participant_data:
            if participant.fallback_name:
                name = repr(participant.fallback_name)
            else:
                name = 'No fallback name'
            print('     - {} ({})'.format(name, participant.id.gaia_id))


if __name__ == '__main__':
    run_example(sync_recent_conversations)
