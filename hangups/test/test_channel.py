"""Tests for channel data parsing."""

# pylint: disable=protected-access

import pytest

from hangups import channel


@pytest.mark.parametrize('input_,expected', [
    (b'79\n[[0,["c","98803CAAD92268E8","",8]\n]\n,'
     b'[1,[{"gsid":"7tCoFHumSL-IT6BHpCaxLA"}]]\n]\n',
     ('98803CAAD92268E8', '7tCoFHumSL-IT6BHpCaxLA')),
])
def test_parse_sid_response(input_, expected):
    assert channel._parse_sid_response(input_) == expected


@pytest.mark.parametrize('input_,expected', [
    # '€' is 3 bytes in UTF-8.
    ('€€'.encode()[:6], '€€'),
    ('€€'.encode()[:5], '€'),
    ('€€'.encode()[:4], '€'),
    ('€€'.encode()[:3], '€'),
    ('€€'.encode()[:2], ''),
    ('€€'.encode()[:1], ''),
    ('€€'.encode()[:0], ''),
])
def test_best_effort_decode(input_, expected):
    assert channel._best_effort_decode(input_) == expected


def test_simple():
    p = channel.ChunkParser()
    assert list(p.get_chunks('10\n01234567893\nabc'.encode())) == [
        '0123456789',
        'abc',
    ]


def test_truncated_message():
    p = channel.ChunkParser()
    assert list(p.get_chunks('12\n012345678'.encode())) == []


def test_junk_before_length():
    p = channel.ChunkParser()
    assert list(p.get_chunks('junk4\nfail'.encode())) == []


def test_truncated_length():
    p = channel.ChunkParser()
    assert list(p.get_chunks('13'.encode())) == []


def test_malformed_length():
    p = channel.ChunkParser()
    # TODO: could detect errors like these with some extra work
    assert list(p.get_chunks('11\n0123456789\n5e\n"abc"'.encode())) == [
        '0123456789\n'
    ]


def test_incremental():
    p = channel.ChunkParser()
    assert list(p.get_chunks(''.encode())) == []
    assert list(p.get_chunks('5'.encode())) == []
    assert list(p.get_chunks('\n'.encode())) == []
    assert list(p.get_chunks('abc'.encode())) == []
    assert list(p.get_chunks('de'.encode())) == ['abcde']
    assert list(p.get_chunks(''.encode())) == []


def test_unicode():
    p = channel.ChunkParser()
    # smile is actually 2 code units
    assert list(p.get_chunks('3\na😀'.encode())) == ['a😀']


def test_split_characters():
    p = channel.ChunkParser()
    assert list(p.get_chunks(b'1\n\xe2\x82')) == []
    assert list(p.get_chunks(b'\xac')) == ['€']
