"""Shared UI utility function."""

import hangups


def get_conv_name(conv, truncate=False, show_unread=False):
    """Return a readable name for a conversation.

    If the conversation has a custom name, use the custom name. Otherwise, for
    one-to-one conversations, the name is the full name of the other user. For
    group conversations, the name is a comma-separated list of first names. If
    the group conversation is empty, the name is "Empty Conversation".

    If truncate is true, only show up to two names in a group conversation.

    If show_unread is True, if there are unread chat messages, show the number
    of unread chat messages in parentheses after the conversation name.
    """
    num_unread = len([conv_event for conv_event in conv.unread_events if
                      isinstance(conv_event, hangups.ChatMessageEvent) and
                      not conv.get_user(conv_event.user_id).is_self])
    if show_unread and num_unread > 0:
        postfix = ' ({})'.format(num_unread)
    else:
        postfix = ''
    if conv.name is not None:
        return conv.name + postfix
    else:
        participants = sorted(
            (user for user in conv.users if not user.is_self),
            key=lambda user: user.id_
        )
        names = [user.first_name for user in participants]
        if len(participants) == 0:
            return "Empty Conversation" + postfix
        if len(participants) == 1:
            return participants[0].full_name + postfix
        elif truncate and len(participants) > 2:
            return (', '.join(names[:2] + ['+{}'.format(len(names) - 2)]) +
                    postfix)
        else:
            return ', '.join(names) + postfix
