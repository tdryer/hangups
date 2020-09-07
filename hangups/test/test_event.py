"""Tests for the simple observer implementation."""

import asyncio
import pytest

from hangups import event


def coroutine_test(coro):
    """Decorator to create a coroutine that starts and stops its own loop."""
    def wrapper(*args, **kwargs):
        future = coro(*args, **kwargs)
        loop = asyncio.new_event_loop()
        loop.run_until_complete(future)
    return wrapper


@coroutine_test
async def test_event():
    e = event.Event('MyEvent')
    res = []

    async def a(arg):
        res.append('a' + arg)

    async def b(arg):
        res.append('b' + arg)
    e.add_observer(a)
    await e.fire('1')
    e.add_observer(b)
    await e.fire('2')
    e.remove_observer(a)
    await e.fire('3')
    e.remove_observer(b)
    await e.fire('4')
    assert res == ['a1', 'a2', 'b2', 'b3']


@coroutine_test
async def test_function_observer():
    e = event.Event('MyEvent')
    res = []
    e.add_observer(lambda arg: res.append('a' + arg))
    await e.fire('1')
    assert res == ['a1']


@coroutine_test
async def test_coroutine_observer():
    e = event.Event('MyEvent')
    res = []

    async def a(arg):
        res.append('a' + arg)
    e.add_observer(a)
    await e.fire('1')
    assert res == ['a1']


def test_already_added():
    def a(arg):
        print('A: got {}'.format(arg))
    e = event.Event('MyEvent')
    e.add_observer(a)
    with pytest.raises(ValueError):
        e.add_observer(a)


def test_remove_nonexistant():
    e = event.Event('MyEvent')
    with pytest.raises(ValueError):
        e.remove_observer(lambda a: print('A: got {}'.format(a)))
