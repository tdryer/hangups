import asyncio
import hangups

from common import run_example

@asyncio.coroutine
def sync_recent_conversations(client, _):
    users, conversations = yield from \
            hangups.build_user_conversation_list(client)
    all_users = users.get_all()
    all_conversations = conversations.get_all(include_archived=True)

    print('{} known users'.format(len(all_users)))
    for user in all_users:
        print('    {}: {}'.format(user.full_name, user.id_.gaia_id))
    print('{} known conversations'.format(len(all_conversations)))
    for conversation in all_conversations:
        if conversation.name:
            name = conversation.name
        else:
            name = 'Unnamed conversation ({})'.format(conversation.id_)
        print('    {}'.format(name))

if __name__ == '__main__':
    run_example(sync_recent_conversations)
