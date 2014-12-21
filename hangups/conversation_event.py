"""ConversationEvent base class and subclasses.

These classes are wrappers for ClientEvent instances from the API. Parsing is
done through property methods, which prefer logging warnings to raising
exceptions.
"""

import logging
import re

from hangups import parsers, user, schemas

logger = logging.getLogger(__name__)
URL_RE = re.compile(r'https?://\S+')


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

    @property
    def id_(self):
        """The ID of the ConversationEvent."""
        return self._event.event_id


class ChatMessageSegment(object):

    """A segment of a chat message."""

    def __init__(self, text, segment_type=None,
                 is_bold=False, is_italic=False, is_strikethrough=False,
                 is_underline=False, link_target=None):
        """Create a new chat message segment."""
        if segment_type is not None:
            self.type_ = segment_type
        elif link_target is not None:
            self.type_ = schemas.SegmentType.LINK
        else:
            self.type_ = schemas.SegmentType.TEXT
        self.text = text
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.is_strikethrough = is_strikethrough
        self.is_underline = is_underline
        self.link_target = link_target

    @staticmethod
    def from_str(text):
        """Generate ChatMessageSegment list parsed from a string.

        This method handles automatically finding URLs and making them into
        link segments.
        """
        last = 0
        for match in URL_RE.finditer(text):
            if match.start() > last:
                yield ChatMessageSegment(text[last:match.start()])
            yield ChatMessageSegment(match.group(), link_target=match.group())
            last = match.end()
        if last != len(text):
            yield ChatMessageSegment(text[last:])

    @staticmethod
    def deserialize(segment):
        """Create a chat message segment from a parsed MESSAGE_SEGMENT."""
        # The formatting options are optional.
        if segment.formatting is None:
            is_bold = False
            is_italic = False
            is_strikethrough = False
            is_underline = False
        else:
            is_bold = bool(segment.formatting.bold)
            is_italic = bool(segment.formatting.italic)
            is_strikethrough = bool(segment.formatting.strikethrough)
            is_underline = bool(segment.formatting.underline)
        return ChatMessageSegment(
            segment.text, segment_type=segment.type_,
            is_bold=is_bold, is_italic=is_italic,
            is_strikethrough=is_strikethrough, is_underline=is_underline,
        )

    def serialize(self):
        """Serialize the segment to pblite."""
        return [self.type_.value, self.text, [
            1 if self.is_bold else 0,
            1 if self.is_italic else 0,
            1 if self.is_strikethrough else 0,
            1 if self.is_underline else 0,
        ], [self.link_target]]


class ChatMessageEvent(ConversationEvent):

    """An event containing a chat message.

    Corresponds to ClientChatMessage in the API.
    """

    @property
    def text(self):
        """A textual representation of the message."""
        lines = ['']
        for segment in self.segments:
            if segment.type_ == schemas.SegmentType.TEXT:
                lines[-1] += segment.text
            elif segment.type_ == schemas.SegmentType.LINK:
                lines[-1] += segment.text
            elif segment.type_ == schemas.SegmentType.LINE_BREAK:
                lines.append('')
            else:
                logger.warning('Ignoring unknown chat message segment type: {}'
                               .format(segment.type_))
        lines.extend(self.attachments)
        return '\n'.join(lines)

    @property
    def segments(self):
        """List of ChatMessageSegments in the message."""
        seg_list = self._event.chat_message.message_content.segment
        # seg_list may be None because the field is optional
        if seg_list is not None:
            return [ChatMessageSegment.deserialize(seg) for seg in seg_list]
        else:
            return []

    @property
    def attachments(self):
        """Attachments in the message."""
        raw_attachments = self._event.chat_message.message_content.attachment
        if raw_attachments is None:
            raw_attachments = []
        attachments = []
        for attachment in raw_attachments:
            if attachment.embed_item.type_ == [249]:  # PLUS_PHOTO
                # Try to parse an image message. Image messages contain no
                # message segments, and thus have no automatic textual
                # fallback.
                try:
                    attachments.append(
                        attachment.embed_item.data['27639957'][0][3]
                    )
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
        return attachments


class RenameEvent(ConversationEvent):

    """An event that renames a conversation.

    Corresponds to ClientConversationRename in the API.
    """

    @property
    def new_name(self):
        """The conversation's new name.

        An empty string if the conversation's name was cleared.
        """
        return self._event.conversation_rename.new_name

    @property
    def old_name(self):
        """The conversation's old name.

        An empty string if the conversation had no previous name.
        """
        return self._event.conversation_rename.old_name


class MembershipChangeEvent(ConversationEvent):

    """An event that adds or removes a conversation participant.

    Corresponds to ClientMembershipChange in the API.
    """

    @property
    def type_(self):
        """The membership change type (MembershipChangeType)."""
        return self._event.membership_change.type_

    @property
    def participant_ids(self):
        """Return the UserIDs involved in the membership change.

        Multiple users may be added to a conversation at the same time.
        """
        return [user.UserID(chat_id=id_.chat_id, gaia_id=id_.gaia_id)
                for id_ in self._event.membership_change.participant_ids]
