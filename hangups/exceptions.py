"""Exceptions used by hangups."""


class HangupsError(Exception):
    """An ambiguous error occurred."""


class NetworkError(HangupsError):
    """A network error occurred."""


class ConversationTypeError(HangupsError):
    """An action was performed on a conversation that doesn't support it."""
