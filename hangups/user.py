"""User objects."""

import logging
from collections import namedtuple

logger = logging.getLogger(__name__)
DEFAULT_NAME = 'Unknown'

UserID = namedtuple('UserID', ['chat_id', 'gaia_id'])


class User(object):

    """A chat user.

    Handles full_name or first_name being None by creating an approximate
    first_name from the full_name, or setting both to DEFAULT_NAME.
    """

    def __init__(self, user_id, full_name, first_name, is_self):
        """Initialize a User."""
        self.id_ = user_id
        self.full_name = full_name if full_name is not None else DEFAULT_NAME
        self.first_name = (first_name if first_name is not None
                           else self.full_name.split()[0])
        self.is_self = is_self

    @staticmethod
    def from_entity(entity, self_user_id):
        """Initialize from a ClientEntity.

        If self_user_id is None, assume this is the self user.
        """
        user_id = UserID(chat_id=entity.id_.chat_id,
                         gaia_id=entity.id_.gaia_id)
        return User(user_id, entity.properties.display_name,
                    entity.properties.first_name,
                    (self_user_id == user_id) or (self_user_id is None))

    @staticmethod
    def from_conv_part_data(conv_part_data, self_user_id):
        """Initialize from ClientConversationParticipantData.

        If self_user_id is None, assume this is the self user.
        """
        user_id = UserID(chat_id=conv_part_data.id_.chat_id,
                         gaia_id=conv_part_data.id_.gaia_id)
        return User(user_id, conv_part_data.fallback_name, None,
                    (self_user_id == user_id) or (self_user_id is None))


class UserList(object):

    """Collection of User instances."""

    def __init__(self, self_entity, entities, conv_parts):
        """Initialize the list of Users.

        Creates users from the given ClientEntity and
        ClientConversationParticipantData instances. The latter is used only as
        a fallback, because it doesn't include a real first_name.
        """
        self_user = User.from_entity(self_entity, None)
        self._user_dict = {self_user.id_: self_user} # {UserID: User}
        # Add each entity as a new User.
        for entity in entities:
            user_ = User.from_entity(entity, self_user.id_)
            self._user_dict[user_.id_] = user_
        # Add each conversation participant as a new User if we didn't already
        # add them from an entity.
        for participant in conv_parts:
            user_ = User.from_conv_part_data(participant, self_user.id_)
            if user_.id_ not in self._user_dict:
                logging.warning('Adding fallback User: {}'.format(user_))
                self._user_dict[user_.id_] = user_
        logger.info('UserList initialized with {} user(s)'
                    .format(len(self._user_dict)))

    def get_user(self, user_id):
        """Return a User by their UserID.

        Raises KeyError if the User is not available.
        """
        # TODO: While there are still ways we could request a user that hangups
        # is not aware of, return a default user rather than raising KeyError.
        try:
            return self._user_dict[user_id]
        except KeyError:
            logger.warning('UserList returning unknown User for UserID {}'
                           .format(user_id))
            return User(user_id, DEFAULT_NAME, None, False)
