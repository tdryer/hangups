"""Example of using hangups.build_user_conversation_list to data."""

import asyncio

import hangups

from common import run_example


@asyncio.coroutine
def sync_recent_conversations(client, _):
    user_list, conversation_list = (
        yield from hangups.build_user_conversation_list(client)
    )
    all_users = user_list.get_all()
    all_conversations = conversation_list.get_all(include_archived=True)

    print('{} known users'.format(len(all_users)))
    for idx, user in enumerate(all_users):
        name = user.full_name
        gaia_id = user.id_.gaia_id
        print('    ({}) {}: {}'.format(idx + 1, name, gaia_id))

    print('{} known conversations'.format(len(all_conversations)))
    for idx, conversation in enumerate(all_conversations):
        cid = conversation.id_

        if conversation.name:
            # This conversation is named
            name = '{} ({})'.format(conversation.name, cid)
        else:
            # This conversation isn't named; just generate a name from
            # the full names of users in the conversation that aren't us.
            users = ', '.join(
                map(lambda u: u.full_name,
                    filter(lambda u: u.id_ != user_list._self_user.id_,
                           conversation.users)
                )
            )
            name = 'Conversation with {} ({})'.format(users, cid)

        print('    ({}) {}'.format(idx + 1, name))


if __name__ == '__main__':
    run_example(sync_recent_conversations)
