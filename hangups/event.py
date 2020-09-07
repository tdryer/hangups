"""Simple event observer system supporting asyncio.

Observers must be removed to avoid memory leaks.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


class Event:
    """An event that can notify subscribers with arguments when fired.

    Args:
        name (str): Name of the new event.
    """

    def __init__(self, name):
        self._name = str(name)
        self._observers = []

    def add_observer(self, callback):
        """Add an observer to this event.

        Args:
            callback: A function or coroutine callback to call when the event
                is fired.

        Raises:
            ValueError: If the callback has already been added.
        """
        if callback in self._observers:
            raise ValueError('{} is already an observer of {}'
                             .format(callback, self))
        self._observers.append(callback)

    def remove_observer(self, callback):
        """Remove an observer from this event.

        Args:
            callback: A function or coroutine callback to remove from this
                event.

        Raises:
            ValueError: If the callback is not an observer of this event.
        """
        if callback not in self._observers:
            raise ValueError('{} is not an observer of {}'
                             .format(callback, self))
        self._observers.remove(callback)

    async def fire(self, *args, **kwargs):
        """Fire this event, calling all observers with the same arguments."""
        logger.debug('Fired {}'.format(self))
        for observer in self._observers:
            gen = observer(*args, **kwargs)
            if asyncio.iscoroutinefunction(observer):
                await gen

    def __repr__(self):
        return 'Event(\'{}\')'.format(self._name)
