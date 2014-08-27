"""Tests for hangups.pblite."""

import enum
import pytest
import types

from hangups import pblite


##############################################################################
# Fixtures
##############################################################################

class Colour(enum.Enum):
    RED = 1
    BLUE = 2


field = pblite.Field()
optional_field = pblite.Field(is_optional=True)
enum_field = pblite.EnumField(Colour)
repeated_field = pblite.RepeatedField(pblite.Field())
optional_repeated_field = pblite.RepeatedField(pblite.Field(),
                                               is_optional=True)
message = pblite.Message(
    ('item', pblite.Field()),
    (None, pblite.Field()),
    ('count', pblite.Field(is_optional=True)),
)


##############################################################################
# Tests
##############################################################################

def test_field():
    assert field.parse("test") == "test"


def test_field_none():
    with pytest.raises(ValueError) as e:
        field.parse(None)
    assert e.value.args[0] == 'Field is not optional'


def test_optional_field_none():
    assert optional_field.parse(None) == None


def test_enum_field():
    assert enum_field.parse(2) == Colour.BLUE


def test_enum_field_invalid():
    with pytest.raises(ValueError) as e:
        enum_field.parse(None)
    assert e.value.args[0] == 'None is not a valid Colour'


def test_repeated_field():
    assert repeated_field.parse([1, 2, 3]) == [1, 2, 3]


def test_repeated_field_item_error():
    with pytest.raises(ValueError) as e:
        repeated_field.parse([1, None, 3])
    assert e.value.args[0] == 'RepeatedField item: Field is not optional'


def test_repeated_field_none():
    with pytest.raises(ValueError) as e:
        repeated_field.parse(None)
    assert e.value.args[0] == 'RepeatedField is not optional'


def test_repeated_field_not_list():
    with pytest.raises(ValueError) as e:
        repeated_field.parse(123)
    assert e.value.args[0] == ('RepeatedField expected list but got '
                               '<class \'int\'>')


def test_optional_repeated_field_none():
    assert optional_repeated_field.parse(None) == None


def test_message():
    assert (message.parse(['rose', None, 1]).__dict__ ==
            types.SimpleNamespace(item='rose', count=1).__dict__)


def test_message_extra_field():
    assert (message.parse(['rose', None, 1, 100]).__dict__ ==
            types.SimpleNamespace(item='rose', count=1).__dict__)


def test_message_missing_optional_field():
    assert (message.parse(['rose', None]).__dict__ ==
            types.SimpleNamespace(item='rose', count=None).__dict__)


def test_message_missing_field():
    with pytest.raises(ValueError) as e:
        message.parse([])
    assert e.value.args[0] == 'Message field \'item\': Field is not optional'


def test_message_not_list():
    with pytest.raises(ValueError) as e:
        message.parse(123)
    assert e.value.args[0] == ('Message expected list but got '
                               '<class \'int\'>')
