Low-Level APIs
==============

.. module:: hangups

This page documents the low-level APIs for using hangups.

Authentication
--------------

.. autofunction:: hangups.get_auth_stdin

.. autofunction:: hangups.get_auth

.. autoclass:: hangups.CredentialsPrompt
    :members:

.. autoclass:: hangups.RefreshTokenCache
    :members:

Client
------

.. autoclass:: hangups.Client
    :members:

.. autoclass:: hangups.client.UploadedImage

Exceptions
----------

.. autoexception:: hangups.GoogleAuthError

.. autoexception:: hangups.HangupsError

.. autoexception:: hangups.NetworkError

Event
-----

.. autoclass:: hangups.event.Event
    :members:
