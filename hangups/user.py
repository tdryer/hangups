"""User objects."""

from collections import namedtuple
import asyncio
import logging

from hangups import exceptions

logger = logging.getLogger(__name__)
DEFAULT_NAME = 'Unknown'

UserID = namedtuple('UserID', ['chat_id', 'gaia_id'])


class User(object):

    """A chat user.

    Handles full_name or first_name being None by creating an approximate
    first_name from the full_name, or setting both to DEFAULT_NAME.
    """

    def __init__(self, user_id, full_name, first_name, photo_url, emails,
                 is_self):
        """Initialize a User."""
        self.id_ = user_id
        self.full_name = full_name if full_name is not None else DEFAULT_NAME
        self.first_name = (first_name if first_name is not None
                           else self.full_name.split()[0])
        self.photo_url = photo_url
        self.emails = emails
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
                    entity.properties.photo_url,
                    entity.properties.emails,
                    (self_user_id == user_id) or (self_user_id is None))

    @staticmethod
    def from_conv_part_data(conv_part_data, self_user_id):
        """Initialize from ClientConversationParticipantData.

        If self_user_id is None, assume this is the self user.
        """
        user_id = UserID(chat_id=conv_part_data.id_.chat_id,
                         gaia_id=conv_part_data.id_.gaia_id)
        return User(user_id, conv_part_data.fallback_name, None, None, [],
                    (self_user_id == user_id) or (self_user_id is None))


@asyncio.coroutine
def build_user_list(client, initial_data):
    """Return UserList from initial contact data and an additional request.

    The initial data contains the user's contacts, but there may be conversions
    containing users that are not in the contacts. This function takes care of
    requesting data for those users and constructing the UserList.
    """

    present_user_ids = {
        UserID(chat_id=entity.id_.chat_id, gaia_id=entity.id_.gaia_id)
        for entity in initial_data.entities + [initial_data.self_entity]
    }
    required_user_ids = set()
    for conv_state in initial_data.conversation_states:
        required_user_ids |= {
            UserID(chat_id=part.id_.chat_id, gaia_id=part.id_.gaia_id)
            for part in conv_state.conversation.participant_data
        }
    missing_user_ids = required_user_ids - present_user_ids
    if missing_user_ids:
        logger.debug('Need to request additional users: {}'
                     .format(missing_user_ids))
        try:
            response = yield from client.getentitybyid(
                [user_id.chat_id for user_id in missing_user_ids]
            )
            missing_entities = response.entities
        except exceptions.NetworkError as e:
            logger.warning('Failed to request missing users: {}'.format(e))
            missing_entities = []
        all_entities = initial_data.entities + missing_entities
        logger.debug('Received additional users: {}'.format(missing_entities))
    all_entities = initial_data.entities
    user_list = UserList(client, initial_data.self_entity,
                         all_entities,
                         initial_data.conversation_participants)
    return user_list


class UserList(object):

    """Collection of User instances."""

    def __init__(self, client, self_entity, entities, conv_parts):
        """Initialize the list of Users.

        Creates users from the given ClientEntity and
        ClientConversationParticipantData instances. The latter is used only as
        a fallback, because it doesn't include a real first_name.
        """
        self._client = client
        self._self_user = User.from_entity(self_entity, None)
        # {UserID: User}
        self._user_dict = {self._self_user.id_: self._self_user}
        # Add each entity as a new User.
        for entity in entities:
            user_ = User.from_entity(entity, self._self_user.id_)
            self._user_dict[user_.id_] = user_
        # Add each conversation participant as a new User if we didn't already
        # add them from an entity.
        for participant in conv_parts:
            self.add_user_from_conv_part(participant)
        logger.info('UserList initialized with {} user(s)'
                    .format(len(self._user_dict)))

        self._client.on_state_update.add_observer(self._on_state_update)

    def get_user(self, user_id):
        """Return a User by their UserID.

        Raises KeyError if the User is not available.
        """
        try:
            return self._user_dict[user_id]
        except KeyError:
            logger.warning('UserList returning unknown User for UserID {}'
                           .format(user_id))
            return User(user_id, DEFAULT_NAME, None, None, [], False)

    def get_all(self):
        """Returns all the users known"""
        return self._user_dict.values()

    def add_user_from_conv_part(self, conv_part):
        """Add new User from ClientConversationParticipantData"""
        user_ = User.from_conv_part_data(conv_part, self._self_user.id_)
        if user_.id_ not in self._user_dict:
            logging.warning('Adding fallback User: {}'.format(user_))
            self._user_dict[user_.id_] = user_
        return user_

    def _on_state_update(self, state_update):
        """Receive a ClientStateUpdate"""
        if state_update.client_conversation is not None:
            self._handle_client_conversation(state_update.client_conversation)

    def _handle_client_conversation(self, client_conversation):
        """Receive ClientConversation and update list of users"""
        for participant in client_conversation.participant_data:
            self.add_user_from_conv_part(participant)
