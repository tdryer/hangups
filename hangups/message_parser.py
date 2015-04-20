import re

from reparser import Parser, Token, MatchGroup
from hangups.schemas import SegmentType


# Common regex patterns
boundary_chars = r'\s`!()\[\]{{}};:\'".,<>?«»“”‘’'
b_left = r'(?:(?<=[' + boundary_chars + r'])|(?<=^))' # Lookbehind
b_right = r'(?:(?=[' + boundary_chars + r'])|(?=$))' # Lookahead

# Regex patterns used by token definitions
markdown = b_left + r'(?P<start>{tag})(?!{tag})(?P<text>(?:\S.+?\S|\S+))(?<!{tag})(?P<end>{tag})' + b_right
markdown_link = r'(?P<start>\[)(?P<text>.+?)\]\((?P<url>.+?)(?P<end>\))'
html = r'(?i)(?P<start><{tag}>)(?P<text>.+?)(?P<end></{tag}>)'
html_link = r'(?i)(?P<start><a href=[\'"](?P<url>.+?)[\'"]>)(?P<text>.+?)(?P<end></a>)'
html_img = r'(?i)(?P<text><img src=[\'"](?P<url>.+?)[\'"](\s*/)?>)'
html_newline = r'(?i)(?P<text><br(\s*/)?>)'
newline = r'(?P<text>\n|\r\n)'

# Based on URL regex pattern by John Gruber (http://gist.github.com/gruber/249502)
auto_link = (r'(?i)\b(?P<text>'
             r'(?:[a-z][\w-]+:/{1,3}|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)'
             r'(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+'
             r'(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’]))')

url_proto_re = re.compile(r'(?i)^[a-z][\w-]+:/{1,3}')
url_complete = lambda u: u if url_proto_re.search(u) else 'http://' + u

class Tokens:
    """Groups of tokens to be used by ChatMessageParser"""
    basic = [
        Token(auto_link, final=True, link_target=MatchGroup('text', func=url_complete)),
        Token(newline, text='\n', final=True, segment_type=SegmentType.LINE_BREAK)
    ]

    markdown = [
        Token(markdown.format(tag=r'\*\*\*'), is_bold=True, is_italic=True),
        Token(markdown.format(tag=r'___'), is_bold=True, is_italic=True),
        Token(markdown.format(tag=r'\*\*'), is_bold=True),
        Token(markdown.format(tag=r'__'), is_bold=True),
        Token(markdown.format(tag=r'\*'), is_italic=True),
        Token(markdown.format(tag=r'_'), is_italic=True),
        Token(markdown.format(tag=r'~~'), is_strikethrough=True),
        Token(markdown.format(tag=r'=='), is_underline=True),
        Token(markdown_link, final=True, link_target=MatchGroup('url', func=url_complete))
    ]

    html = [
        Token(html.format(tag=r'b'), is_bold=True),
        Token(html.format(tag=r'strong'), is_bold=True),
        Token(html.format(tag=r'i'), is_italic=True),
        Token(html.format(tag=r'em'), is_italic=True),
        Token(html.format(tag=r's'), is_strikethrough=True),
        Token(html.format(tag=r'strike'), is_strikethrough=True),
        Token(html.format(tag=r'del'), is_strikethrough=True),
        Token(html.format(tag=r'u'), is_underline=True),
        Token(html.format(tag=r'ins'), is_underline=True),
        Token(html.format(tag=r'mark'), is_underline=True),
        Token(html_link, final=True, link_target=MatchGroup('url', func=url_complete)),
        Token(html_img, text=MatchGroup('url', func=url_complete), final=True,
              link_target=MatchGroup('url', func=url_complete)),
        Token(html_newline, text='\n', final=True, segment_type=SegmentType.LINE_BREAK)
    ]


class ChatMessageParser(Parser):
    """Chat message parser"""
    def __init__(self, tokens=Tokens.markdown + Tokens.html + Tokens.basic):
        super().__init__(tokens)

    def preprocess(self, text):
        """Preprocess text before parsing"""
        # Replace two consecutive spaces with space and non-breakable space
        # (this is how original Hangouts client does it to preserve multiple spaces)
        return text.replace('  ', ' \xa0')
