"""Simple event observer system supporting asyncio.

Observers must be removed to avoid memory leaks.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class Event(object):

    """Event that tracks a list of observer callbacks to notify when fired."""

    def __init__(self, name):
        """Create a new Event with a name."""
        self._name = str(name)
        self._observers = []

    def add_observer(self, callback):
        """Add an event observer callback.

        callback may be a coroutine or function.

        Raises ValueError if the callback has already been added.
        """
        if callback in self._observers:
            raise ValueError('{} is already an observer of {}'
                             .format(callback, self))
        self._observers.append(callback)

    def remove_observer(self, callback):
        """Remove an event observer callback.

        Raises ValueError if the callback is not an event observer.
        """
        if callback not in self._observers:
            raise ValueError('{} is not an observer of {}'
                             .format(callback, self))
        self._observers.remove(callback)

    @asyncio.coroutine
    def fire(self, *args, **kwargs):
        """Call all observer callbacks with the same arguments."""
        logger.debug('Fired {}'.format(self))
        for observer in self._observers:
            gen = observer(*args, **kwargs)
            if asyncio.iscoroutinefunction(observer):
                yield from gen

    def __repr__(self):
        return 'Event(\'{}\')'.format(self._name)
