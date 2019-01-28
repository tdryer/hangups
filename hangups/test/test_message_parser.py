"""Tests for ReParser-based message parser"""

from hangups import message_parser, hangouts_pb2


def parse_text(text):
    parser = message_parser.ChatMessageParser()
    return [(s.text, s.params) for s in parser.parse(text)]


def test_parse_linebreaks():
    text = 'line1\nline2\r\nline3'
    expected = [('line1', {}),
                ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
                ('line2', {}),
                ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
                ('line3', {})]
    assert expected == parse_text(text)


def test_parse_auto_link_minimal():
    text = (
        'http://domain.tld\n'
        'https://domain.tld\n'
        'sub.domain.tld\n'
        'domain.tld/\n'
        '1.1.1.1/\n'
    )
    expected = [
        ('http://domain.tld', {'link_target': 'http://domain.tld'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('https://domain.tld', {'link_target': 'https://domain.tld'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('sub.domain.tld', {'link_target': 'http://sub.domain.tld'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('domain.tld/', {'link_target': 'http://domain.tld/'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('1.1.1.1/', {'link_target': 'http://1.1.1.1/'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
    ]
    assert expected == parse_text(text)


def test_parse_auto_link_port():
    text = (
        'http://domain.tld:8080\n'
        'https://domain.tld:8080\n'
        'sub.domain.tld:8080\n'
        'domain.tld:8080/\n'
    )
    expected = [
        ('http://domain.tld:8080',
         {'link_target': 'http://domain.tld:8080'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('https://domain.tld:8080',
         {'link_target': 'https://domain.tld:8080'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('sub.domain.tld:8080',
         {'link_target': 'http://sub.domain.tld:8080'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('domain.tld:8080/',
         {'link_target': 'http://domain.tld:8080/'}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
    ]
    assert expected == parse_text(text)


def test_parse_auto_link_parens():
    text = (
        'pre (https://domain.tld) post\n'
        'pre (inner https://domain.tld inner) post\n'
        'pre (inner (https://domain.tld) inner) post\n'
        'pre https://domain.tld/path(inner) post\n'
        'pre (https://domain.tld/path(inner)) post\n'
    )
    expected = [
        ('pre (', {}),
        ('https://domain.tld', {'link_target': 'https://domain.tld'}),
        (') post', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('pre (inner ', {}),
        ('https://domain.tld', {'link_target': 'https://domain.tld'}),
        (' inner) post', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('pre (inner (', {}),
        ('https://domain.tld', {'link_target': 'https://domain.tld'}),
        (') inner) post', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('pre ', {}),
        ('https://domain.tld/path(inner)',
         {'link_target': 'https://domain.tld/path(inner)'}),
        (' post', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('pre (', {}),
        ('https://domain.tld/path(inner)',
         {'link_target': 'https://domain.tld/path(inner)'}),
        (') post', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
    ]
    assert expected == parse_text(text)


def test_parse_auto_link_email():
    text = (
        'name@domain.tld\n'
        'name.other.name@domain.tld\n'
        'name.other.name@sub.domain.tld\n'
    )
    expected = [
        ('name@domain.tld', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('name.other.name@domain.tld', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('name.other.name@sub.domain.tld', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
    ]
    assert expected == parse_text(text)


def test_parse_auto_link_invalid():
    text = (
        'hangups:hangups\n'
        'http://tld\n'
        'http://tld/path\n'
        'version 3.5.11\n'
    )
    expected = [
        ('hangups:hangups', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('http://tld', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('http://tld/path', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('version 3.5.11', {}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
    ]
    assert expected == parse_text(text)


def test_parse_autolinks():
    text = ('www.google.com google.com/maps '
            '(https://en.wikipedia.org/wiki/Parenthesis_(disambiguation))')
    expected = [
        ('www.google.com', {'link_target': 'http://www.google.com'}),
        (' ', {}),
        ('google.com/maps', {'link_target': 'http://google.com/maps'}),
        (' (', {}),
        ('https://en.wikipedia.org/wiki/Parenthesis_(disambiguation)',
         {'link_target':
          'https://en.wikipedia.org/wiki/Parenthesis_(disambiguation)'}),
        (')', {})
    ]
    assert expected == parse_text(text)


def test_parse_markdown():
    text = ('Test **bold *bolditalic* bold** _italic_ not_italic_not '
            '~~strike~~ [Google](www.google.com)'
            r'**`_bold not italic_`**')
    expected = [('Test ', {}),
                ('bold ', {'is_bold': True}),
                ('bolditalic', {'is_bold': True, 'is_italic': True}),
                (' bold', {'is_bold': True}),
                (' ', {}),
                ('italic', {'is_italic': True}),
                (' not_italic_not ', {}),
                ('strike', {'is_strikethrough': True}),
                (' ', {}),
                ('Google', {'link_target': 'http://www.google.com'}),
                ('_bold not italic_', {'is_bold': True})]
    assert expected == parse_text(text)

    text = '*first opened **second opened _third opened __fourth opened'
    assert [(text, {})] == parse_text(text)


def test_parse_html():
    text = (
        'Test <b>bold <i>bolditalic</i> bold</b> <em>italic</em> '
        '<del>strike</del><br><a href="google.com">Google</a>'
        '<img src=\'https://upload.wikimedia.org/wikipedia/en/8/80/'
        'Wikipedia-logo-v2.svg\'><i>default'
    )
    expected = [
        ('Test ', {}),
        ('bold ', {'is_bold': True}),
        ('bolditalic', {'is_bold': True, 'is_italic': True}),
        (' bold', {'is_bold': True}),
        (' ', {}),
        ('italic', {'is_italic': True}),
        (' ', {}),
        ('strike', {'is_strikethrough': True}),
        ('\n', {'segment_type': hangouts_pb2.SEGMENT_TYPE_LINE_BREAK}),
        ('Google', {'link_target': 'http://google.com'}),
        ('https://upload.wikimedia.org/wikipedia/en/8/80/'
         'Wikipedia-logo-v2.svg',
         {'link_target':
          'https://upload.wikimedia.org/wikipedia/en/8/80/'
          'Wikipedia-logo-v2.svg'}),
        ('<i>default', {}),
    ]
    assert expected == parse_text(text)
