"""Example of using hangups to get conversation events."""

import hangups

from common import run_example


MAX_REQUESTS = 3
MAX_EVENTS = 5


async def get_events(client, args):
    _, conversation_list = await hangups.build_user_conversation_list(client)

    try:
        conversation = conversation_list.get(args.conversation_id)
    except KeyError:
        print('conversation {!r} not found'.format(args.conversation_id))
        return

    # Load events from the server
    all_events = await _get_events(conversation)
    # Load events cached in the conversation
    all_events_cached = await _get_events(conversation)

    assert (
        [event.timestamp for event in all_events] ==
        [event.timestamp for event in all_events_cached]
    )

    # Print the events oldest to newest
    for event in all_events:
        print('{} {} {!r}'.format(
            event.timestamp.strftime('%c'), event.__class__.__name__,
            getattr(event, 'text')
        ))


async def _get_events(conversation):
    all_events = []  # newest-first
    event_id = None
    for _ in range(MAX_REQUESTS):
        events = await conversation.get_events(
            event_id=event_id, max_events=MAX_EVENTS
        )
        event_id = events[0].id_  # oldest event
        all_events.extend(reversed(events))
    return list(reversed(all_events))  # oldest-first


if __name__ == '__main__':
    run_example(get_events, '--conversation-id')
