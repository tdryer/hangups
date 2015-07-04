from hangups import pblite2
from hangups.test import test_pblite2_pb2

def test_decode_no_fields():
    test_message = test_pblite2_pb2.TestMessage()
    pblite2.decode(test_message, [])
    assert test_message.test_int == 0
    assert test_message.embedded_message.test_int == 0
    assert len(test_message.test_int_list) == 0
    assert len(test_message.embedded_message_list) == 0

def test_decode_one_field():
    test_message = test_pblite2_pb2.TestMessage()
    pblite2.decode(test_message, [1])
    assert test_message.test_int == 1

def test_decode_extra_field():
    test_message = test_pblite2_pb2.TestMessage()
    pblite2.decode(test_message, [1, None, None, None, 10])
    assert test_message.test_int == 1

def test_decode_embedded_message():
    test_message = test_pblite2_pb2.TestMessage()
    pblite2.decode(test_message, [None, [1]])
    assert test_message.test_int == 0
    assert test_message.embedded_message.test_int == 1

def test_decode_repeated():
    test_message = test_pblite2_pb2.TestMessage()
    pblite2.decode(test_message, [None, None, [1, 2, 3]])
    assert test_message.test_int_list == [1, 2, 3]

def test_encode_no_fields():
    test_message = test_pblite2_pb2.TestMessage()
    assert pblite2.encode(test_message) == []

def test_encode_embedded_message():
    test_message = test_pblite2_pb2.TestMessage()
    test_message.test_int = 1
    test_message.embedded_message.test_int = 2
    test_message.test_int_list.extend([3, 4])
    test_message.embedded_message_list.add()
    test_message.embedded_message_list[0].test_int = 5
    assert pblite2.encode(test_message) == [1, [2], [3, 4], [[5]]]

# TODO not useful
def test_encode_empty_embedded_message():
    test_message = test_pblite2_pb2.TestMessage()
    test_message.test_int = 1
    assert pblite2.encode(test_message) == [1]

def test_encode_serialize_default_value():
    # Field is always serialized when it is set, even when set to the default
    # value.
    test_message = test_pblite2_pb2.TestMessage()
    test_message.test_int = 0
    assert pblite2.encode(test_message) == [0]

def test_encode_required_field():
    # Required fields are always serialized to the default value.
    test_message = test_pblite2_pb2.RequiredMessage()
    # TODO
    #assert pblite2.encode(test_message) == [0]

