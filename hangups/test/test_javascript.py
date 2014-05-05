"""Tests for the JavaScript parser."""

import pytest

from hangups import javascript


@pytest.mark.parametrize('input_,expected', [
    # simple types
    ('12', 12),
    ('null', None),
    ('true', True),
    ('false', False),
    # lists
    ('[ ]', []),
    ('[12]', [12]),
    ('[1, null, true, false, []]', [1, None, True, False, []]),
    ('[1,,2]', [1, None, 2]),
    ('[1,,,2]', [1, None, None, 2]),
    ('[,1]', [None, 1]),
    ('[,,1]', [None, None, 1]),
    ('[1,]', [1]),
    ('[1,,]', [1, None]),
    # strings
    ('\'\'', ''),
    ('""', ''),
    ('\'f\'', 'f'),
    ('"f"', 'f'),
    ('\'foo\'', 'foo'),
    ('"foo"', 'foo'),
    (r'"\u003d"', '='),
    ('[["foo","bar"],,,1232]', [['foo', 'bar'], None, None, 1232]),
    # objects
    ('{ }', {}),
    ('{"foo": 1}', {'foo': 1}),
    ('{"foo": 1, "bar": 2}', {'foo': 1, 'bar': 2}),
    ('{foo: 1}', {'foo': 1}),
    ('"\\n"', '\n'),
    ('"\\\\"', '\\'),
    ('"\\""', '"'),
    ("'\\''", "'"),
    (r'"[\"foo\"]"', '["foo"]'),

])
def test_loads(input_, expected):
    """Test loading Javascript from a string."""
    assert javascript.loads(input_) == expected
