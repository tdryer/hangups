"""Tests for the simple observer implementation."""

import asyncio
import pytest

from hangups import event

def coroutine_test(f):
    """Decorator to create a coroutine that starts and stops its own loop."""
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(future)
    return wrapper


@coroutine_test
def test_event():
    e = event.Event('MyEvent')
    res = []
    a = asyncio.coroutine(lambda arg: res.append('a' + arg))
    b = asyncio.coroutine(lambda arg: res.append('b' + arg))
    e.add_observer(a)
    yield from e.fire('1')
    e.add_observer(b)
    yield from e.fire('2')
    e.remove_observer(a)
    yield from e.fire('3')
    e.remove_observer(b)
    yield from e.fire('4')
    assert res == ['a1', 'a2', 'b2', 'b3']


@coroutine_test
def test_function_observer():
    e = event.Event('MyEvent')
    res = []
    a = lambda arg: res.append('a' + arg)
    e.add_observer(a)
    yield from e.fire('1')
    assert res == ['a1']


@coroutine_test
def test_coroutine_observer():
    e = event.Event('MyEvent')
    res = []
    a = asyncio.coroutine(lambda arg: res.append('a' + arg))
    e.add_observer(a)
    yield from e.fire('1')
    assert res == ['a1']


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
