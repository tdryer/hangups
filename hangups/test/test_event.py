"""Tests for the simple observer implementation."""

import pytest

from hangups import event


def test_event():
    e = event.Event('MyEvent')
    res = []
    a = lambda arg: res.append('a' + arg)
    b = lambda arg: res.append('b' + arg)
    e.add_observer(a)
    e.fire('1')
    e.add_observer(b)
    e.fire('2')
    e.remove_observer(a)
    e.fire('3')
    e.remove_observer(b)
    e.fire('4')
    assert res == ['a1', 'a2', 'b2', 'b3']


def test_already_added():
    e = event.Event('MyEvent')
    a = lambda a: print('A: got {}'.format(a))
    e.add_observer(a)
    with pytest.raises(ValueError):
        e.add_observer(a)


def test_remove_nonexistant():
    e = event.Event('MyEvent')
    a = lambda a: print('A: got {}'.format(a))
    with pytest.raises(ValueError):
        e.remove_observer(a)
