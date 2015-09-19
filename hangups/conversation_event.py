"""ConversationEvent base class and subclasses.

These classes are wrappers for hangouts_pb2.Event instances. Parsing is done
through property methods, which prefer logging warnings to raising exceptions.
"""

import logging

from hangups import parsers, message_parser, user, hangouts_pb2

logger = logging.getLogger(__name__)
chat_message_parser = message_parser.ChatMessageParser()


class ConversationEvent(object):

    """An event which becomes part of the permanent record of a conversation.

    This corresponds to hangouts_pb2.Event.

    This is the base class for such events.
    """

    def __init__(self, event):
        self._event = event  # Event

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
        return self._event.conversation_id.id

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
            self.type_ = hangouts_pb2.SEGMENT_TYPE_LINK
        else:
            self.type_ = hangouts_pb2.SEGMENT_TYPE_TEXT
        self.text = text
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.is_strikethrough = is_strikethrough
        self.is_underline = is_underline
        self.link_target = link_target

    @staticmethod
    def from_str(text):
        """Generate ChatMessageSegment list parsed from a string.

        This method handles automatically finding line breaks, URLs and
        parsing simple formatting markup (simplified Markdown and HTML).
        """
        segment_list = chat_message_parser.parse(text)
        return [ChatMessageSegment(segment.text, **segment.params)
                for segment in segment_list]

    @staticmethod
    def deserialize(segment):
        """Create a chat message segment from hangups_pb2.Segment."""
        link_target = segment.link_data.link_target
        return ChatMessageSegment(
            segment.text, segment_type=segment.type,
            is_bold=segment.formatting.bold,
            is_italic=segment.formatting.italic,
            is_strikethrough=segment.formatting.strikethrough,
            is_underline=segment.formatting.underline,
            link_target=None if link_target == '' else link_target
        )

    def serialize(self):
        """Serialize the segment to protobuf."""
        segment = hangouts_pb2.Segment(
            type=self.type_,
            text=self.text,
            formatting=hangouts_pb2.Formatting(
                bold=self.is_bold,
                italic=self.is_italic,
                strikethrough=self.is_strikethrough,
                underline=self.is_underline,
            ),
        )
        if self.link_target is not None:
            segment.link_data.link_target = self.link_target
        return segment


class ChatMessageEvent(ConversationEvent):

    """An event containing a chat message.

    Corresponds to hangouts_pb2.ChatMessage.
    """

    @property
    def text(self):
        """A textual representation of the message."""
        lines = ['']
        for segment in self.segments:
            if segment.type_ == hangouts_pb2.SEGMENT_TYPE_TEXT:
                lines[-1] += segment.text
            elif segment.type_ == hangouts_pb2.SEGMENT_TYPE_LINK:
                lines[-1] += segment.text
            elif segment.type_ == hangouts_pb2.SEGMENT_TYPE_LINE_BREAK:
                lines.append('')
            else:
                logger.warning('Ignoring unknown chat message segment type: {}'
                               .format(segment.type_))
        lines.extend(self.attachments)
        return '\n'.join(lines)

    @property
    def segments(self):
        """List of hangouts_pb2.Segment in the message."""
        seg_list = self._event.chat_message.message_content.segment
        return [ChatMessageSegment.deserialize(seg) for seg in seg_list]

    @property
    def attachments(self):
        """Attachments in the message."""
        raw_attachments = self._event.chat_message.message_content.attachment
        if raw_attachments is None:
            raw_attachments = []
        attachments = []
        for attachment in raw_attachments:
            for embed_item_type in attachment.embed_item.type:
                known_types = [
                    hangouts_pb2.ITEM_TYPE_PLUS_PHOTO,
                    hangouts_pb2.ITEM_TYPE_PLACE_V2,
                    hangouts_pb2.ITEM_TYPE_PLACE,
                    hangouts_pb2.ITEM_TYPE_THING,
                ]
                if embed_item_type not in known_types:
                    logger.warning('Received chat message attachment with '
                                   'unknown embed type: %r', embed_item_type)

            if attachment.embed_item.HasField('plus_photo'):
                attachments.append(
                    attachment.embed_item.plus_photo.thumbnail.image_url
                )
        return attachments


class RenameEvent(ConversationEvent):

    """An event that renames a conversation.

    Corresponds to hangouts_pb2.ConversationRename.
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

    Corresponds to hangouts_pb2.MembershipChange.
    """

    @property
    def type_(self):
        """The membership change type (MembershipChangeType)."""
        return self._event.membership_change.type

    @property
    def participant_ids(self):
        """Return the UserIDs involved in the membership change.

        Multiple users may be added to a conversation at the same time.
        """
        return [user.UserID(chat_id=id_.chat_id, gaia_id=id_.gaia_id)
                for id_ in self._event.membership_change.participant_ids]
