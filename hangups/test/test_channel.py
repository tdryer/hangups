import pytest

from hangups import channel


# [(test, (SID, header_client, gsessionid))]
@pytest.mark.parametrize('input_,expected', [

    (
        b'300\n[[0,["c","A5CFCC4C27DB0410",,8]\n]\n,[1,["b"]\n]\n,[2,["c",[\'D7482B41270E1674\',["me","tdryer.ca@gmail.com",0]\n]]\n]\n,[3,["c",[\'D7482B41270E1674\',["cfj","tdryer.ca@gmail.com/AChromeExtensionwC7D1A6A7"]\n]]\n]\n,[4,["c",[\'D7482B41270E1674\',["ei","bmhFHNqd3hs","1402515430",0,28800000,57600000,28800000]\n]]\n]\n]\n',
        ('A5CFCC4C27DB0410', 'AChromeExtensionwC7D1A6A7', 'bmhFHNqd3hs')
    ),
    (
        b'280\n[[0,["c","3083767439152ACA",,8]\n]\n,[1,["b"]\n]\n,[2,["c",[\'D7482B41270E1674\',["cfj","tdryer.ca@gmail.com/AChromeExtensionwC7D1A6A7"]\n]]\n]\n,[3,["c",[\'D7482B41270E1674\',["nt",[]\n]\n]]\n]\n,[4,["c",[\'D7482B41270E1674\',["ei","8nO9mnnJwRQ","1402515430",0,28800000,57600000,28800000]\n]]\n]\n]\n',
        ('3083767439152ACA', 'AChromeExtensionwC7D1A6A7', '8nO9mnnJwRQ'),
    ),

    (
        b'280\n[[0,["c","ABF01B7416DF5E48",,8]\n]\n,[1,["b"]\n]\n,[2,["c",[\'9F97F7B0270E1674\',["cfj","tdryer.ca@gmail.com/AChromeExtensionwA41D7046"]\n]]\n]\n,[3,["c",[\'9F97F7B0270E1674\',["nt",[]\n]\n]]\n]\n,[4,["c",[\'9F97F7B0270E1674\',["ei","PDG7IRJf69g","1402515430",0,28800000,57600000,28800000]\n]]\n]\n]\n',
        ('ABF01B7416DF5E48', 'AChromeExtensionwA41D7046', 'PDG7IRJf69g'),
    ),
])
def test_parse_sid_response(input_, expected):
    assert channel._parse_sid_response(input_) == expected
