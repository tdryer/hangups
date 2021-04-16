"""User objects."""

from collections import namedtuple
import enum
import logging


logger = logging.getLogger(__name__)
DEFAULT_NAME = 'Unknown'

UserID = namedtuple('UserID', ['chat_id', 'gaia_id'])
"""A user ID, consisting of two parts which are always identical."""


NameType = enum.IntEnum('NameType', dict(DEFAULT=0, NUMERIC=1, REAL=2))
"""Indicates which type of name a user has.

``DEFAULT`` indicates that only a first name is available. ``NUMERIC``
indicates that only a numeric name is available. ``REAL`` indicates that a real
full name is available.
"""


class User:
    """A chat user.

    Use :class:`.UserList` or :class:`.ConversationList` methods to get
    instances of this class.
    """

    def __init__(self, user_id, full_name, first_name, photo_url,
                 canonical_email, emails, is_self):
        # Handle full_name or first_name being None by creating an approximate
        # first_name from the full_name, or setting both to DEFAULT_NAME.
        if not full_name:
            full_name = first_name = DEFAULT_NAME
            name_type = NameType.DEFAULT
        elif not any(c.isalpha() for c in full_name):
            first_name = full_name
            name_type = NameType.NUMERIC
        else:
            first_name = first_name if first_name else full_name.split()[0]
            name_type = NameType.REAL

        self.name_type = name_type
        """The user's name type (:class:`~hangups.user.NameType`)."""

        self.full_name = full_name
        """The user's full name (:class:`str`)."""

        self.first_name = first_name
        """The user's first name (:class:`str`)."""

        self.id_ = user_id
        """The user's ID (:class:`~hangups.user.UserID`)."""

        self.photo_url = photo_url
        """The user's profile photo URL (:class:`str`)."""

        self.canonical_email = canonical_email
        """The user's canonical email address (:class:`str`)."""

        self.emails = emails
        """The user's email addresses (:class:`list`)."""

        self.is_self = is_self
        """Whether this user is the current user (:class:`bool`)."""

    def upgrade_name(self, user_):
        """Upgrade name type of this user.

        Google Voice participants often first appear with no name at all, and
        then get upgraded unpredictably to numbers ("+12125551212") or names.

        Args:
            user_ (~hangups.user.User): User to upgrade with.
        """
        if user_.name_type > self.name_type:
            self.full_name = user_.full_name
            self.first_name = user_.first_name
            self.name_type = user_.name_type
            logger.debug('Added %s name to User "%s": %s',
                         self.name_type.name.lower(), self.full_name, self)

    @staticmethod
    def from_entity(entity, self_user_id):
        """Construct user from ``Entity`` message.

        Args:
            entity: ``Entity`` message.
            self_user_id (~hangups.user.UserID or None): The ID of the current
                user. If ``None``, assume ``entity`` is the current user.

        Returns:
            :class:`~hangups.user.User` object.
        """
        user_id = UserID(chat_id=entity.id.chat_id,
                         gaia_id=entity.id.gaia_id)
        return User(user_id, entity.properties.display_name,
                    entity.properties.first_name,
                    entity.properties.photo_url,
                    entity.properties.canonical_email,
                    entity.properties.email,
                    (self_user_id == user_id) or (self_user_id is None))

    @staticmethod
    def from_conv_part_data(conv_part_data, self_user_id):
        """Construct user from ``ConversationParticipantData`` message.

        Args:
            conv_part_id: ``ConversationParticipantData`` message.
            self_user_id (~hangups.user.UserID or None): The ID of the current
                user. If ``None``, assume ``conv_part_id`` is the current user.

        Returns:
            :class:`~hangups.user.User` object.
        """
        user_id = UserID(chat_id=conv_part_data.id.chat_id,
                         gaia_id=conv_part_data.id.gaia_id)
        if conv_part_data.fallback_name == 'unknown':
            full_name = None
        else:
            full_name = conv_part_data.fallback_name
        return User(user_id, full_name, None, None, None, [],
                    (self_user_id == user_id) or (self_user_id is None))


class UserList:
    """Maintains a list of all the users.

    Using :func:`build_user_conversation_list` to initialize this class is
    recommended.

    Args:
        client: The connected :class:`Client`.
        self_entity: ``Entity`` message for the current user.
        entities: List of known ``Entity`` messages.
        conv_parts: List of ``ConversationParticipantData`` messages. These are
            used as a fallback in case any users are missing.

    """

    def __init__(self, client, self_entity, entities, conv_parts):
        self._client = client
        self._self_user = User.from_entity(self_entity, None)
        # {UserID: User}
        self._user_dict = {self._self_user.id_: self._self_user}
        # Add each entity as a new User.
        for entity in entities:
            user_ = User.from_entity(entity, self._self_user.id_)
            self._user_dict[user_.id_] = user_
        # Add each conversation participant as a new User if we didn't already
        # add them from an entity. These don't include a real first_name, so
        # only use them as a fallback.
        for participant in conv_parts:
            self._add_user_from_conv_part(participant)
        logger.info('UserList initialized with %s user(s)',
                    len(self._user_dict))

        self._client.on_state_update.add_observer(self._on_state_update)

    def get_user(self, user_id):
        """Get a user by its ID.

        Args:
            user_id (~hangups.user.UserID): The ID of the user.

        Raises:
            KeyError: If no such user is known.

        Returns:
            :class:`~hangups.user.User` with the given ID.
        """
        try:
            return self._user_dict[user_id]
        except KeyError:
            logger.warning('UserList returning unknown User for UserID %s',
                           user_id)
            return User(user_id, None, None, None, None, [], False)

    def get_all(self):
        """Get all known users.

        Returns:
            List of :class:`~hangups.user.User` instances.
        """
        return self._user_dict.values()

    def _add_user_from_conv_part(self, conv_part):
        """Add or upgrade User from ConversationParticipantData."""
        user_ = User.from_conv_part_data(conv_part, self._self_user.id_)

        existing = self._user_dict.get(user_.id_)
        if existing is None:
            logger.warning('Adding fallback User with %s name "%s"',
                           user_.name_type.name.lower(), user_.full_name)
            self._user_dict[user_.id_] = user_
            return user_
        else:
            existing.upgrade_name(user_)
            return existing

    def _on_state_update(self, state_update):
        """Receive a StateUpdate"""
        if state_update.HasField('conversation'):
            self._handle_conversation(state_update.conversation)

    def _handle_conversation(self, conversation):
        """Receive Conversation and update list of users"""
        for participant in conversation.participant_data:
            self._add_user_from_conv_part(participant)
