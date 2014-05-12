"""Tests for long poll message parsing."""

from hangups import longpoll


def test_simple():
    s = '10\n01234567893\nabc'
    p = longpoll.parse_push_data()
    p.send(None)
    assert p.send(s) == "0123456789"
    assert next(p) == "abc"
    assert next(p) == None


def test_truncated_message():
    s = '12\n012345678'
    p = longpoll.parse_push_data()
    p.send(None)
    assert p.send(s) == None


def test_truncated_length():
    s = '13'
    p = longpoll.parse_push_data()
    p.send(None)
    assert p.send(s) == None


def test_malformed_length():
    s = '11\n0123456789\n5e\n"abc"'
    p = longpoll.parse_push_data()
    p.send(None)
    assert p.send(s) == '0123456789\n'
    # TODO: could detect errors like these with some extra work
    assert next(p) == None


def test_incremental():
    p = longpoll.parse_push_data()
    p.send(None)
    assert p.send('5') == None
    assert p.send('\n') == None
    assert p.send('abc') == None
    assert p.send('de') == 'abcde'
    assert next(p) == None


def test_unicode():
    s = '3\na😀' # smile is actually 2 code units
    p = longpoll.parse_push_data()
    p.send(None)
    assert p.send(s) == "a😀"
    assert next(p) == None
