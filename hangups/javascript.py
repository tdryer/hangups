"""Parser for a subset of JavaScript written with purplex.

Parses a broader subset of JavaScript than just JSON, needed for parsing some
API responses. This is only as complete as necessary to parse the responses
we're getting.
"""

import logging
import purplex

logger = logging.getLogger(__name__)


def loads(string):
    """Parse simple JavaScript types from string into Python types.

    Raises ValueError if parsing fails.
    """
    try:
        return _PARSER.parse(string)
    except purplex.exception.PurplexError as e:
        raise ValueError('Failed to load JavaScript: {}'.format(e))


_ESCAPES = {
    'b': '\b',
    't': '\t',
    'n': '\n',
    'v': '\v',
    'f': '\f',
    'r': '\r',
    '"': '"',
    "'": "'",
    '\\': '\\',
    # Unicode escapes are a special case:
    'u': '',
}


def _unescape_string(s):
    """Unescape JavaScript escape sequences."""
    chars = list(s)
    unescaped_chars = []
    while len(chars) > 0:
        c = chars.pop(0)
        if c != '\\':
            unescaped_chars.append(c)
        else:
            try:
                c = chars.pop(0)
            except IndexError:
                raise ValueError('Reached end of string literal '
                                 'prematurely: {}'.format(s))
            if c == 'u':
                # One character can be formed from multiple contiguous \u
                # escape sequences.
                char_hex = ''
                while True:
                    try:
                        char_hex += ''.join([chars.pop(0) for _ in range(4)])
                    except IndexError:
                        raise ValueError('Reached end of string literal '
                                         'prematurely: {}'.format(s))
                    if len(chars) > 1 and ''.join(chars[0:2]) == r'\u':
                        chars.pop(0)
                        chars.pop(0)
                    else:
                        break
                try:
                    char = bytes.fromhex(char_hex).decode('utf-16be')
                except (ValueError, UnicodeDecodeError) as e:
                    logger.warning('Failed to decode unicode escape: {}'
                                   .format(e))
                    char = ''
                unescaped_chars.extend(char)
            else:
                try:
                    unescaped_chars.append(_ESCAPES[c])
                except KeyError:
                    # Mimic browser engines by ignoring the backslash if it
                    # forms an invalid escape sequence.
                    logger.warning('Ignoring invalid escape sequence: \\{}'
                                   .format(c))
                    unescaped_chars.append(c)
    return "".join(unescaped_chars)


class JavaScriptLexer(purplex.Lexer):
    """Lexer for a subset of JavaScript."""
    # TODO: Negative integers
    INTEGER = purplex.TokenDef(r'\d+')
    FLOAT = purplex.TokenDef(r'[-+]?\d*[.]\d+')

    NULL = purplex.TokenDef(r'null')
    TRUE = purplex.TokenDef(r'true')
    FALSE = purplex.TokenDef(r'false')

    LIST_START = purplex.TokenDef(r'\[')
    LIST_END = purplex.TokenDef(r'\]')
    OBJECT_START = purplex.TokenDef(r'\{')
    OBJECT_END = purplex.TokenDef(r'\}')
    COMMA = purplex.TokenDef(r',')
    COLON = purplex.TokenDef(r':')

    STRING = purplex.TokenDef(
        '(\'(([^\\\\\'])|(\\\\.))*?\')|("(([^\\\\"])|(\\\\.))*?")'
    )
    # TODO more unquoted keys are allowed
    KEY = purplex.TokenDef(r'[a-zA-Z0-9_$]+')

    WHITESPACE = purplex.TokenDef(r'[\s\n]+', ignore=True)


class JavaScriptParser(purplex.Parser):
    """Parser for a subset of JavaScript."""

    # pylint: disable=C0111,R0201,W0613,R0913
    LEXER = JavaScriptLexer
    START = 'e'
    PRECEDENCE = ()

    @purplex.attach('listitems : e')
    def listitems_1(self, child):
        return [child]

    @purplex.attach('listitems : e COMMA listitems')
    def listitems_2(self, child, comma, rest_of_list):
        return [child] + rest_of_list

    @purplex.attach('listitems : COMMA listitems')
    def listitems_3(self, comma, rest_of_list):
        return [None] + rest_of_list

    @purplex.attach('listitems : ')
    def listitems_4(self):
        return []

    @purplex.attach('e : LIST_START listitems LIST_END')
    def list(self, *children):
        return children[1]

    @purplex.attach('objectkey : e')
    @purplex.attach('objectkey : KEY')
    def objectkey(self, key):
        # TODO not everything can be a key
        return key

    @purplex.attach('objectitems : ')
    def objectitems_1(self):
        return {}

    @purplex.attach('objectitems : objectkey COLON e')
    def objectitems_2(self, key, colon, val):
        return {key: val}

    @purplex.attach('objectitems : objectkey COLON e COMMA objectitems')
    def objectitems_3(self, key, colon, val, comma, otheritems):
        d = dict(otheritems)
        d[key] = val
        return d

    @purplex.attach('e : OBJECT_START objectitems OBJECT_END')
    def object(self, start, objectitems, end):
        return objectitems

    @purplex.attach('e : INTEGER')
    def number(self, num):
        return int(num)

    @purplex.attach('e : FLOAT')
    def float_number(self, num):
        return float(num)

    @purplex.attach('e : NULL')
    def null(self, t):
        return None

    @purplex.attach('e : TRUE')
    def true(self, t):
        return True

    @purplex.attach('e : FALSE')
    def false(self, t):
        return False

    @purplex.attach('e : STRING')
    def string(self, s):
        return _unescape_string(s[1:-1])


# instantiate the parser at module-load time for better performance
_PARSER = JavaScriptParser()
