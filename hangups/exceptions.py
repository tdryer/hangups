"""Exceptions used by hangups."""


class HangupsError(Exception):
    """An ambiguous error occurred."""


class NetworkError(HangupsError):
    """A network error occurred."""
