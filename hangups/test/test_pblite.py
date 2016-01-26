"""Tests for pblite format decoder and encoder."""

from hangups import pblite
from hangups.test import test_pblite_pb2


###############################################################################
# pblite.decode
###############################################################################

def test_decode():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        1,
        [3, 4],
        'foo',
        ['bar', 'baz'],
        1,
        [2, 3],
        [1],
        [[2], [3]],
        'AA==',
        ['AAE=', 'AAEC'],
    ])
    assert message == test_pblite_pb2.TestMessage(
        test_int=1,
        test_repeated_int=[3, 4],
        test_string='foo',
        test_repeated_string=['bar', 'baz'],
        test_enum=test_pblite_pb2.TestMessage.TEST_1,
        test_repeated_enum=[test_pblite_pb2.TestMessage.TEST_2,
                            test_pblite_pb2.TestMessage.TEST_3],
        test_embedded_message=test_pblite_pb2.TestMessage.EmbeddedMessage(
            test_embedded_int=1,
        ),
        test_repeated_embedded_message=[
            test_pblite_pb2.TestMessage.EmbeddedMessage(
                test_embedded_int=2,
            ),
            test_pblite_pb2.TestMessage.EmbeddedMessage(
                test_embedded_int=3,
            ),
        ],
        test_bytes=b'\x00',
        test_repeated_bytes=[b'\x00\x01', b'\x00\x01\x02'],
    )


def test_decode_unserialized_fields():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None,
        None,
        'foo',
    ])
    assert message == test_pblite_pb2.TestMessage(
        test_string='foo',
    )


def test_decode_unknown_field():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [None] * 99 + [1])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_unknown_enum():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None,
        None,
        None,
        None,
        99,
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_unknown_repeated_enum():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None,
        None,
        None,
        None,
        None,
        [1, 99],
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_scalar_wrong_type():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        'foo',
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_repeated_scalar_wrong_type():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None,
        [1, 'foo', 2]
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_message_wrong_type():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None,
        None,
        None,
        None,
        None,
        None,
        1,
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_repeated_message_wrong_type():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        [1],
    ])
    assert message == test_pblite_pb2.TestMessage(
        test_repeated_embedded_message=[
            test_pblite_pb2.TestMessage.EmbeddedMessage(),
        ],
    )


def test_decode_bytes_wrong_type():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None, None, None, None, None, None, None, None, 1,
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_bytes_invalid_value():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None, None, None, None, None, None, None, None, 'A?==',
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_repeated_bytes_wrong_type():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None, None, None, None, None, None, None, None, None, [1],
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_repeated_bytes_invalid_value():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        None, None, None, None, None, None, None, None, None, ['A?=='],
    ])
    assert message == test_pblite_pb2.TestMessage()


def test_decode_ignore_first_item():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        'ignored',
        1,
        [3, 4],
    ], ignore_first_item=True)
    assert message == test_pblite_pb2.TestMessage(
        test_int=1,
        test_repeated_int=[3, 4],
    )


def test_decode_dict():
    message = test_pblite_pb2.TestMessage()
    pblite.decode(message, [
        1,
        {
            '7': [2],
        },
    ])
    assert message == test_pblite_pb2.TestMessage(
        test_int=1,
        test_embedded_message=test_pblite_pb2.TestMessage.EmbeddedMessage(
            test_embedded_int=2,
        ),
    )
