"""Tests for the user module"""


import hangups.user
import hangups.hangouts_pb2


USER_ID = hangups.user.UserID(1, 1)


def test_default_type_detection_empty_0():
    # missing names
    user = hangups.user.User(
        USER_ID,
        full_name='',
        first_name='',
        photo_url='',
        canonical_email='',
        emails=[],
        is_self=False,
    )

    assert user.full_name == hangups.user.DEFAULT_NAME
    assert user.first_name == hangups.user.DEFAULT_NAME
    assert user.name_type == hangups.user.NameType.DEFAULT


def test_default_type_detection_empty_1():
    # missing names
    user = hangups.user.User(
        USER_ID,
        full_name=None,
        first_name=None,
        photo_url='',
        canonical_email='',
        emails=[],
        is_self=False,
    )

    assert user.full_name == hangups.user.DEFAULT_NAME
    assert user.first_name == hangups.user.DEFAULT_NAME
    assert user.name_type == hangups.user.NameType.DEFAULT


def test_default_type_detection_from_conv_part_data():
    # default user in 201904
    conv_part_data = hangups.hangouts_pb2.ConversationParticipantData(
        id=hangups.hangouts_pb2.ParticipantId(
            chat_id='1',
            gaia_id='1'
        ),
        fallback_name='unknown',
        invitation_status=hangups.hangouts_pb2.INVITATION_STATUS_ACCEPTED,
        participant_type=hangups.hangouts_pb2.PARTICIPANT_TYPE_GAIA,
        new_invitation_status=hangups.hangouts_pb2.INVITATION_STATUS_ACCEPTED,
    )

    user = hangups.user.User.from_conv_part_data(
        conv_part_data=conv_part_data,
        self_user_id=USER_ID
    )

    assert user.full_name == hangups.user.DEFAULT_NAME
    assert user.first_name == hangups.user.DEFAULT_NAME
    assert user.name_type == hangups.user.NameType.DEFAULT


def test_real_type():
    # regular name
    user = hangups.user.User(
        USER_ID,
        full_name='Joe Doe',
        first_name='Joe',
        photo_url='',
        canonical_email='',
        emails=[],
        is_self=False,
    )

    assert user.full_name == 'Joe Doe'
    assert user.first_name == 'Joe'
    assert user.name_type == hangups.user.NameType.REAL


def test_real_type_from_conv_part_data():
    conv_part_data = hangups.hangouts_pb2.ConversationParticipantData(
        id=hangups.hangouts_pb2.ParticipantId(
            chat_id='1',
            gaia_id='1'
        ),
        fallback_name='Joe Doe',
        invitation_status=hangups.hangouts_pb2.INVITATION_STATUS_ACCEPTED,
        participant_type=hangups.hangouts_pb2.PARTICIPANT_TYPE_GAIA,
        new_invitation_status=hangups.hangouts_pb2.INVITATION_STATUS_ACCEPTED,
    )

    user = hangups.user.User.from_conv_part_data(
        conv_part_data=conv_part_data,
        self_user_id=USER_ID
    )

    assert user.full_name == 'Joe Doe'
    assert user.first_name == 'Joe'
    assert user.name_type == hangups.user.NameType.REAL
