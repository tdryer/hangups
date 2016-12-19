Low-Level APIs
==============

This page documents the low-level APIs for using hangups.

Authentication
--------------

.. autoclass:: hangups.CredentialsPrompt
    :members:

.. autoclass:: hangups.RefreshTokenCache
    :members:

.. autofunction:: hangups.get_auth

.. autofunction:: hangups.get_auth_stdin

Client
------

.. autoclass:: hangups.Client
    :members:

Exceptions
----------

.. autoexception:: hangups.GoogleAuthError

.. autoexception:: hangups.HangupsError

.. autoexception:: hangups.NetworkError

Event
-----

.. autoclass:: hangups.event.Event
    :members:
