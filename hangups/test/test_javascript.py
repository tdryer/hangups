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
    ('[["foo","bar"],,,1232]', [['foo', 'bar'], None, None, 1232]),
    ('"😀"', '😀'),
    # string escape sequences
    (r'"\b"', '\b'),
    (r'"\t"', '\t'),
    (r'"\n"', '\n'),
    (r'"\v"', '\v'),
    (r'"\f"', '\f'),
    (r'"\r"', '\r'),
    (r'"\\"', '\\'),
    (r'"\""', '"'),
    (r"'\''", "'"),
    (r'"a\u003db"', 'a=b'),
    (r'"\ud83d\ude1c"', '😜'),
    (r'"a\ud83d\ude1cb"', 'a😜b'),
    (r'"a\ud83d\ude1c\ud83d\ude1cb"', 'a😜😜b'),
    # invalid string escape sequences
    (r'"\a"', 'a'),
    (r'"a\uzzzzb"', 'ab'),
    (r'"\ud83d\uffff"', ''),
    # objects
    ('{ }', {}),
    ('{"foo": 1}', {'foo': 1}),
    ('{"foo": 1, "bar": 2}', {'foo': 1, 'bar': 2}),
    ('{foo: 1}', {'foo': 1}),
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
