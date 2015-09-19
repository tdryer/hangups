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
            '~~strike~~ [Google](www.google.com)')
    expected = [('Test ', {}),
                ('bold ', {'is_bold': True}),
                ('bolditalic', {'is_bold': True, 'is_italic': True}),
                (' bold', {'is_bold': True}),
                (' ', {}),
                ('italic', {'is_italic': True}),
                (' not_italic_not ', {}),
                ('strike', {'is_strikethrough': True}),
                (' ', {}),
                ('Google', {'link_target': 'http://www.google.com'})]
    assert expected == parse_text(text)


def test_parse_html():
    text = (
        'Test <b>bold <i>bolditalic</i> bold</b> <em>italic</em> '
        '<del>strike</del><br><a href="google.com">Google</a>'
        '<img src=\'https://upload.wikimedia.org/wikipedia/en/8/80/'
        'Wikipedia-logo-v2.svg\'>'
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
          'Wikipedia-logo-v2.svg'})
    ]
    assert expected == parse_text(text)
