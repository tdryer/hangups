"""Hangouts emoticon to emoji converter."""


def replace_emoticons(string):
    """Replace emoticon words in string with corresponding emoji."""
    return _replace_words(HANGOUTS_EMOTICONS_TO_EMOJI, string)


def _replace_words(replacements, string):
    """Replace words with corresponding values in replacements dict.

    Words must be separated by spaces or newlines.
    """
    output_lines = []
    for line in string.split('\n'):
        output_words = []
        for word in line.split(' '):
            new_word = replacements.get(word, word)
            output_words.append(new_word)
        output_lines.append(output_words)
    return '\n'.join(' '.join(output_words) for output_words in output_lines)


# Emoticon conversions extracted from hangouts.google.com
HANGOUTS_EMOTICONS_TO_EMOJI = {
    ':)': '\U0000263a',
    ':-)': '\U0000263a',
    '<3': '\U00002764',
    '-<@%': '\U0001f41d',
    ':(|)': '\U0001f435',
    ':(:)': '\U0001f437',
    '(y)': '\U0001f44d',
    '(Y)': '\U0001f44d',
    '(n)': '\U0001f44e',
    '(N)': '\U0001f44e',
    '(]:{': '\U0001f473',
    '<\\3': '\U0001f494',
    '</3': '\U0001f494',
    '~@~': '\U0001f4a9',
    ':D': '\U0001f600',
    ':-D': '\U0001f600',
    '^_^': '\U0001f601',
    ":''D": '\U0001f602',
    '=D': '\U0001f604',
    '^_^;;': '\U0001f605',
    'O:)': '\U0001f607',
    'O=)': '\U0001f607',
    'O:-)': '\U0001f607',
    '}:-)': '\U0001f608',
    '}=)': '\U0001f608',
    '}:)': '\U0001f608',
    ';-)': '\U0001f609',
    ';)': '\U0001f609',
    '=)': '\U0001f60a',
    'B-)': '\U0001f60e',
    ':,': '\U0001f60f',
    ':-,': '\U0001f60f',
    '=|': '\U0001f610',
    ':-|': '\U0001f610',
    ':|': '\U0001f610',
    '-_-': '\U0001f611',
    'o_o;': '\U0001f613',
    'u_u': '\U0001f614',
    '=\\': '\U0001f615',
    ':-\\': '\U0001f615',
    ':-/': '\U0001f615',
    ':\\': '\U0001f615',
    ':/': '\U0001f615',
    '=/': '\U0001f615',
    ':-s': '\U0001f616',
    ':-S': '\U0001f616',
    ':S': '\U0001f616',
    ':s': '\U0001f616',
    ':*': '\U0001f617',
    ':-*': '\U0001f617',
    ';-*': '\U0001f618',
    ';*': '\U0001f618',
    '=*': '\U0001f61a',
    ':-P': '\U0001f61b',
    ':p': '\U0001f61b',
    ':-p': '\U0001f61b',
    ':P': '\U0001f61b',
    '=P': '\U0001f61b',
    '=p': '\U0001f61b',
    ';p': '\U0001f61c',
    ';P': '\U0001f61c',
    ';-p': '\U0001f61c',
    ';-P': '\U0001f61c',
    ':(': '\U0001f61e',
    '=(': '\U0001f61e',
    ':-(': '\U0001f61e',
    '>.<': '\U0001f621',
    '>=(': '\U0001f621',
    '>:(': '\U0001f621',
    '>:-(': '\U0001f621',
    ';_;': '\U0001f622',
    "='(": '\U0001f622',
    'T_T': '\U0001f622',
    ":'(": '\U0001f622',
    '>_<': '\U0001f623',
    'D:': '\U0001f626',
    ":''(": '\U0001f62d',
    ':o': '\U0001f62e',
    ':-o': '\U0001f62e',
    ':-O': '\U0001f62e',
    '=O': '\U0001f62e',
    ':O': '\U0001f62e',
    'o.o': '\U0001f62e',
    '=o': '\U0001f62e',
    'O.O': '\U0001f632',
    'X-O': '\U0001f635',
    'x_x': '\U0001f635',
    'X(': '\U0001f635',
    'X-o': '\U0001f635',
    'X-(': '\U0001f635',
    ':X)': '\U0001f638',
    '(=^..^=)': '\U0001f638',
    ':3': '\U0001f638',
    '=^_^=': '\U0001f638',
    '(=^.^=)': '\U0001f638',
    '!:)': '\U0001f643',
    '!:-)': '\U0001f643',
    '>:(X': '\U0001f645',
    'o/': '\U0001f64b',
    '\\o': '\U0001f64b',
    ':)X': '\U0001f917',
    '>:D<': '\U0001f917',
    ':-)X': '\U0001f917',
    '\\m/': '\U0001f918',
    'V.v.V': '\U0001f980',
}
