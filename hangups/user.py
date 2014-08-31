"""User objects."""

import logging
from tornado import gen
from collections import namedtuple

logger = logging.getLogger(__name__)
DEFAULT_NAME = 'Unknown'

UserID = namedtuple('UserID', ['chat_id', 'gaia_id'])


class User(object):

    """A chat user.

    Handles full_name or first_name being None by creating an approximate
    first_name from the full_name, or setting both to DEFAULT_NAME.
    """

    def __init__(self, chat_id, full_name, first_name, is_self):
        """Initialize a User."""
        self.id_ = chat_id
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


# TODO: This class isn't really being used yet.
class UserList(object):

    """Allows querying known chat users."""

    def __init__(self, client):
        self._client = client
        self._users = dict(client.initial_users)
        self._self_user_id = client.self_user_id
        logger.info('UserList initialized with {} user(s)'
                    .format(len(self._users)))

    def get_self_id(self):
        """Return UserID of the logged in user."""
        return self._self_user_id

    @gen.coroutine
    def get_self_user(self):
        """Return User who is logged in."""
        yield self.get_users([self._self_user_id])[0]

    @gen.coroutine
    def get_user(self, user_id):
        """Wrapper for get_users for getting a single user."""
        users = yield self.get_users([user_id])
        return users[0]

    @gen.coroutine
    def get_users(self, user_id_list):
        """Gets Users by a list of IDs.

        Returns a dict user_id -> User.

        Until we can find all users reliably, this method will return dummy
        users rather than raising an exception when a user can't be found.
        """
        # Request any new user IDs if necessary
        unknown_user_ids = set(user_id_list) - set(self._users.keys())
        if unknown_user_ids:
            logger.info('Need to request users: {}'.format(unknown_user_ids))
            yield self._request_users(unknown_user_ids)

        # Return Users and add dummies for Users we couldn't find.
        return {user_id: (self._users[user_id] if user_id in self._users
                          else self._make_dummy_user(user_id))
                for user_id in user_id_list}

    def _make_dummy_user(self, user_id):
        """Return a dummy User and add it to the list."""
        logger.info('Creating dummy user for {}'.format(user_id))
        user = User(user_id, 'UNKNOWN', 'UNKNOWN',
                    (user_id == self._self_user_id))
        self._users[user_id] = user
        return user

    @gen.coroutine
    def _request_users(self, user_id_list):
        """Make request for a list of users by ID."""
        res = yield self._client.getentitybyid([user_id.chat_id for user_id
                                                in user_id_list])
        for entity in res['entity']:
            try:
                user = _parse_user_entity(entity)
            except ValueError as e:
                logger.warning('Failed to parse user entity: {}: {}'
                               .format(e, entity))
            else:
                user_id = UserID(chat_id=user['chat_id'],
                                 gaia_id=user['gaia_id'])
                self._users[user_id] = User(user_id, user['full_name'],
                                            user['first_name'],
                                            (user_id == self._self_user_id))


def _parse_user_entity(entity):
    """Parse entities returned from the getentitybyid endpoint.

    Raises ValueError if the entity cannot be parsed.
    """
    # TODO: Parse this with a schema.
    # Known entity types:
    # GAIA: regular user
    # INVALID: entity does not exist
    entity_type = entity.get('entity_type', None)
    if entity_type != 'GAIA':
        raise ValueError('Cannot parse entity with entity type {}'
                         .format(entity_type))
    try:
        chat_id = entity['id']['chat_id']
        gaia_id = entity['id']['gaia_id']
    except KeyError:
        raise ValueError('Cannot determine entity ID')
    properties = entity.get('properties', {})
    return {
        'chat_id': chat_id,
        'gaia_id': gaia_id,
        'first_name': properties.get('first_name', 'UNKNOWN'),
        'full_name': properties.get('display_name', 'UNKNOWN'),
    }
