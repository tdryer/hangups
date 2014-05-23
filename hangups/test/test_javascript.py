"""Tests for the JavaScript parser."""

import pytest

from hangups import javascript


@pytest.mark.parametrize('input_,expected', [
    # simple types
    ('12', 12),
    ('null', None),
    ('true', True),
    ('false', False),
    # floats
    ('123.0', 123.0),
    ('-123.0', -123.0),
    ('.123', 0.123),
    ('-.123', -0.123),
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
    ('"😀"', '😀'),
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
    """Test loading JS from a string."""
    assert javascript.loads(input_) == expected


def test_loads_lex_error():
    """Test loading invalid JS that fails lexing."""
    with pytest.raises(ValueError):
        javascript.loads('{""": 1}')


def test_loads_parse_error():
    """Test loading invalid JS that fails parsing."""
    with pytest.raises(ValueError):
        javascript.loads('{"foo": 1}}')
