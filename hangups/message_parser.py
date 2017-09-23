"""Parser for message formatting markup."""

import re

from reparser import Parser, Token, MatchGroup

from hangups import hangouts_pb2


# Common regex patterns
boundary_chars = r'\s`!()\[\]{{}};:\'".,<>?«»“”‘’*_~='
b_left = r'(?:(?<=[' + boundary_chars + r'])|(?<=^))'  # Lookbehind
b_right = r'(?:(?=[' + boundary_chars + r'])|(?=$))'  # Lookahead

# Regex patterns used by token definitions
markdown_start = b_left + r'(?<!\\){tag}(?!\s)(?!{tag})'
markdown_end = r'(?<!{tag})(?<!\s)(?<!\\){tag}' + b_right
markdown_link = r'(?<!\\)\[(?P<link>.+?)\]\((?P<url>.+?)\)'
html_start = r'(?i)<{tag}>'
html_end = r'(?i)</{tag}>'
html_link = r'(?i)<a\s+href=[\'"](?P<url>.+?)[\'"]\s*>(?P<link>.+?)</a>'
html_img = r'(?i)<img\s+src=[\'"](?P<url>.+?)[\'"]\s*/?>'
html_newline = r'(?i)<br\s*/?>'
newline = r'\n|\r\n'

# Based on URL regex pattern by John Gruber
# (https://gist.github.com/gruber/8891611)
_DOMAINS = (
    'com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|'
    'name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|'
    'au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|'
    'cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|'
    'dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|'
    'gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|'
    'is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|'
    'lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|'
    'my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|'
    'pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|'
    'sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|'
    'tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw')
_BALANCED_PARENS = r'\([^\s()]*?\([^\s()]+\)[^\s()]*?\)'
AUTO_LINK = (
    (r'(?i)\b('
     r'(?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:domains)/)'
     r'(?:[^\s()<>{}\[\]]+|balanced_parens|\([^\s]+?\))+'
     r'(?:balanced_parens|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|'
     r'(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:domains)\b/?(?!@)))')
    .replace('domains', _DOMAINS).replace('balanced_parens', _BALANCED_PARENS))
# cleanup
del _DOMAINS
del _BALANCED_PARENS

# Precompiled regex for matching protocol part of URL
url_proto_regex = re.compile(r'(?i)^[a-z][\w-]+:/{1,3}')

# Precompiled regex for removing backslash before escaped Markdown tags
markdown_unescape_regex = re.compile(r'\\([*_~=`\[])')


def markdown(tag):
    """Return start and end regex pattern sequences for simple Markdown tag."""
    return (markdown_start.format(tag=tag), markdown_end.format(tag=tag))


def html(tag):
    """Return sequence of start and end regex patterns for simple HTML tag"""
    return (html_start.format(tag=tag), html_end.format(tag=tag))


def url_complete(url):
    """If URL doesn't start with protocol, prepend it with http://"""
    return url if url_proto_regex.search(url) else 'http://' + url


class Tokens:
    """Groups of tokens to be used by ChatMessageParser"""
    basic = [
        Token('link', AUTO_LINK, link_target=MatchGroup('start',
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
    def __init__(self, tokens=Tokens.markdown + Tokens.html + Tokens.basic):
        # we add default tokens here.
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
