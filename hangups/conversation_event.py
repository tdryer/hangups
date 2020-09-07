"""ConversationEvent base class and subclasses.

These classes are wrappers for hangouts_pb2.Event instances. Parsing is done
through property methods, which prefer logging warnings to raising exceptions.
"""

import logging

from hangups import parsers, message_parser, user, hangouts_pb2

logger = logging.getLogger(__name__)
chat_message_parser = message_parser.ChatMessageParser()


class ConversationEvent:
    """An event which becomes part of the permanent record of a conversation.

    This is a wrapper for the ``Event`` message, which may contain one of many
    subtypes, represented here as other subclasses.

    Args:
        event: ``Event`` message.
    """

    def __init__(self, event):
        self._event = event  # Event

    @property
    def timestamp(self):
        """When the event occurred (:class:`datetime.datetime`)."""
        return parsers.from_timestamp(self._event.timestamp)

    @property
    def user_id(self):
        """Who created the event (:class:`~hangups.user.UserID`)."""
        return user.UserID(chat_id=self._event.sender_id.chat_id,
                           gaia_id=self._event.sender_id.gaia_id)

    @property
    def conversation_id(self):
        """ID of the conversation containing the event (:class:`str`)."""
        return self._event.conversation_id.id

    @property
    def id_(self):
        """ID of this event (:class:`str`)."""
        return self._event.event_id


class ChatMessageSegment:
    """A segment of a chat message in :class:`ChatMessageEvent`.

    Args:
        text (str): Text of the segment.
        segment_type: (optional) One of ``SEGMENT_TYPE_TEXT``,
            ``SEGMENT_TYPE_LINE_BREAK``, or ``SEGMENT_TYPE_LINK``. Defaults to
            ``SEGMENT_TYPE_TEXT``, or ``SEGMENT_TYPE_LINK`` if ``link_target``
            is specified.
        is_bold (bool): (optional) Whether the text is bold. Defaults to
            ``False``.
        is_italic (bool): (optional) Whether the text is italic. Defaults to
            ``False``.
        is_strikethrough (bool): (optional) Whether the text is struck through.
            Defaults to ``False``.
        is_underline (bool): (optional) Whether the text is underlined.
            Defaults to ``False``.
        link_target (str): (option) URL to link to. Defaults to ``None``.
    """

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
        """Construct :class:`ChatMessageSegment` list parsed from a string.

        Args:
            text (str): Text to parse. May contain line breaks, URLs and
                formatting markup (simplified Markdown and HTML) to be
                converted into equivalent segments.

        Returns:
            List of :class:`ChatMessageSegment` objects.
        """
        segment_list = chat_message_parser.parse(text)
        return [ChatMessageSegment(segment.text, **segment.params)
                for segment in segment_list]

    @staticmethod
    def deserialize(segment):
        """Construct :class:`ChatMessageSegment` from ``Segment`` message.

        Args:
            segment: ``Segment`` message to parse.

        Returns:
            :class:`ChatMessageSegment` object.
        """
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
        """Serialize this segment to a ``Segment`` message.

        Returns:
            ``Segment`` message.
        """
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
    """An event that adds a new message to a conversation.

    Corresponds to the ``ChatMessage`` message.
    """

    @property
    def text(self):
        """Text of the message without formatting (:class:`str`)."""
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
        """List of :class:`ChatMessageSegment` in message (:class:`list`)."""
        seg_list = self._event.chat_message.message_content.segment
        return [ChatMessageSegment.deserialize(seg) for seg in seg_list]

    @property
    def attachments(self):
        """List of attachments in the message (:class:`list`)."""
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


class OTREvent(ConversationEvent):
    """An event that changes a conversation's OTR (history) mode.

    Corresponds to the ``OTRModification`` message.
    """

    @property
    def new_otr_status(self):
        """The conversation's new OTR status.

        May be either ``OFF_THE_RECORD_STATUS_OFF_THE_RECORD`` or
        ``OFF_THE_RECORD_STATUS_ON_THE_RECORD``.
        """
        return self._event.otr_modification.new_otr_status

    @property
    def old_otr_status(self):
        """The conversation's old OTR status.

        May be either ``OFF_THE_RECORD_STATUS_OFF_THE_RECORD`` or
        ``OFF_THE_RECORD_STATUS_ON_THE_RECORD``.
        """
        return self._event.otr_modification.old_otr_status


class RenameEvent(ConversationEvent):
    """An event that renames a conversation.

    Corresponds to the ``ConversationRename`` message.
    """

    @property
    def new_name(self):
        """The conversation's new name (:class:`str`).

        May be an empty string if the conversation's name was cleared.
        """
        return self._event.conversation_rename.new_name

    @property
    def old_name(self):
        """The conversation's old name (:class:`str`).

        May be an empty string if the conversation had no previous name.
        """
        return self._event.conversation_rename.old_name


class MembershipChangeEvent(ConversationEvent):
    """An event that adds or removes a conversation participant.

    Corresponds to the ``MembershipChange`` message.
    """

    @property
    def type_(self):
        """The type of membership change.

        May be either ``MEMBERSHIP_CHANGE_TYPE_JOIN`` or
        ``MEMBERSHIP_CHANGE_TYPE_LEAVE``.
        """
        return self._event.membership_change.type

    @property
    def participant_ids(self):
        """:class:`~hangups.user.UserID` of users involved (:class:`list`)."""
        return [user.UserID(chat_id=id_.chat_id, gaia_id=id_.gaia_id)
                for id_ in self._event.membership_change.participant_ids]


class HangoutEvent(ConversationEvent):
    """An event that is related to a Hangout voice or video call.

    Corresponds to the ``HangoutEvent`` message.
    """

    @property
    def event_type(self):
        """The Hangout event type.

        May be one of ``HANGOUT_EVENT_TYPE_START``, ``HANGOUT_EVENT_TYPE_END``,
        ``HANGOUT_EVENT_TYPE_JOIN``, ``HANGOUT_EVENT_TYPE_LEAVE``,
        ``HANGOUT_EVENT_TYPE_COMING_SOON``, or ``HANGOUT_EVENT_TYPE_ONGOING``.
        """
        return self._event.hangout_event.event_type


class GroupLinkSharingModificationEvent(ConversationEvent):
    """An event that modifies a conversation's group link sharing status.

    Corresponds to the ``GroupLinkSharingModification`` message.
    """

    @property
    def new_status(self):
        """The new group link sharing status.

        May be either ``GROUP_LINK_SHARING_STATUS_ON`` or
        ``GROUP_LINK_SHARING_STATUS_OFF``.
        """
        return self._event.group_link_sharing_modification.new_status
