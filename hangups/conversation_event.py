"""ConversationEvent base class and subclasses.

These classes are wrappers for ClientEvent instances from the API. Parsing is
done through property methods, which prefer logging warnings to raising
exceptions.
"""

import logging

from hangups import parsers, user, schemas

logger = logging.getLogger(__name__)


class ConversationEvent(object):

    """An event which becomes part of the permanent record of a conversation.

    This corresponds to ClientEvent in the API.

    This is the base class for such events.
    """

    def __init__(self, client_event):
        self._event = client_event

    @property
    def timestamp(self):
        """A timestamp of when the event occurred."""
        return parsers.from_timestamp(self._event.timestamp)

    @property
    def user_id(self):
        """A UserID indicating who created the event."""
        return user.UserID(chat_id=self._event.sender_id.chat_id,
                           gaia_id=self._event.sender_id.gaia_id)

    @property
    def conversation_id(self):
        """The ID of the conversation the event belongs to."""
        return self._event.conversation_id.id_


class ChatMessageEvent(ConversationEvent):

    """An event containing a chat message.

    Corresponds to ClientChatMessage in the API.
    """

    @property
    def text(self):
        """A textual representation of the message."""
        lines = ['']
        for segment in self._event.chat_message.message_content.segment:
            if segment.type_ == schemas.SegmentType.TEXT:
                lines[-1] += segment.text
            elif segment.type_ == schemas.SegmentType.LINK:
                lines[-1] += segment.text
            elif segment.type_ == schemas.SegmentType.LINE_BREAK:
                lines.append('')
            else:
                logger.warning('Ignoring unknown chat message segment type: {}'
                               .format(segment.type_))
        for attachment in self._event.chat_message.message_content.attachment:
            if attachment.embed_item.type_ == [249]:  # PLUS_PHOTO
                # Try to parse an image message. Image messages contain no
                # message segments, and thus have no automatic textual
                # fallback.
                try:
                    lines.append(attachment.embed_item.data['27639957'][0][3])
                except (KeyError, TypeError, IndexError):
                    logger.warning(
                        'Failed to parse PLUS_PHOTO attachment: {}'
                        .format(attachment)
                    )
            elif attachment.embed_item.type_ == [340, 335, 0]:
                pass  # Google Maps URL that's already in the text.
            else:
                logger.warning('Ignoring unknown chat message attachment: {}'
                               .format(attachment))
        return '\n'.join(lines)


class RenameEvent(ConversationEvent):

    """An event that renames a conversation.

    Corresponds to ClientConversationRename in the API.
    """

    @property
    def new_name(self):
        """The conversation's new name."""
        return self._event.conversation_rename.new_name

    @property
    def old_name(self):
        """The conversation's old name."""
        return self._event.conversation_rename.old_name
