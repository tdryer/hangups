"""Tests for long poll message parsing."""

import pytest
from io import BytesIO

from hangups import longpoll


def test_loads_simple():
    s = b'13\n"0123456789"\n5\n"abc"'
    assert longpoll.loads(BytesIO(s)) == ["0123456789", "abc"]


def test_loads_truncated_message():
    s = b'13\n"012345678'
    with pytest.raises(ValueError) as e:
        longpoll.loads(BytesIO(s))
    assert str(e.value) == "Unexpected EOF while parsing message"


def test_loads_truncated_length():
    s = b'13'
    with pytest.raises(ValueError) as e:
        longpoll.loads(BytesIO(s))
    assert str(e.value) == "Unexpected EOF while parsing message length"


def test_loads_malformed_length():
    s = b'13\n"0123456789"\n5e\n"abc"'
    with pytest.raises(ValueError) as e:
        longpoll.loads(BytesIO(s))
    assert str(e.value) == "Malformed message length"
