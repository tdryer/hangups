"""Tests for long poll message parsing."""

from hangups import parsers


def test_simple():
    p = parsers.PushDataParser()
    assert list(p.get_submissions('10\n01234567893\nabc')) == [
        '0123456789',
        'abc',
    ]


def test_truncated_message():
    p = parsers.PushDataParser()
    assert list(p.get_submissions('12\n012345678')) == []


def test_truncated_length():
    p = parsers.PushDataParser()
    assert list(p.get_submissions('13')) == []


def test_malformed_length():
    p = parsers.PushDataParser()
    # TODO: could detect errors like these with some extra work
    assert list(p.get_submissions('11\n0123456789\n5e\n"abc"')) == [
        '0123456789\n'
    ]


def test_incremental():
    p = parsers.PushDataParser()
    assert list(p.get_submissions('')) == []
    assert list(p.get_submissions('5')) == []
    assert list(p.get_submissions('\n')) == []
    assert list(p.get_submissions('abc')) == []
    assert list(p.get_submissions('de')) == ['abcde']
    assert list(p.get_submissions('')) == []


def test_unicode():
    p = parsers.PushDataParser()
    # smile is actually 2 code units
    assert list(p.get_submissions('3\na😀')) == ['a😀']
