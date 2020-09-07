"""Parser for message formatting markup."""

import re

from reparser import Parser, Token, MatchGroup

from hangups import hangouts_pb2


# Common regex patterns
BOUNDARY_CHARS = r'\s`!()\[\]{{}};:\'".,<>?«»“”‘’*_~='
B_LEFT = r'(?:(?<=[' + BOUNDARY_CHARS + r'])|(?<=^))'  # Lookbehind
B_RIGHT = r'(?:(?=[' + BOUNDARY_CHARS + r'])|(?=$))'   # Lookahead

# Regex patterns used by token definitions
MARKDOWN_END = r'(?<![\s\\]){tag}' + B_RIGHT
MARKDOWN_START = B_LEFT + r'(?<!\\){tag}(?!\s)(?!{tag})(?=.+%s)' % MARKDOWN_END
markdown_link = r'(?<!\\)\[(?P<link>.+?)\]\((?P<url>.+?)\)'
HTML_END = r'(?i)</{tag}>'
HTML_START = r'(?i)<{tag}>(?=.+%s)' % HTML_END
html_link = r'(?i)<a\s+href=[\'"](?P<url>.+?)[\'"]\s*>(?P<link>.+?)</a>'
html_img = r'(?i)<img\s+src=[\'"](?P<url>.+?)[\'"]\s*/?>'
html_newline = r'(?i)<br\s*/?>'
newline = r'\n|\r\n'

# supported minimal url pattern:
#   - http://domain.tld
#   - https://domain.tld
#   - sub.domain.tld
#   - domain.tld/
# custom ports are supported, however there is no port range check
# parens in the path are matched balanced only:
#   - me.you/(yeah) is matched as me.you/(yeah)
#   - me.you/(nope)) is matched as me.you/(nope)
#   this is useful when parsing a wrapped url: (inner.link/path_with_(parens))
auto_link = r"""
\b
(
    (?:
        (?:
            https?://
            |
            (?<!@)[a-zA-Z0-9\-]{1,63}\.
            |
            (?=\S+/)
        )
        (?:[a-zA-Z0-9\-]{1,63}\.)+
        [a-zA-Z\-]{2,63}
        |
        (?:
            https?://
            |
            (?=[\d.]+/)
        )
        \d{1,3}(?:\.\d{1,3}){3}
    )
    (?::\d+)?
    \b(?!@)
    (?:
        /
        (?:
            \(
                [^\s/()]*
                \(
                    [^\s/()]+
                \)
                [^\s/()]*
            \)
            |
            \(
                [^\s/()]+
            \)
            |
            [^\s/(){};:!<>«»“”"'‘’`´]*
        )*
    )*
)
""".replace(' ', '').replace('\n', '')

# Precompiled regex for matching protocol part of URL
url_proto_regex = re.compile(r'(?i)^[a-z][\w-]+:/{1,3}')

# Precompiled regex for removing backslash before escaped Markdown tags
markdown_unescape_regex = re.compile(r'\\([*_~=`\[])')


def markdown(tag):
    """Return start and end regex pattern sequences for simple Markdown tag."""
    return (MARKDOWN_START.format(tag=tag), MARKDOWN_END.format(tag=tag))


def html(tag):
    """Return sequence of start and end regex patterns for simple HTML tag"""
    return (HTML_START.format(tag=tag), HTML_END.format(tag=tag))


def url_complete(url):
    """If URL doesn't start with protocol, prepend it with http://"""
    return url if url_proto_regex.search(url) else 'http://' + url


class Tokens:
    """Groups of tokens to be used by ChatMessageParser"""
    basic = [
        Token('link', auto_link, link_target=MatchGroup('start',
                                                        func=url_complete)),
        Token('br', newline, text='\n',
              segment_type=hangouts_pb2.SEGMENT_TYPE_LINE_BREAK)
    ]

    markdown = [
        Token('md_bi1', *markdown(r'\*\*\*'), is_bold=True, is_italic=True),
        Token('md_bi2', *markdown(r'___'), is_bold=True, is_italic=True),
        Token('md_b1', *markdown(r'\*\*'), is_bold=True),
        Token('md_b2', *markdown(r'__'), is_bold=True),
        Token('md_i1', *markdown(r'\*'), is_italic=True),
        Token('md_i2', *markdown(r'_'), is_italic=True),
        Token('md_pre3', *markdown(r'```'), skip=True),
        Token('md_pre2', *markdown(r'``'), skip=True),
        Token('md_pre1', *markdown(r'`'), skip=True),
        Token('md_s', *markdown(r'~~'), is_strikethrough=True),
        Token('md_u', *markdown(r'=='), is_underline=True),
        Token('md_link', markdown_link, text=MatchGroup('link'),
              link_target=MatchGroup('url', func=url_complete))
    ]

    html = [
        Token('html_b1', *html(r'b'), is_bold=True),
        Token('html_b2', *html(r'strong'), is_bold=True),
        Token('html_i1', *html(r'i'), is_italic=True),
        Token('html_i2', *html(r'em'), is_italic=True),
        Token('html_s1', *html(r's'), is_strikethrough=True),
        Token('html_s2', *html(r'strike'), is_strikethrough=True),
        Token('html_s3', *html(r'del'), is_strikethrough=True),
        Token('html_u1', *html(r'u'), is_underline=True),
        Token('html_u2', *html(r'ins'), is_underline=True),
        Token('html_u3', *html(r'mark'), is_underline=True),
        Token('html_pre', *html(r'pre'), skip=True),
        Token('html_link', html_link, text=MatchGroup('link'),
              link_target=MatchGroup('url', func=url_complete)),
        Token('html_img', html_img, text=MatchGroup('url'),
              link_target=MatchGroup('url', func=url_complete)),
        Token('html_br', html_newline, text='\n',
              segment_type=hangouts_pb2.SEGMENT_TYPE_LINE_BREAK)
    ]


class ChatMessageParser(Parser):
    """Chat message parser"""
    def __init__(self, tokens=None):
        # we add default tokens here.
        if not tokens:
            tokens = Tokens.markdown + Tokens.html + Tokens.basic
        # pylint:disable=useless-super-delegation
        super().__init__(tokens)

    def preprocess(self, text):
        """Preprocess text before parsing"""
        # Replace two consecutive spaces with space and non-breakable space
        # (this is how original Hangouts client does it to preserve multiple
        # spaces)
        return text.replace('  ', ' \xa0')

    def postprocess(self, text):
        """Postprocess text after parsing"""
        # Remove backslash before escaped Markdown tags
        return markdown_unescape_regex.sub(r'\1', text)
