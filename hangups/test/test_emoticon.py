import pytest

from hangups.ui.emoticon import _replace_words, replace_emoticons


@pytest.mark.parametrize('replacements,string,result', [
    ({}, '', ''),
    ({}, ' ', ' '),
    ({}, '\n', '\n'),
    ({}, 'foo', 'foo'),
    ({'foo': 'bar'}, 'foo', 'bar'),
    ({'foo': 'bar'}, 'foofoo', 'foofoo'),
    ({'foo': 'bar'}, 'foo foo', 'bar bar'),
    ({'foo': 'bar'}, 'foo ', 'bar '),
    ({'foo': 'bar'}, 'foo\nfoo', 'bar\nbar'),
    ({'foo': 'bar'}, 'foo\n', 'bar\n'),
])
def test_replace_words(replacements, string, result):
    assert _replace_words(replacements, string) == result


@pytest.mark.parametrize('string,result', [
    ('this is a test:)', 'this is a test:)'),
    ('this is a test :)', 'this is a test \U0000263a'),
    ('this is a test\n:)', 'this is a test\n\U0000263a'),
])
def test_replace_emoticons(string, result):
    assert replace_emoticons(string) == result
