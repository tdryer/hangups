import pytest

from hangups import channel


# [(test, (SID, email, header_client, gsessionid))]
@pytest.mark.parametrize('input_,expected', [

    (
        b'300\n[[0,["c","A5CFCC4C27DB0410",,8]\n]\n,[1,["b"]\n]\n,[2,["c",[\'D7482B41270E1674\',["me","tdryer.ca@gmail.com",0]\n]]\n]\n,[3,["c",[\'D7482B41270E1674\',["cfj","tdryer.ca@gmail.com/AChromeExtensionwC7D1A6A7"]\n]]\n]\n,[4,["c",[\'D7482B41270E1674\',["ei","bmhFHNqd3hs","1402515430",0,28800000,57600000,28800000]\n]]\n]\n]\n',
        ('A5CFCC4C27DB0410', 'tdryer.ca@gmail.com',
         'AChromeExtensionwC7D1A6A7', 'bmhFHNqd3hs')
    ),
    (
        b'280\n[[0,["c","3083767439152ACA",,8]\n]\n,[1,["b"]\n]\n,[2,["c",[\'D7482B41270E1674\',["cfj","tdryer.ca@gmail.com/AChromeExtensionwC7D1A6A7"]\n]]\n]\n,[3,["c",[\'D7482B41270E1674\',["nt",[]\n]\n]]\n]\n,[4,["c",[\'D7482B41270E1674\',["ei","8nO9mnnJwRQ","1402515430",0,28800000,57600000,28800000]\n]]\n]\n]\n',
        ('3083767439152ACA', 'tdryer.ca@gmail.com',
         'AChromeExtensionwC7D1A6A7', '8nO9mnnJwRQ'),
    ),

    (
        b'280\n[[0,["c","ABF01B7416DF5E48",,8]\n]\n,[1,["b"]\n]\n,[2,["c",[\'9F97F7B0270E1674\',["cfj","tdryer.ca@gmail.com/AChromeExtensionwA41D7046"]\n]]\n]\n,[3,["c",[\'9F97F7B0270E1674\',["nt",[]\n]\n]]\n]\n,[4,["c",[\'9F97F7B0270E1674\',["ei","PDG7IRJf69g","1402515430",0,28800000,57600000,28800000]\n]]\n]\n]\n',
        ('ABF01B7416DF5E48', 'tdryer.ca@gmail.com',
         'AChromeExtensionwA41D7046', 'PDG7IRJf69g'),
    ),
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
    p = channel.PushDataParser()
    assert list(p.get_submissions('10\n01234567893\nabc'.encode())) == [
        '0123456789',
        'abc',
    ]


def test_truncated_message():
    p = channel.PushDataParser()
    assert list(p.get_submissions('12\n012345678'.encode())) == []


def test_truncated_length():
    p = channel.PushDataParser()
    assert list(p.get_submissions('13'.encode())) == []


def test_malformed_length():
    p = channel.PushDataParser()
    # TODO: could detect errors like these with some extra work
    assert list(p.get_submissions('11\n0123456789\n5e\n"abc"'.encode())) == [
        '0123456789\n'
    ]


def test_incremental():
    p = channel.PushDataParser()
    assert list(p.get_submissions(''.encode())) == []
    assert list(p.get_submissions('5'.encode())) == []
    assert list(p.get_submissions('\n'.encode())) == []
    assert list(p.get_submissions('abc'.encode())) == []
    assert list(p.get_submissions('de'.encode())) == ['abcde']
    assert list(p.get_submissions(''.encode())) == []


def test_unicode():
    p = channel.PushDataParser()
    # smile is actually 2 code units
    assert list(p.get_submissions('3\na😀'.encode())) == ['a😀']


def test_split_characters():
    p = channel.PushDataParser()
    assert list(p.get_submissions(b'1\n\xe2\x82')) == []
    assert list(p.get_submissions(b'\xac')) == ['€']
