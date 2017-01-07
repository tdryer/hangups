High-Level APIs
===============

.. module:: hangups

This page documents high-level APIs that expose some of hangups' low-level
functionality in a simpler way.

Conversation List
-----------------

.. autocofunction:: hangups.build_user_conversation_list

.. autoclass:: hangups.ConversationList
    :members:

Conversation
------------

.. autoclass:: hangups.conversation.Conversation
    :members:

Conversation Event
------------------

.. autoclass:: hangups.ConversationEvent
    :members:

.. autoclass:: hangups.ChatMessageEvent
    :members:

.. autoclass:: hangups.OTREvent
    :members:

.. autoclass:: hangups.RenameEvent
    :members:

.. autoclass:: hangups.MembershipChangeEvent
    :members:

.. autoclass:: hangups.HangoutEvent
    :members:

.. autoclass:: hangups.GroupLinkSharingModificationEvent
    :members:

Chat Message Segment
--------------------

.. autoclass:: hangups.ChatMessageSegment
    :members:

Notifications
-------------

.. autoclass:: hangups.parsers.TypingStatusMessage

.. autoclass:: hangups.parsers.WatermarkNotification

User List
---------

.. autoclass:: hangups.UserList
    :members:

User
----

.. autoclass:: hangups.user.NameType
    :members:
    :undoc-members:
    :inherited-members:

.. autoclass:: hangups.user.UserID

.. autoclass:: hangups.user.User
    :members:
