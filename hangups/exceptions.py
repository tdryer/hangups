"""Exceptions used by hangups."""


class HangupsError(Exception):
    """An ambiguous error occurred."""
    pass


class NetworkError(HangupsError):
    """A network error occurred."""
    pass
