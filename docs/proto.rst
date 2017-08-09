.. This file was automatically generated from hangups/hangouts.proto and should not be edited directly.

DoNotDisturbSetting
-------------------

The state of do-not-disturb mode. Not to be confused with DndSetting, which
is used to change the state of do-not-disturb mode.

============================ ====== ====== ======== =================================================================================================
Field                        Number Type   Label    Description                                                                                      
============================ ====== ====== ======== =================================================================================================
:code:`do_not_disturb`       1      bool   optional Whether do-not-disturb mode is enabled.                                                          
:code:`expiration_timestamp` 2      uint64 optional Timestamp when do-not-disturb mode expires.                                                      
:code:`version`              3      uint64 optional Timestamp when this setting was applied. Not present when this message comes from a notification.
============================ ====== ====== ======== =================================================================================================

NotificationSettings
--------------------

==================== ====== ====================== ======== ===========
Field                Number Type                   Label    Description
==================== ====== ====================== ======== ===========
:code:`dnd_settings` 1      `DoNotDisturbSetting`_ optional            
==================== ====== ====================== ======== ===========

ConversationId
--------------

Identifies a conversation.

========== ====== ====== ======== =====================================
Field      Number Type   Label    Description                          
========== ====== ====== ======== =====================================
:code:`id` 1      string optional Unique identifier for a conversation.
========== ====== ====== ======== =====================================

ParticipantId
-------------

Identifies a user.

=============== ====== ====== ======== ==============================================
Field           Number Type   Label    Description                                   
=============== ====== ====== ======== ==============================================
:code:`gaia_id` 1      string optional Unique identifier for a user's Google account.
:code:`chat_id` 2      string optional Seems to always be the same as gaia_id.       
=============== ====== ====== ======== ==============================================

DeviceStatus
------------

Indicates whether Hangouts is active (running in the foreground) on
different types of devices.

=============== ====== ==== ======== ======================================
Field           Number Type Label    Description                           
=============== ====== ==== ======== ======================================
:code:`mobile`  1      bool optional True if a mobile phone is active.     
:code:`desktop` 2      bool optional True if a desktop or laptop is active.
:code:`tablet`  3      bool optional True if a tablet is active.           
=============== ====== ==== ======== ======================================

LastSeen
--------

================================ ====== ====== ======== ===========
Field                            Number Type   Label    Description
================================ ====== ====== ======== ===========
:code:`last_seen_timestamp_usec` 1      uint64 optional            
:code:`usec_since_last_seen`     2      uint64 optional            
================================ ====== ====== ======== ===========

Presence
--------

===================== ====== =============== ======== ===========
Field                 Number Type            Label    Description
===================== ====== =============== ======== ===========
:code:`reachable`     1      bool            optional            
:code:`available`     2      bool            optional            
:code:`device_status` 6      `DeviceStatus`_ optional            
:code:`mood_message`  9      `MoodMessage`_  optional            
:code:`last_seen`     10     `LastSeen`_     optional            
===================== ====== =============== ======== ===========

PresenceResult
--------------

================ ====== ================ ======== ===========
Field            Number Type             Label    Description
================ ====== ================ ======== ===========
:code:`user_id`  1      `ParticipantId`_ optional            
:code:`presence` 2      `Presence`_      optional            
================ ====== ================ ======== ===========

ClientIdentifier
----------------

================= ====== ====== ======== ===============================
Field             Number Type   Label    Description                    
================= ====== ====== ======== ===============================
:code:`resource`  1      string optional (client_id in hangups).        
:code:`header_id` 2      string optional unknown (header_id in hangups).
================= ====== ====== ======== ===============================

ClientPresenceState
-------------------

================== ====== ========================== ======== ===========
Field              Number Type                       Label    Description
================== ====== ========================== ======== ===========
:code:`identifier` 1      `ClientIdentifier`_        optional            
:code:`state`      2      `ClientPresenceStateType`_ optional            
================== ====== ========================== ======== ===========

UserEventState
--------------

=========================== ====== ==================== ======== ===========
Field                       Number Type                 Label    Description
=========================== ====== ==================== ======== ===========
:code:`user_id`             1      `ParticipantId`_     optional            
:code:`client_generated_id` 2      string               optional            
:code:`notification_level`  3      `NotificationLevel`_ optional            
=========================== ====== ==================== ======== ===========

Formatting
----------

===================== ====== ==== ======== ===========
Field                 Number Type Label    Description
===================== ====== ==== ======== ===========
:code:`bold`          1      bool optional            
:code:`italic`        2      bool optional            
:code:`strikethrough` 3      bool optional            
:code:`underline`     4      bool optional            
===================== ====== ==== ======== ===========

LinkData
--------

=================== ====== ====== ======== ===========
Field               Number Type   Label    Description
=================== ====== ====== ======== ===========
:code:`link_target` 1      string optional            
=================== ====== ====== ======== ===========

Segment
-------

A segment of a message. Message are broken into segments that may be of
different types and have different formatting.

================== ====== ============== ======== ===========================================================================================
Field              Number Type           Label    Description                                                                                
================== ====== ============== ======== ===========================================================================================
:code:`type`       1      `SegmentType`_ required Note: This field is required because Hangouts for Chrome misbehaves if it isn't serialized.
:code:`text`       2      string         optional The segment text. For line breaks, may either be empty or contain new line character.      
:code:`formatting` 3      `Formatting`_  optional Formatting for this segment.                                                               
:code:`link_data`  4      `LinkData`_    optional Link data for this segment, if it is a link.                                               
================== ====== ============== ======== ===========================================================================================

PlusPhoto
---------

Google Plus photo that can be embedded in a chat message.

============================ ====== ====================== ======== =============================
Field                        Number Type                   Label    Description                  
============================ ====== ====================== ======== =============================
:code:`thumbnail`            1      `PlusPhoto.Thumbnail`_ optional Thumbnail.                   
:code:`owner_obfuscated_id`  2      string                 optional Owner obfuscated ID.         
:code:`album_id`             3      string                 optional Album ID.                    
:code:`photo_id`             4      string                 optional Photo ID.                    
:code:`url`                  6      string                 optional URL of full-sized image.     
:code:`original_content_url` 10     string                 optional URL of image thumbnail.      
:code:`media_type`           13     `PlusPhoto.MediaType`_ optional The media type.              
:code:`stream_id`            14     string                 repeated List of stream ID parameters.
============================ ====== ====================== ======== =============================

PlusPhoto.Thumbnail
-------------------

Metadata for displaying an image thumbnail.

================= ====== ====== ======== =========================================================================
Field             Number Type   Label    Description                                                              
================= ====== ====== ======== =========================================================================
:code:`url`       1      string optional URL to navigate to when thumbnail is selected (a Google Plus album page).
:code:`image_url` 4      string optional URL of thumbnail image.                                                  
:code:`width_px`  10     uint64 optional Image width in pixels.                                                   
:code:`height_px` 11     uint64 optional Image height in pixels.                                                  
================= ====== ====== ======== =========================================================================

PlusPhoto.MediaType
-------------------

Media type.

================================= ====== ===========
Name                              Number Description
================================= ====== ===========
:code:`MEDIA_TYPE_UNKNOWN`        0                 
:code:`MEDIA_TYPE_PHOTO`          1                 
:code:`MEDIA_TYPE_ANIMATED_PHOTO` 4                 
================================= ====== ===========

Place
-----

Place that can be embedded in a chat message via Google Maps.

============================ ====== ============ ======== ==================================================
Field                        Number Type         Label    Description                                       
============================ ====== ============ ======== ==================================================
:code:`url`                  1      string       optional Google Maps URL pointing to the place coordinates.
:code:`name`                 3      string       optional Name of the place.                                
:code:`address`              24     `EmbedItem`_ optional Address of the place.                             
:code:`geo`                  25     `EmbedItem`_ optional Geographic location of the place.                 
:code:`representative_image` 185    `EmbedItem`_ optional Representative image of the place (map with pin). 
============================ ====== ============ ======== ==================================================

EmbedItem
---------

An item of some type embedded in a chat message.

======================= ======== =========================== ======== ================================================================
Field                   Number   Type                        Label    Description                                                     
======================= ======== =========================== ======== ================================================================
:code:`type`            1        `ItemType`_                 repeated List of embedded item types in this message.                    
:code:`id`              2        string                      optional For photos this is not given, for maps, it's the URL of the map.
:code:`plus_photo`      27639957 `PlusPhoto`_                optional Embedded Google Plus photo.                                     
:code:`place`           35825640 `Place`_                    optional Embedded Google Map of a place.                                 
:code:`postal_address`  36003298 `EmbedItem.PostalAddress`_  optional Embedded postal address.                                        
:code:`geo_coordinates` 36736749 `EmbedItem.GeoCoordinates`_ optional Embedded geographical coordinates.                              
:code:`image`           40265033 `EmbedItem.Image`_          optional Embedded image.                                                 
======================= ======== =========================== ======== ================================================================

EmbedItem.PostalAddress
-----------------------

====================== ====== ====== ======== ===========
Field                  Number Type   Label    Description
====================== ====== ====== ======== ===========
:code:`street_address` 35     string optional            
====================== ====== ====== ======== ===========

EmbedItem.GeoCoordinates
------------------------

================= ====== ====== ======== ===========
Field             Number Type   Label    Description
================= ====== ====== ======== ===========
:code:`latitude`  36     double optional            
:code:`longitude` 37     double optional            
================= ====== ====== ======== ===========

EmbedItem.Image
---------------

=========== ====== ====== ======== ===========
Field       Number Type   Label    Description
=========== ====== ====== ======== ===========
:code:`url` 1      string optional            
=========== ====== ====== ======== ===========

Attachment
----------

An attachment for a chat message.

================== ====== ============ ======== ===========
Field              Number Type         Label    Description
================== ====== ============ ======== ===========
:code:`embed_item` 1      `EmbedItem`_ optional            
================== ====== ============ ======== ===========

MessageContent
--------------

Chat message content.

================== ====== ============= ======== ===========
Field              Number Type          Label    Description
================== ====== ============= ======== ===========
:code:`segment`    1      `Segment`_    repeated            
:code:`attachment` 2      `Attachment`_ repeated            
================== ====== ============= ======== ===========

EventAnnotation
---------------

Annotation that can be applied to a chat message event. The only known use
for this is "\me" actions supported by the Chrome client (type 4).

============= ====== ====== ======== =================================
Field         Number Type   Label    Description                      
============= ====== ====== ======== =================================
:code:`type`  1      int32  optional Annotation type.                 
:code:`value` 2      string optional Optional annotation string value.
============= ====== ====== ======== =================================

ChatMessage
-----------

A chat message in a conversation.

======================= ====== ================== ======== =========================================
Field                   Number Type               Label    Description                              
======================= ====== ================== ======== =========================================
:code:`annotation`      2      `EventAnnotation`_ repeated Optional annotation to attach to message.
:code:`message_content` 3      `MessageContent`_  optional The message's content.                   
======================= ====== ================== ======== =========================================

MembershipChange
----------------

======================= ====== ======================= ======== ===========
Field                   Number Type                    Label    Description
======================= ====== ======================= ======== ===========
:code:`type`            1      `MembershipChangeType`_ optional            
:code:`participant_ids` 3      `ParticipantId`_        repeated            
======================= ====== ======================= ======== ===========

ConversationRename
------------------

================ ====== ====== ======== ===========
Field            Number Type   Label    Description
================ ====== ====== ======== ===========
:code:`new_name` 1      string optional            
:code:`old_name` 2      string optional            
================ ====== ====== ======== ===========

HangoutEvent
------------

====================== ====== =================== ======== ===========
Field                  Number Type                Label    Description
====================== ====== =================== ======== ===========
:code:`event_type`     1      `HangoutEventType`_ optional            
:code:`participant_id` 2      `ParticipantId`_    repeated            
====================== ====== =================== ======== ===========

OTRModification
---------------

====================== ====== ===================== ======== ===========
Field                  Number Type                  Label    Description
====================== ====== ===================== ======== ===========
:code:`old_otr_status` 1      `OffTheRecordStatus`_ optional            
:code:`new_otr_status` 2      `OffTheRecordStatus`_ optional            
:code:`old_otr_toggle` 3      `OffTheRecordToggle`_ optional            
:code:`new_otr_toggle` 4      `OffTheRecordToggle`_ optional            
====================== ====== ===================== ======== ===========

HashModifier
------------

================= ====== ====== ======== ===========
Field             Number Type   Label    Description
================= ====== ====== ======== ===========
:code:`update_id` 1      string optional            
:code:`hash_diff` 2      uint64 optional            
:code:`version`   4      uint64 optional            
================= ====== ====== ======== ===========

Event
-----

Event that becomes part of a conversation's history.

======================================= ====== =============================== ======== =============================================
Field                                   Number Type                            Label    Description                                  
======================================= ====== =============================== ======== =============================================
:code:`conversation_id`                 1      `ConversationId`_               optional ID of the conversation this event belongs to.
:code:`sender_id`                       2      `ParticipantId`_                optional ID of the user that sent this event.         
:code:`timestamp`                       3      uint64                          optional Timestamp when the event occurred.           
:code:`self_event_state`                4      `UserEventState`_               optional                                              
:code:`source_type`                     6      `SourceType`_                   optional                                              
:code:`chat_message`                    7      `ChatMessage`_                  optional                                              
:code:`membership_change`               9      `MembershipChange`_             optional                                              
:code:`conversation_rename`             10     `ConversationRename`_           optional                                              
:code:`hangout_event`                   11     `HangoutEvent`_                 optional                                              
:code:`event_id`                        12     string                          optional Unique ID for the event.                     
:code:`expiration_timestamp`            13     uint64                          optional                                              
:code:`otr_modification`                14     `OTRModification`_              optional                                              
:code:`advances_sort_timestamp`         15     bool                            optional                                              
:code:`otr_status`                      16     `OffTheRecordStatus`_           optional                                              
:code:`persisted`                       17     bool                            optional                                              
:code:`medium_type`                     20     `DeliveryMedium`_               optional                                              
:code:`event_type`                      23     `EventType`_                    optional The event's type.                            
:code:`event_version`                   24     uint64                          optional Event version timestamp.                     
:code:`hash_modifier`                   26     `HashModifier`_                 optional                                              
:code:`group_link_sharing_modification` 31     `GroupLinkSharingModification`_ optional                                              
======================================= ====== =============================== ======== =============================================

UserReadState
-------------

============================= ====== ================ ======== ==============================================================
Field                         Number Type             Label    Description                                                   
============================= ====== ================ ======== ==============================================================
:code:`participant_id`        1      `ParticipantId`_ optional                                                               
:code:`latest_read_timestamp` 2      uint64           optional Timestamp of the user's last read message in the conversation.
============================= ====== ================ ======== ==============================================================

DeliveryMedium
--------------

==================== ====== ===================== ======== ======================================================
Field                Number Type                  Label    Description                                           
==================== ====== ===================== ======== ======================================================
:code:`medium_type`  1      `DeliveryMediumType`_ optional                                                       
:code:`phone_number` 2      `PhoneNumber`_        optional Phone number to use for sending Google Voice messages.
==================== ====== ===================== ======== ======================================================

DeliveryMediumOption
--------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`delivery_medium` 1      `DeliveryMedium`_ optional            
:code:`current_default` 2      bool              optional            
======================= ====== ================= ======== ===========

UserConversationState
---------------------

============================== ====== ======================= ======== ===========
Field                          Number Type                    Label    Description
============================== ====== ======================= ======== ===========
:code:`client_generated_id`    2      string                  optional            
:code:`self_read_state`        7      `UserReadState`_        optional            
:code:`status`                 8      `ConversationStatus`_   optional            
:code:`notification_level`     9      `NotificationLevel`_    optional            
:code:`view`                   10     `ConversationView`_     repeated            
:code:`inviter_id`             11     `ParticipantId`_        optional            
:code:`invite_timestamp`       12     uint64                  optional            
:code:`sort_timestamp`         13     uint64                  optional            
:code:`active_timestamp`       14     uint64                  optional            
:code:`invite_affinity`        15     `InvitationAffinity`_   optional            
:code:`delivery_medium_option` 17     `DeliveryMediumOption`_ repeated            
============================== ====== ======================= ======== ===========

ConversationParticipantData
---------------------------

============================= ====== =================== ======== ===========
Field                         Number Type                Label    Description
============================= ====== =================== ======== ===========
:code:`id`                    1      `ParticipantId`_    optional            
:code:`fallback_name`         2      string              optional            
:code:`invitation_status`     3      `InvitationStatus`_ optional            
:code:`participant_type`      5      `ParticipantType`_  optional            
:code:`new_invitation_status` 6      `InvitationStatus`_ optional            
============================= ====== =================== ======== ===========

Conversation
------------

A conversation between two or more users.

====================================== ====== ============================== ======== ======================================================================
Field                                  Number Type                           Label    Description                                                           
====================================== ====== ============================== ======== ======================================================================
:code:`conversation_id`                1      `ConversationId`_              optional                                                                       
:code:`type`                           2      `ConversationType`_            optional                                                                       
:code:`name`                           3      string                         optional                                                                       
:code:`self_conversation_state`        4      `UserConversationState`_       optional                                                                       
:code:`read_state`                     8      `UserReadState`_               repeated Read state (watermark position) for every conversation participant.   
:code:`has_active_hangout`             9      bool                           optional True if the conversation has an active Hangout.                       
:code:`otr_status`                     10     `OffTheRecordStatus`_          optional The conversation's "off the record" status.                           
:code:`otr_toggle`                     11     `OffTheRecordToggle`_          optional Whether the OTR toggle is available to the user for this conversation.
:code:`conversation_history_supported` 12     bool                           optional                                                                       
:code:`current_participant`            13     `ParticipantId`_               repeated                                                                       
:code:`participant_data`               14     `ConversationParticipantData`_ repeated                                                                       
:code:`network_type`                   18     `NetworkType`_                 repeated                                                                       
:code:`force_history_state`            19     `ForceHistory`_                optional                                                                       
:code:`group_link_sharing_status`      22     `GroupLinkSharingStatus`_      optional                                                                       
====================================== ====== ============================== ======== ======================================================================

EasterEgg
---------

=============== ====== ====== ======== ===========
Field           Number Type   Label    Description
=============== ====== ====== ======== ===========
:code:`message` 1      string optional            
=============== ====== ====== ======== ===========

BlockStateChange
----------------

======================= ====== ================ ======== ===========
Field                   Number Type             Label    Description
======================= ====== ================ ======== ===========
:code:`participant_id`  1      `ParticipantId`_ optional            
:code:`new_block_state` 2      `BlockState`_    optional            
======================= ====== ================ ======== ===========

Photo
-----

===================================== ====== ====== ======== =============================================================================
Field                                 Number Type   Label    Description                                                                  
===================================== ====== ====== ======== =============================================================================
:code:`photo_id`                      1      string optional Picasa photo ID.                                                             
:code:`delete_albumless_source_photo` 2      bool   optional                                                                              
:code:`user_id`                       3      string optional Optional Picasa user ID needed for photos from other accounts (eg. stickers).
:code:`is_custom_user_id`             4      bool   optional Must be true if user_id is specified.                                        
===================================== ====== ====== ======== =============================================================================

ExistingMedia
-------------

============= ====== ======== ======== ===========
Field         Number Type     Label    Description
============= ====== ======== ======== ===========
:code:`photo` 1      `Photo`_ optional            
============= ====== ======== ======== ===========

EventRequestHeader
------------------

=========================== ====== ===================== ======== ===========
Field                       Number Type                  Label    Description
=========================== ====== ===================== ======== ===========
:code:`conversation_id`     1      `ConversationId`_     optional            
:code:`client_generated_id` 2      uint64                optional            
:code:`expected_otr`        3      `OffTheRecordStatus`_ optional            
:code:`delivery_medium`     4      `DeliveryMedium`_     optional            
:code:`event_type`          5      `EventType`_          optional            
=========================== ====== ===================== ======== ===========

ClientVersion
-------------

The client and device version.

========================= ====== ================== ======== =======================================
Field                     Number Type               Label    Description                            
========================= ====== ================== ======== =======================================
:code:`client_id`         1      `ClientId`_        optional Identifies the client.                 
:code:`build_type`        2      `ClientBuildType`_ optional The client build type.                 
:code:`major_version`     3      string             optional Client version.                        
:code:`version_timestamp` 4      uint64             optional Client version timestamp.              
:code:`device_os_version` 5      string             optional OS version string (for native apps).   
:code:`device_hardware`   6      string             optional Device hardware name (for native apps).
========================= ====== ================== ======== =======================================

RequestHeader
-------------

Header for requests from the client to the server.

========================= ====== =================== ======== ===========
Field                     Number Type                Label    Description
========================= ====== =================== ======== ===========
:code:`client_version`    1      `ClientVersion`_    optional            
:code:`client_identifier` 2      `ClientIdentifier`_ optional            
:code:`language_code`     4      string              optional            
========================= ====== =================== ======== ===========

ResponseHeader
--------------

Header for responses from the server to the client.

=========================== ====== ================= ======== ===========
Field                       Number Type              Label    Description
=========================== ====== ================= ======== ===========
:code:`status`              1      `ResponseStatus`_ optional            
:code:`error_description`   2      string            optional            
:code:`debug_url`           3      string            optional            
:code:`request_trace_id`    4      string            optional            
:code:`current_server_time` 5      uint64            optional            
=========================== ====== ================= ======== ===========

Entity
------

A user that can participate in conversations.

============================== ====== ========================== ======== ==============================
Field                          Number Type                       Label    Description                   
============================== ====== ========================== ======== ==============================
:code:`id`                     9      `ParticipantId`_           optional The user's ID.                
:code:`presence`               8      `Presence`_                optional Optional user presence status.
:code:`properties`             10     `EntityProperties`_        optional Optional user properties.     
:code:`entity_type`            13     `ParticipantType`_         optional                               
:code:`had_past_hangout_state` 16     `Entity.PastHangoutState`_ optional                               
============================== ====== ========================== ======== ==============================

Entity.PastHangoutState
-----------------------

=========================================== ====== ===========
Name                                        Number Description
=========================================== ====== ===========
:code:`PAST_HANGOUT_STATE_UNKNOWN`          0                 
:code:`PAST_HANGOUT_STATE_HAD_PAST_HANGOUT` 1                 
:code:`PAST_HANGOUT_STATE_NO_PAST_HANGOUT`  2                 
=========================================== ====== ===========

EntityProperties
----------------

======================== ====== ================= ======== ==============================================================================
Field                    Number Type              Label    Description                                                                   
======================== ====== ================= ======== ==============================================================================
:code:`type`             1      `ProfileType`_    optional                                                                               
:code:`display_name`     2      string            optional                                                                               
:code:`first_name`       3      string            optional                                                                               
:code:`photo_url`        4      string            optional Photo URL with protocol scheme omitted (eg. "//lh.googleusercontent.com/...").
:code:`email`            5      string            repeated                                                                               
:code:`phone`            6      string            repeated                                                                               
:code:`in_users_domain`  10     bool              optional                                                                               
:code:`gender`           11     `Gender`_         optional                                                                               
:code:`photo_url_status` 12     `PhotoUrlStatus`_ optional                                                                               
:code:`canonical_email`  15     string            optional                                                                               
======================== ====== ================= ======== ==============================================================================

ConversationState
-----------------

State of a conversation and recent events.

================================ ====== ========================= ======== ===========
Field                            Number Type                      Label    Description
================================ ====== ========================= ======== ===========
:code:`conversation_id`          1      `ConversationId`_         optional            
:code:`conversation`             2      `Conversation`_           optional            
:code:`event`                    3      `Event`_                  repeated            
:code:`event_continuation_token` 5      `EventContinuationToken`_ optional            
================================ ====== ========================= ======== ===========

EventContinuationToken
----------------------

Token that allows retrieving more events from a position in a conversation.
Specifying event_timestamp is sufficient.

================================== ====== ====== ======== ===========
Field                              Number Type   Label    Description
================================== ====== ====== ======== ===========
:code:`event_id`                   1      string optional            
:code:`storage_continuation_token` 2      bytes  optional            
:code:`event_timestamp`            3      uint64 optional            
================================== ====== ====== ======== ===========

EntityLookupSpec
----------------

Specifies an entity to lookup by one of its properties.

============================== ====== ====== ======== ==============================================================================
Field                          Number Type   Label    Description                                                                   
============================== ====== ====== ======== ==============================================================================
:code:`gaia_id`                1      string optional                                                                               
:code:`email`                  3      string optional                                                                               
:code:`phone`                  4      string optional Phone number as string (eg. "+15551234567").                                  
:code:`create_offnetwork_gaia` 6      bool   optional Whether create a gaia_id for off-network contacts (eg. Google Voice contacts).
============================== ====== ====== ======== ==============================================================================

ConfigurationBit
----------------

============================== ====== ======================= ======== ===========
Field                          Number Type                    Label    Description
============================== ====== ======================= ======== ===========
:code:`configuration_bit_type` 1      `ConfigurationBitType`_ optional            
:code:`value`                  2      bool                    optional            
============================== ====== ======================= ======== ===========

RichPresenceState
-----------------

======================================= ====== =========================== ======== ===========
Field                                   Number Type                        Label    Description
======================================= ====== =========================== ======== ===========
:code:`get_rich_presence_enabled_state` 3      `RichPresenceEnabledState`_ repeated            
======================================= ====== =========================== ======== ===========

RichPresenceEnabledState
------------------------

=============== ====== =================== ======== ===========
Field           Number Type                Label    Description
=============== ====== =================== ======== ===========
:code:`type`    1      `RichPresenceType`_ optional            
:code:`enabled` 2      bool                optional            
=============== ====== =================== ======== ===========

DesktopOffSetting
-----------------

=================== ====== ==== ======== ===============================
Field               Number Type Label    Description                    
=================== ====== ==== ======== ===============================
:code:`desktop_off` 1      bool optional State of "desktop off" setting.
=================== ====== ==== ======== ===============================

DesktopOffState
---------------

=================== ====== ====== ======== =============================================
Field               Number Type   Label    Description                                  
=================== ====== ====== ======== =============================================
:code:`desktop_off` 1      bool   optional Whether Hangouts desktop is signed off or on.
:code:`version`     2      uint64 optional                                              
=================== ====== ====== ======== =============================================

DndSetting
----------

Enable or disable do-not-disturb mode. Not to be confused with
DoNotDisturbSetting, which is used to indicate the state of do-not-disturb
mode.

====================== ====== ====== ======== =================================================
Field                  Number Type   Label    Description                                      
====================== ====== ====== ======== =================================================
:code:`do_not_disturb` 1      bool   optional Whether to enable or disable do-not-disturb mode.
:code:`timeout_secs`   2      uint64 optional Do not disturb expiration in seconds.            
====================== ====== ====== ======== =================================================

PresenceStateSetting
--------------------

==================== ====== ========================== ======== ===========
Field                Number Type                       Label    Description
==================== ====== ========================== ======== ===========
:code:`timeout_secs` 1      uint64                     optional            
:code:`type`         2      `ClientPresenceStateType`_ optional            
==================== ====== ========================== ======== ===========

MoodMessage
-----------

==================== ====== ============== ======== ===========
Field                Number Type           Label    Description
==================== ====== ============== ======== ===========
:code:`mood_content` 1      `MoodContent`_ optional            
==================== ====== ============== ======== ===========

MoodContent
-----------

=============== ====== ========== ======== ===========
Field           Number Type       Label    Description
=============== ====== ========== ======== ===========
:code:`segment` 1      `Segment`_ repeated            
=============== ====== ========== ======== ===========

MoodSetting
-----------

The user's mood message.

==================== ====== ============== ======== ===========
Field                Number Type           Label    Description
==================== ====== ============== ======== ===========
:code:`mood_message` 1      `MoodMessage`_ optional            
==================== ====== ============== ======== ===========

MoodState
---------

==================== ====== ============== ======== ===========
Field                Number Type           Label    Description
==================== ====== ============== ======== ===========
:code:`mood_setting` 4      `MoodSetting`_ optional            
==================== ====== ============== ======== ===========

DeleteAction
------------

==================================== ====== ============= ======== ===========
Field                                Number Type          Label    Description
==================================== ====== ============= ======== ===========
:code:`delete_action_timestamp`      1      uint64        optional            
:code:`delete_upper_bound_timestamp` 2      uint64        optional            
:code:`delete_type`                  3      `DeleteType`_ optional            
==================================== ====== ============= ======== ===========

InviteeID
---------

===================== ====== ====== ======== ===========
Field                 Number Type   Label    Description
===================== ====== ====== ======== ===========
:code:`gaia_id`       1      string optional            
:code:`fallback_name` 4      string optional            
===================== ====== ====== ======== ===========

Country
-------

Describes a user's country.

==================== ====== ====== ======== ===================================
Field                Number Type   Label    Description                        
==================== ====== ====== ======== ===================================
:code:`region_code`  1      string optional Abbreviated region code (eg. "CA").
:code:`country_code` 2      uint64 optional Country's calling code (eg. "1").  
==================== ====== ====== ======== ===================================

DesktopSoundSetting
-------------------

Sound settings in the desktop Hangouts client.

================================ ====== ============= ======== ============================================
Field                            Number Type          Label    Description                                 
================================ ====== ============= ======== ============================================
:code:`desktop_sound_state`      1      `SoundState`_ optional Whether to play sound for incoming messages.
:code:`desktop_ring_sound_state` 2      `SoundState`_ optional Whether to ring for incoming calls.         
================================ ====== ============= ======== ============================================

PhoneData
---------

=============================== ====== ======================= ======== ===========
Field                           Number Type                    Label    Description
=============================== ====== ======================= ======== ===========
:code:`phone`                   1      `Phone`_                repeated            
:code:`caller_id_settings_mask` 3      `CallerIdSettingsMask`_ optional            
=============================== ====== ======================= ======== ===========

Phone
-----

============================== ====== ============================= ======== ===========
Field                          Number Type                          Label    Description
============================== ====== ============================= ======== ===========
:code:`phone_number`           1      `PhoneNumber`_                optional            
:code:`google_voice`           2      bool                          optional            
:code:`verification_status`    3      `PhoneVerificationStatus`_    optional            
:code:`discoverable`           4      bool                          optional            
:code:`discoverability_status` 5      `PhoneDiscoverabilityStatus`_ optional            
:code:`primary`                6      bool                          optional            
============================== ====== ============================= ======== ===========

I18nData
--------

============================ ====== ======================== ======== ===========
Field                        Number Type                     Label    Description
============================ ====== ======================== ======== ===========
:code:`national_number`      1      string                   optional            
:code:`international_number` 2      string                   optional            
:code:`country_code`         3      uint64                   optional            
:code:`region_code`          4      string                   optional            
:code:`is_valid`             5      bool                     optional            
:code:`validation_result`    6      `PhoneValidationResult`_ optional            
============================ ====== ======================== ======== ===========

PhoneNumber
-----------

================= ====== =========== ======== ============================================
Field             Number Type        Label    Description                                 
================= ====== =========== ======== ============================================
:code:`e164`      1      string      optional Phone number as string (eg. "+15551234567").
:code:`i18n_data` 2      `I18nData`_ optional                                             
================= ====== =========== ======== ============================================

SuggestedContactGroupHash
-------------------------

=================== ====== ====== ======== ====================================================================================
Field               Number Type   Label    Description                                                                         
=================== ====== ====== ======== ====================================================================================
:code:`max_results` 1      uint64 optional Number of results to return from this group.                                        
:code:`hash`        2      bytes  optional An optional 4-byte hash. If this matches the server's hash, no results will be sent.
=================== ====== ====== ======== ====================================================================================

SuggestedContact
----------------

========================= ====== =================== ======== ================================
Field                     Number Type                Label    Description                     
========================= ====== =================== ======== ================================
:code:`entity`            1      `Entity`_           optional The contact's entity.           
:code:`invitation_status` 2      `InvitationStatus`_ optional The contact's invitation status.
========================= ====== =================== ======== ================================

SuggestedContactGroup
---------------------

==================== ====== =================== ======== ====================================================================
Field                Number Type                Label    Description                                                         
==================== ====== =================== ======== ====================================================================
:code:`hash_matched` 1      bool                optional True if the request's hash matched and no contacts will be included.
:code:`hash`         2      bytes               optional A 4-byte hash which can be used in subsequent requests.             
:code:`contact`      3      `SuggestedContact`_ repeated List of contacts in this group.                                     
==================== ====== =================== ======== ====================================================================

GroupLinkSharingModification
----------------------------

================== ====== ========================= ======== ===========
Field              Number Type                      Label    Description
================== ====== ========================= ======== ===========
:code:`new_status` 1      `GroupLinkSharingStatus`_ optional            
================== ====== ========================= ======== ===========

StateUpdate
-----------

Pushed from the server to the client to notify it of state changes. Includes
exactly one type of notification, and optionally updates the attributes of a
conversation.

================================================ ====== =============================================== ======== ====================================================================================
Field                                            Number Type                                            Label    Description                                                                         
================================================ ====== =============================================== ======== ====================================================================================
:code:`state_update_header`                      1      `StateUpdateHeader`_                            optional                                                                                     
:code:`conversation`                             13     `Conversation`_                                 optional If set, includes conversation attributes that have been updated by the notification.
:code:`conversation_notification`                2      `ConversationNotification`_                     optional                                                                                     
:code:`event_notification`                       3      `EventNotification`_                            optional                                                                                     
:code:`focus_notification`                       4      `SetFocusNotification`_                         optional                                                                                     
:code:`typing_notification`                      5      `SetTypingNotification`_                        optional                                                                                     
:code:`notification_level_notification`          6      `SetConversationNotificationLevelNotification`_ optional                                                                                     
:code:`reply_to_invite_notification`             7      `ReplyToInviteNotification`_                    optional                                                                                     
:code:`watermark_notification`                   8      `WatermarkNotification`_                        optional                                                                                     
:code:`view_modification`                        11     `ConversationViewModification`_                 optional                                                                                     
:code:`easter_egg_notification`                  12     `EasterEggNotification`_                        optional                                                                                     
:code:`self_presence_notification`               14     `SelfPresenceNotification`_                     optional                                                                                     
:code:`delete_notification`                      15     `DeleteActionNotification`_                     optional                                                                                     
:code:`presence_notification`                    16     `PresenceNotification`_                         optional                                                                                     
:code:`block_notification`                       17     `BlockNotification`_                            optional                                                                                     
:code:`notification_setting_notification`        19     `SetNotificationSettingNotification`_           optional                                                                                     
:code:`rich_presence_enabled_state_notification` 20     `RichPresenceEnabledStateNotification`_         optional                                                                                     
================================================ ====== =============================================== ======== ====================================================================================

StateUpdateHeader
-----------------

Header for StateUpdate messages.

============================= ====== ======================= ======== ===========
Field                         Number Type                    Label    Description
============================= ====== ======================= ======== ===========
:code:`active_client_state`   1      `ActiveClientState`_    optional            
:code:`request_trace_id`      3      string                  optional            
:code:`notification_settings` 4      `NotificationSettings`_ optional            
:code:`current_server_time`   5      uint64                  optional            
============================= ====== ======================= ======== ===========

BatchUpdate
-----------

List of StateUpdate messages to allow pushing multiple notifications from
the server to the client simultaneously.

==================== ====== ============== ======== ===========
Field                Number Type           Label    Description
==================== ====== ============== ======== ===========
:code:`state_update` 1      `StateUpdate`_ repeated            
==================== ====== ============== ======== ===========

ConversationNotification
------------------------

==================== ====== =============== ======== ===========
Field                Number Type            Label    Description
==================== ====== =============== ======== ===========
:code:`conversation` 1      `Conversation`_ optional            
==================== ====== =============== ======== ===========

EventNotification
-----------------

============= ====== ======== ======== ===========
Field         Number Type     Label    Description
============= ====== ======== ======== ===========
:code:`event` 1      `Event`_ optional            
============= ====== ======== ======== ===========

SetFocusNotification
--------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`conversation_id` 1      `ConversationId`_ optional            
:code:`sender_id`       2      `ParticipantId`_  optional            
:code:`timestamp`       3      uint64            optional            
:code:`type`            4      `FocusType`_      optional            
:code:`device`          5      `FocusDevice`_    optional            
======================= ====== ================= ======== ===========

SetTypingNotification
---------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`conversation_id` 1      `ConversationId`_ optional            
:code:`sender_id`       2      `ParticipantId`_  optional            
:code:`timestamp`       3      uint64            optional            
:code:`type`            4      `TypingType`_     optional            
======================= ====== ================= ======== ===========

SetConversationNotificationLevelNotification
--------------------------------------------

======================= ====== ==================== ======== ===========
Field                   Number Type                 Label    Description
======================= ====== ==================== ======== ===========
:code:`conversation_id` 1      `ConversationId`_    optional            
:code:`level`           2      `NotificationLevel`_ optional            
:code:`timestamp`       4      uint64               optional            
======================= ====== ==================== ======== ===========

ReplyToInviteNotification
-------------------------

======================= ====== ==================== ======== ===========
Field                   Number Type                 Label    Description
======================= ====== ==================== ======== ===========
:code:`conversation_id` 1      `ConversationId`_    optional            
:code:`type`            2      `ReplyToInviteType`_ optional            
======================= ====== ==================== ======== ===========

WatermarkNotification
---------------------

============================= ====== ================= ======== ===========
Field                         Number Type              Label    Description
============================= ====== ================= ======== ===========
:code:`sender_id`             1      `ParticipantId`_  optional            
:code:`conversation_id`       2      `ConversationId`_ optional            
:code:`latest_read_timestamp` 3      uint64            optional            
============================= ====== ================= ======== ===========

ConversationViewModification
----------------------------

======================= ====== =================== ======== ===========
Field                   Number Type                Label    Description
======================= ====== =================== ======== ===========
:code:`conversation_id` 1      `ConversationId`_   optional            
:code:`old_view`        2      `ConversationView`_ optional            
:code:`new_view`        3      `ConversationView`_ optional            
======================= ====== =================== ======== ===========

EasterEggNotification
---------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`sender_id`       1      `ParticipantId`_  optional            
:code:`conversation_id` 2      `ConversationId`_ optional            
:code:`easter_egg`      3      `EasterEgg`_      optional            
======================= ====== ================= ======== ===========

SelfPresenceNotification
------------------------

Notifies the status of other clients and mood.

============================== ====== ====================== ======== ===========
Field                          Number Type                   Label    Description
============================== ====== ====================== ======== ===========
:code:`client_presence_state`  1      `ClientPresenceState`_ optional            
:code:`do_not_disturb_setting` 3      `DoNotDisturbSetting`_ optional            
:code:`desktop_off_setting`    4      `DesktopOffSetting`_   optional            
:code:`desktop_off_state`      5      `DesktopOffState`_     optional            
:code:`mood_state`             6      `MoodState`_           optional            
============================== ====== ====================== ======== ===========

DeleteActionNotification
------------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`conversation_id` 1      `ConversationId`_ optional            
:code:`delete_action`   2      `DeleteAction`_   optional            
======================= ====== ================= ======== ===========

PresenceNotification
--------------------

================ ====== ================= ======== ===========
Field            Number Type              Label    Description
================ ====== ================= ======== ===========
:code:`presence` 1      `PresenceResult`_ repeated            
================ ====== ================= ======== ===========

BlockNotification
-----------------

========================== ====== =================== ======== ===========
Field                      Number Type                Label    Description
========================== ====== =================== ======== ===========
:code:`block_state_change` 1      `BlockStateChange`_ repeated            
========================== ====== =================== ======== ===========

SetNotificationSettingNotification
----------------------------------

============================= ====== ====================== ======== ===========
Field                         Number Type                   Label    Description
============================= ====== ====================== ======== ===========
:code:`configuration_bit`     1      `ConfigurationBit`_    repeated            
:code:`desktop_sound_setting` 2      `DesktopSoundSetting`_ optional            
============================= ====== ====================== ======== ===========

RichPresenceEnabledStateNotification
------------------------------------

=================================== ====== =========================== ======== ===========
Field                               Number Type                        Label    Description
=================================== ====== =========================== ======== ===========
:code:`rich_presence_enabled_state` 1      `RichPresenceEnabledState`_ repeated            
=================================== ====== =========================== ======== ===========

ConversationSpec
----------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`conversation_id` 1      `ConversationId`_ optional            
======================= ====== ================= ======== ===========

OffnetworkAddress
-----------------

============= ====== ======================== ======== ===========
Field         Number Type                     Label    Description
============= ====== ======================== ======== ===========
:code:`type`  1      `OffnetworkAddressType`_ optional            
:code:`email` 3      string                   optional            
============= ====== ======================== ======== ===========

EntityResult
------------

=================== ====== =================== ======== ===========
Field               Number Type                Label    Description
=================== ====== =================== ======== ===========
:code:`lookup_spec` 1      `EntityLookupSpec`_ optional            
:code:`entity`      2      `Entity`_           repeated            
=================== ====== =================== ======== ===========

AddUserRequest
--------------

============================ ====== ===================== ======== ===========
Field                        Number Type                  Label    Description
============================ ====== ===================== ======== ===========
:code:`request_header`       1      `RequestHeader`_      optional            
:code:`invitee_id`           3      `InviteeID`_          repeated            
:code:`event_request_header` 5      `EventRequestHeader`_ optional            
============================ ====== ===================== ======== ===========

AddUserResponse
---------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`created_event`   5      `Event`_          optional            
======================= ====== ================= ======== ===========

CreateConversationRequest
-------------------------

=========================== ====== =================== ======== ===========
Field                       Number Type                Label    Description
=========================== ====== =================== ======== ===========
:code:`request_header`      1      `RequestHeader`_    optional            
:code:`type`                2      `ConversationType`_ optional            
:code:`client_generated_id` 3      uint64              optional            
:code:`name`                4      string              optional            
:code:`invitee_id`          5      `InviteeID`_        repeated            
=========================== ====== =================== ======== ===========

CreateConversationResponse
--------------------------

================================ ====== ================= ======== ===========
Field                            Number Type              Label    Description
================================ ====== ================= ======== ===========
:code:`response_header`          1      `ResponseHeader`_ optional            
:code:`conversation`             2      `Conversation`_   optional            
:code:`new_conversation_created` 7      bool              optional            
================================ ====== ================= ======== ===========

DeleteConversationRequest
-------------------------

==================================== ====== ================= ======== ===========
Field                                Number Type              Label    Description
==================================== ====== ================= ======== ===========
:code:`request_header`               1      `RequestHeader`_  optional            
:code:`conversation_id`              2      `ConversationId`_ optional            
:code:`delete_upper_bound_timestamp` 3      uint64            optional            
==================================== ====== ================= ======== ===========

DeleteConversationResponse
--------------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`delete_action`   2      `DeleteAction`_   optional            
======================= ====== ================= ======== ===========

EasterEggRequest
----------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`request_header`  1      `RequestHeader`_  optional            
:code:`conversation_id` 2      `ConversationId`_ optional            
:code:`easter_egg`      3      `EasterEgg`_      optional            
======================= ====== ================= ======== ===========

EasterEggResponse
-----------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`timestamp`       2      uint64            optional            
======================= ====== ================= ======== ===========

GetConversationRequest
----------------------

===================================== ====== ========================= ======== ====================================================================================================================
Field                                 Number Type                      Label    Description                                                                                                         
===================================== ====== ========================= ======== ====================================================================================================================
:code:`request_header`                1      `RequestHeader`_          optional                                                                                                                     
:code:`conversation_spec`             2      `ConversationSpec`_       optional                                                                                                                     
:code:`include_conversation_metadata` 3      bool                      optional Whether the ConversationState in the response should include metadata other than the conversation ID (default true).
:code:`include_event`                 4      bool                      optional Whether to include list of events in the response (default true).                                                   
:code:`max_events_per_conversation`   6      uint64                    optional                                                                                                                     
:code:`event_continuation_token`      7      `EventContinuationToken`_ optional                                                                                                                     
===================================== ====== ========================= ======== ====================================================================================================================

GetConversationResponse
-----------------------

========================== ====== ==================== ======== ===========
Field                      Number Type                 Label    Description
========================== ====== ==================== ======== ===========
:code:`response_header`    1      `ResponseHeader`_    optional            
:code:`conversation_state` 2      `ConversationState`_ optional            
========================== ====== ==================== ======== ===========

GetEntityByIdRequest
--------------------

========================= ====== =================== ======== ===========
Field                     Number Type                Label    Description
========================= ====== =================== ======== ===========
:code:`request_header`    1      `RequestHeader`_    optional            
:code:`batch_lookup_spec` 3      `EntityLookupSpec`_ repeated            
========================= ====== =================== ======== ===========

GetEntityByIdResponse
---------------------

======================= ====== ================= ======== =================================================
Field                   Number Type              Label    Description                                      
======================= ====== ================= ======== =================================================
:code:`response_header` 1      `ResponseHeader`_ optional                                                  
:code:`entity`          2      `Entity`_         repeated Resulting entities of PARTICIPANT_TYPE_GAIA only.
:code:`entity_result`   3      `EntityResult`_   repeated All resulting entities.                          
======================= ====== ================= ======== =================================================

GetGroupConversationUrlRequest
------------------------------

======================= ====== ================= ======== =================================
Field                   Number Type              Label    Description                      
======================= ====== ================= ======== =================================
:code:`request_header`  1      `RequestHeader`_  optional                                  
:code:`conversation_id` 2      `ConversationId`_ optional Conversation to retrieve URL for.
======================= ====== ================= ======== =================================

GetGroupConversationUrlResponse
-------------------------------

============================== ====== ================= ======== ====================================
Field                          Number Type              Label    Description                         
============================== ====== ================= ======== ====================================
:code:`response_header`        1      `ResponseHeader`_ optional                                     
:code:`group_conversation_url` 2      string            optional URL for others to join conversation.
============================== ====== ================= ======== ====================================

GetSuggestedEntitiesRequest
---------------------------

================================== ====== ============================ ======== =============================================================
Field                              Number Type                         Label    Description                                                  
================================== ====== ============================ ======== =============================================================
:code:`request_header`             1      `RequestHeader`_             optional                                                              
:code:`max_count`                  4      uint64                       optional Max number of non-grouped entities to return.                
:code:`favorites`                  8      `SuggestedContactGroupHash`_ optional Optional hash for "favorites" contact group.                 
:code:`contacts_you_hangout_with`  9      `SuggestedContactGroupHash`_ optional Optional hash for "contacts you hangout with" contact group. 
:code:`other_contacts_on_hangouts` 10     `SuggestedContactGroupHash`_ optional Optional hash for "other contacts on hangouts" contact group.
:code:`other_contacts`             11     `SuggestedContactGroupHash`_ optional Optional hash for "other contacts" contact group.            
:code:`dismissed_contacts`         12     `SuggestedContactGroupHash`_ optional Optional hash for "dismissed contacts" contact group.        
:code:`pinned_favorites`           13     `SuggestedContactGroupHash`_ optional Optional hash for "pinned favorites" contact group.          
================================== ====== ============================ ======== =============================================================

GetSuggestedEntitiesResponse
----------------------------

================================== ====== ======================== ======== ===========
Field                              Number Type                     Label    Description
================================== ====== ======================== ======== ===========
:code:`response_header`            1      `ResponseHeader`_        optional            
:code:`entity`                     2      `Entity`_                repeated            
:code:`favorites`                  4      `SuggestedContactGroup`_ optional            
:code:`contacts_you_hangout_with`  5      `SuggestedContactGroup`_ optional            
:code:`other_contacts_on_hangouts` 6      `SuggestedContactGroup`_ optional            
:code:`other_contacts`             7      `SuggestedContactGroup`_ optional            
:code:`dismissed_contacts`         8      `SuggestedContactGroup`_ optional            
:code:`pinned_favorites`           9      `SuggestedContactGroup`_ optional            
================================== ====== ======================== ======== ===========

GetSelfInfoRequest
------------------

====================== ====== ================ ======== ===========
Field                  Number Type             Label    Description
====================== ====== ================ ======== ===========
:code:`request_header` 1      `RequestHeader`_ optional            
====================== ====== ================ ======== ===========

GetSelfInfoResponse
-------------------

============================= ====== ====================== ======== ===========
Field                         Number Type                   Label    Description
============================= ====== ====================== ======== ===========
:code:`response_header`       1      `ResponseHeader`_      optional            
:code:`self_entity`           2      `Entity`_              optional            
:code:`is_known_minor`        3      bool                   optional            
:code:`dnd_state`             5      `DoNotDisturbSetting`_ optional            
:code:`desktop_off_setting`   6      `DesktopOffSetting`_   optional            
:code:`phone_data`            7      `PhoneData`_           optional            
:code:`configuration_bit`     8      `ConfigurationBit`_    repeated            
:code:`desktop_off_state`     9      `DesktopOffState`_     optional            
:code:`google_plus_user`      10     bool                   optional            
:code:`desktop_sound_setting` 11     `DesktopSoundSetting`_ optional            
:code:`rich_presence_state`   12     `RichPresenceState`_   optional            
:code:`default_country`       19     `Country`_             optional            
============================= ====== ====================== ======== ===========

QueryPresenceRequest
--------------------

====================== ====== ================ ======== ===========
Field                  Number Type             Label    Description
====================== ====== ================ ======== ===========
:code:`request_header` 1      `RequestHeader`_ optional            
:code:`participant_id` 2      `ParticipantId`_ repeated            
:code:`field_mask`     3      `FieldMask`_     repeated            
====================== ====== ================ ======== ===========

QueryPresenceResponse
---------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`presence_result` 2      `PresenceResult`_ repeated            
======================= ====== ================= ======== ===========

RemoveUserRequest
-----------------

============================ ====== ===================== ======== ========================================================================
Field                        Number Type                  Label    Description                                                             
============================ ====== ===================== ======== ========================================================================
:code:`request_header`       1      `RequestHeader`_      optional                                                                         
:code:`participant_id`       3      `ParticipantId`_      optional Optional participant to remove from conversation, yourself if not given.
:code:`event_request_header` 5      `EventRequestHeader`_ optional                                                                         
============================ ====== ===================== ======== ========================================================================

RemoveUserResponse
------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`created_event`   4      `Event`_          optional            
======================= ====== ================= ======== ===========

RenameConversationRequest
-------------------------

============================ ====== ===================== ======== ===========
Field                        Number Type                  Label    Description
============================ ====== ===================== ======== ===========
:code:`request_header`       1      `RequestHeader`_      optional            
:code:`new_name`             3      string                optional            
:code:`event_request_header` 5      `EventRequestHeader`_ optional            
============================ ====== ===================== ======== ===========

RenameConversationResponse
--------------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`created_event`   4      `Event`_          optional            
======================= ====== ================= ======== ===========

SearchEntitiesRequest
---------------------

====================== ====== ================ ======== ===========
Field                  Number Type             Label    Description
====================== ====== ================ ======== ===========
:code:`request_header` 1      `RequestHeader`_ optional            
:code:`query`          3      string           optional            
:code:`max_count`      4      uint64           optional            
====================== ====== ================ ======== ===========

SearchEntitiesResponse
----------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`entity`          2      `Entity`_         repeated            
======================= ====== ================= ======== ===========

Location
--------

============= ====== ======== ======== ===========
Field         Number Type     Label    Description
============= ====== ======== ======== ===========
:code:`place` 1      `Place`_ optional            
============= ====== ======== ======== ===========

SendChatMessageRequest
----------------------

============================ ====== ===================== ======== ================
Field                        Number Type                  Label    Description     
============================ ====== ===================== ======== ================
:code:`request_header`       1      `RequestHeader`_      optional                 
:code:`annotation`           5      `EventAnnotation`_    repeated                 
:code:`message_content`      6      `MessageContent`_     optional                 
:code:`existing_media`       7      `ExistingMedia`_      optional                 
:code:`event_request_header` 8      `EventRequestHeader`_ optional                 
:code:`user_id`              9      `ParticipantId`_      optional                 
:code:`location`             10     `Location`_           optional TODO: incomplete
============================ ====== ===================== ======== ================

SendChatMessageResponse
-----------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`created_event`   6      `Event`_          optional            
======================= ====== ================= ======== ===========

ModifyOTRStatusRequest
----------------------

============================ ====== ===================== ======== ===========
Field                        Number Type                  Label    Description
============================ ====== ===================== ======== ===========
:code:`request_header`       1      `RequestHeader`_      optional            
:code:`otr_status`           3      `OffTheRecordStatus`_ optional            
:code:`event_request_header` 5      `EventRequestHeader`_ optional            
============================ ====== ===================== ======== ===========

ModifyOTRStatusResponse
-----------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`created_event`   4      `Event`_          optional            
======================= ====== ================= ======== ===========

SendOffnetworkInvitationRequest
-------------------------------

======================= ====== ==================== ======== ===========
Field                   Number Type                 Label    Description
======================= ====== ==================== ======== ===========
:code:`request_header`  1      `RequestHeader`_     optional            
:code:`invitee_address` 2      `OffnetworkAddress`_ optional            
======================= ====== ==================== ======== ===========

SendOffnetworkInvitationResponse
--------------------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
======================= ====== ================= ======== ===========

SetActiveClientRequest
----------------------

====================== ====== ================ ======== ================================================
Field                  Number Type             Label    Description                                     
====================== ====== ================ ======== ================================================
:code:`request_header` 1      `RequestHeader`_ optional                                                 
:code:`is_active`      2      bool             optional Whether to set the client as active or inactive.
:code:`full_jid`       3      string           optional 'email/resource'.                               
:code:`timeout_secs`   4      uint64           optional Timeout in seconds for client to remain active. 
====================== ====== ================ ======== ================================================

SetActiveClientResponse
-----------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
======================= ====== ================= ======== ===========

SetConversationLevelRequest
---------------------------

====================== ====== ================ ======== ===========
Field                  Number Type             Label    Description
====================== ====== ================ ======== ===========
:code:`request_header` 1      `RequestHeader`_ optional            
====================== ====== ================ ======== ===========

SetConversationLevelResponse
----------------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
======================= ====== ================= ======== ===========

SetConversationNotificationLevelRequest
---------------------------------------

======================= ====== ==================== ======== ===========
Field                   Number Type                 Label    Description
======================= ====== ==================== ======== ===========
:code:`request_header`  1      `RequestHeader`_     optional            
:code:`conversation_id` 2      `ConversationId`_    optional            
:code:`level`           3      `NotificationLevel`_ optional            
======================= ====== ==================== ======== ===========

SetConversationNotificationLevelResponse
----------------------------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`timestamp`       2      uint64            optional            
======================= ====== ================= ======== ===========

SetFocusRequest
---------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`request_header`  1      `RequestHeader`_  optional            
:code:`conversation_id` 2      `ConversationId`_ optional            
:code:`type`            3      `FocusType`_      optional            
:code:`timeout_secs`    4      uint32            optional            
======================= ====== ================= ======== ===========

SetFocusResponse
----------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`timestamp`       2      uint64            optional            
======================= ====== ================= ======== ===========

SetGroupLinkSharingEnabledRequest
---------------------------------

================================= ====== ========================= ======== ==============================
Field                             Number Type                      Label    Description                   
================================= ====== ========================= ======== ==============================
:code:`request_header`            1      `RequestHeader`_          optional                               
:code:`event_request_header`      2      `EventRequestHeader`_     optional                               
:code:`group_link_sharing_status` 4      `GroupLinkSharingStatus`_ optional New group link sharing status.
================================= ====== ========================= ======== ==============================

SetGroupLinkSharingEnabledResponse
----------------------------------

============================ ====== ================= ======== =================================================================
Field                        Number Type              Label    Description                                                      
============================ ====== ================= ======== =================================================================
:code:`response_header`      1      `ResponseHeader`_ optional                                                                  
:code:`created_event`        2      `Event`_          optional Created event of type EVENT_TYPE_GROUP_LINK_SHARING_MODIFICATION.
:code:`updated_conversation` 3      `Conversation`_   optional Updated conversation.                                            
============================ ====== ================= ======== =================================================================

SetPresenceRequest
------------------

Allows setting one or more of the included presence-related settings.

============================== ====== ======================= ======== ===========
Field                          Number Type                    Label    Description
============================== ====== ======================= ======== ===========
:code:`request_header`         1      `RequestHeader`_        optional            
:code:`presence_state_setting` 2      `PresenceStateSetting`_ optional            
:code:`dnd_setting`            3      `DndSetting`_           optional            
:code:`desktop_off_setting`    5      `DesktopOffSetting`_    optional            
:code:`mood_setting`           8      `MoodSetting`_          optional            
============================== ====== ======================= ======== ===========

SetPresenceResponse
-------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
======================= ====== ================= ======== ===========

SetTypingRequest
----------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`request_header`  1      `RequestHeader`_  optional            
:code:`conversation_id` 2      `ConversationId`_ optional            
:code:`type`            3      `TypingType`_     optional            
======================= ====== ================= ======== ===========

SetTypingResponse
-----------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
:code:`timestamp`       2      uint64            optional            
======================= ====== ================= ======== ===========

SyncAllNewEventsRequest
-----------------------

=============================== ====== ================ ======== ===============================================
Field                           Number Type             Label    Description                                    
=============================== ====== ================ ======== ===============================================
:code:`request_header`          1      `RequestHeader`_ optional                                                
:code:`last_sync_timestamp`     2      uint64           optional Timestamp after which to return all new events.
:code:`max_response_size_bytes` 8      uint64           optional                                                
=============================== ====== ================ ======== ===============================================

SyncAllNewEventsResponse
------------------------

========================== ====== ==================== ======== ===========
Field                      Number Type                 Label    Description
========================== ====== ==================== ======== ===========
:code:`response_header`    1      `ResponseHeader`_    optional            
:code:`sync_timestamp`     2      uint64               optional            
:code:`conversation_state` 3      `ConversationState`_ repeated            
========================== ====== ==================== ======== ===========

SyncRecentConversationsRequest
------------------------------

=================================== ====== ================ ======== ==============================================================================
Field                               Number Type             Label    Description                                                                   
=================================== ====== ================ ======== ==============================================================================
:code:`request_header`              1      `RequestHeader`_ optional                                                                               
:code:`last_event_timestamp`        2      uint64           optional Timestamp used for pagination, returns most recent conversations if not given.
:code:`max_conversations`           3      uint64           optional                                                                               
:code:`max_events_per_conversation` 4      uint64           optional                                                                               
:code:`sync_filter`                 5      `SyncFilter`_    repeated                                                                               
=================================== ====== ================ ======== ==============================================================================

SyncRecentConversationsResponse
-------------------------------

================================== ====== ==================== ======== ===========
Field                              Number Type                 Label    Description
================================== ====== ==================== ======== ===========
:code:`response_header`            1      `ResponseHeader`_    optional            
:code:`sync_timestamp`             2      uint64               optional            
:code:`conversation_state`         3      `ConversationState`_ repeated            
:code:`continuation_end_timestamp` 4      uint64               optional            
================================== ====== ==================== ======== ===========

UpdateWatermarkRequest
----------------------

=========================== ====== ================= ======== ===========
Field                       Number Type              Label    Description
=========================== ====== ================= ======== ===========
:code:`request_header`      1      `RequestHeader`_  optional            
:code:`conversation_id`     2      `ConversationId`_ optional            
:code:`last_read_timestamp` 3      uint64            optional            
=========================== ====== ================= ======== ===========

UpdateWatermarkResponse
-----------------------

======================= ====== ================= ======== ===========
Field                   Number Type              Label    Description
======================= ====== ================= ======== ===========
:code:`response_header` 1      `ResponseHeader`_ optional            
======================= ====== ================= ======== ===========

ActiveClientState
-----------------

Describes which Hangouts client is active.

======================================== ====== ==========================
Name                                     Number Description               
======================================== ====== ==========================
:code:`ACTIVE_CLIENT_STATE_NO_ACTIVE`    0      No client is active.      
:code:`ACTIVE_CLIENT_STATE_IS_ACTIVE`    1      This is the active client.
:code:`ACTIVE_CLIENT_STATE_OTHER_ACTIVE` 2      Other client is active.   
======================================== ====== ==========================

FocusType
---------

============================ ====== ===========
Name                         Number Description
============================ ====== ===========
:code:`FOCUS_TYPE_UNKNOWN`   0                 
:code:`FOCUS_TYPE_FOCUSED`   1                 
:code:`FOCUS_TYPE_UNFOCUSED` 2                 
============================ ====== ===========

FocusDevice
-----------

================================ ====== ===========
Name                             Number Description
================================ ====== ===========
:code:`FOCUS_DEVICE_UNSPECIFIED` 0                 
:code:`FOCUS_DEVICE_DESKTOP`     20                
:code:`FOCUS_DEVICE_MOBILE`      300               
================================ ====== ===========

TypingType
----------

=========================== ====== =====================================
Name                        Number Description                          
=========================== ====== =====================================
:code:`TYPING_TYPE_UNKNOWN` 0                                           
:code:`TYPING_TYPE_STARTED` 1      Started typing.                      
:code:`TYPING_TYPE_PAUSED`  2      Stopped typing with inputted text.   
:code:`TYPING_TYPE_STOPPED` 3      Stopped typing with no inputted text.
=========================== ====== =====================================

ClientPresenceStateType
-----------------------

============================================ ====== ===========
Name                                         Number Description
============================================ ====== ===========
:code:`CLIENT_PRESENCE_STATE_UNKNOWN`        0                 
:code:`CLIENT_PRESENCE_STATE_NONE`           1                 
:code:`CLIENT_PRESENCE_STATE_DESKTOP_IDLE`   30                
:code:`CLIENT_PRESENCE_STATE_DESKTOP_ACTIVE` 40                
============================================ ====== ===========

NotificationLevel
-----------------

================================== ====== ===========================
Name                               Number Description                
================================== ====== ===========================
:code:`NOTIFICATION_LEVEL_UNKNOWN` 0                                 
:code:`NOTIFICATION_LEVEL_QUIET`   10     Notifications are disabled.
:code:`NOTIFICATION_LEVEL_RING`    30     Notifications are enabled. 
================================== ====== ===========================

SegmentType
-----------

=============================== ====== ============================
Name                            Number Description                 
=============================== ====== ============================
:code:`SEGMENT_TYPE_TEXT`       0      Segment is text.            
:code:`SEGMENT_TYPE_LINE_BREAK` 1      Segment is a line break.    
:code:`SEGMENT_TYPE_LINK`       2      Segment is hyperlinked text.
=============================== ====== ============================

ItemType
--------

A type of embedded item.

============================ ====== ==================
Name                         Number Description       
============================ ====== ==================
:code:`ITEM_TYPE_THING`      0                        
:code:`ITEM_TYPE_PLUS_PHOTO` 249    Google Plus photo.
:code:`ITEM_TYPE_PLACE`      335                      
:code:`ITEM_TYPE_PLACE_V2`   340    Google Map place. 
============================ ====== ==================

MembershipChangeType
--------------------

==================================== ====== ===========
Name                                 Number Description
==================================== ====== ===========
:code:`MEMBERSHIP_CHANGE_TYPE_JOIN`  1                 
:code:`MEMBERSHIP_CHANGE_TYPE_LEAVE` 2                 
==================================== ====== ===========

HangoutEventType
----------------

====================================== ====== ===========
Name                                   Number Description
====================================== ====== ===========
:code:`HANGOUT_EVENT_TYPE_UNKNOWN`     0                 
:code:`HANGOUT_EVENT_TYPE_START`       1                 
:code:`HANGOUT_EVENT_TYPE_END`         2                 
:code:`HANGOUT_EVENT_TYPE_JOIN`        3                 
:code:`HANGOUT_EVENT_TYPE_LEAVE`       4                 
:code:`HANGOUT_EVENT_TYPE_COMING_SOON` 5                 
:code:`HANGOUT_EVENT_TYPE_ONGOING`     6                 
====================================== ====== ===========

OffTheRecordToggle
------------------

Whether the OTR toggle is available to the user.

====================================== ====== ===========
Name                                   Number Description
====================================== ====== ===========
:code:`OFF_THE_RECORD_TOGGLE_UNKNOWN`  0                 
:code:`OFF_THE_RECORD_TOGGLE_ENABLED`  1                 
:code:`OFF_THE_RECORD_TOGGLE_DISABLED` 2                 
====================================== ====== ===========

OffTheRecordStatus
------------------

============================================ ====== ==================================================
Name                                         Number Description                                       
============================================ ====== ==================================================
:code:`OFF_THE_RECORD_STATUS_UNKNOWN`        0                                                        
:code:`OFF_THE_RECORD_STATUS_OFF_THE_RECORD` 1      Conversation is off-the-record (history disabled).
:code:`OFF_THE_RECORD_STATUS_ON_THE_RECORD`  2      Conversation is on-the-record (history enabled).  
============================================ ====== ==================================================

SourceType
----------

=========================== ====== ===========
Name                        Number Description
=========================== ====== ===========
:code:`SOURCE_TYPE_UNKNOWN` 0                 
=========================== ====== ===========

EventType
---------

================================================== ====== ===========
Name                                               Number Description
================================================== ====== ===========
:code:`EVENT_TYPE_UNKNOWN`                         0                 
:code:`EVENT_TYPE_REGULAR_CHAT_MESSAGE`            1                 
:code:`EVENT_TYPE_SMS`                             2                 
:code:`EVENT_TYPE_VOICEMAIL`                       3                 
:code:`EVENT_TYPE_ADD_USER`                        4                 
:code:`EVENT_TYPE_REMOVE_USER`                     5                 
:code:`EVENT_TYPE_CONVERSATION_RENAME`             6                 
:code:`EVENT_TYPE_HANGOUT`                         7                 
:code:`EVENT_TYPE_PHONE_CALL`                      8                 
:code:`EVENT_TYPE_OTR_MODIFICATION`                9                 
:code:`EVENT_TYPE_PLAN_MUTATION`                   10                
:code:`EVENT_TYPE_MMS`                             11                
:code:`EVENT_TYPE_DEPRECATED_12`                   12                
:code:`EVENT_TYPE_OBSERVED_EVENT`                  13                
:code:`EVENT_TYPE_GROUP_LINK_SHARING_MODIFICATION` 14                
================================================== ====== ===========

ConversationType
----------------

==================================== ====== ===================================================
Name                                 Number Description                                        
==================================== ====== ===================================================
:code:`CONVERSATION_TYPE_UNKNOWN`    0                                                         
:code:`CONVERSATION_TYPE_ONE_TO_ONE` 1      Conversation is one-to-one (only 2 participants).  
:code:`CONVERSATION_TYPE_GROUP`      2      Conversation is group (any number of participants).
==================================== ====== ===================================================

ConversationStatus
------------------

=================================== ====== ======================================
Name                                Number Description                           
=================================== ====== ======================================
:code:`CONVERSATION_STATUS_UNKNOWN` 0                                            
:code:`CONVERSATION_STATUS_INVITED` 1      User is invited to conversation.      
:code:`CONVERSATION_STATUS_ACTIVE`  2      User is participating in conversation.
:code:`CONVERSATION_STATUS_LEFT`    3      User has left conversation.           
=================================== ====== ======================================

ConversationView
----------------

================================== ====== ===============================
Name                               Number Description                    
================================== ====== ===============================
:code:`CONVERSATION_VIEW_UNKNOWN`  0                                     
:code:`CONVERSATION_VIEW_INBOX`    1      Conversation is in inbox.      
:code:`CONVERSATION_VIEW_ARCHIVED` 2      Conversation has been archived.
================================== ====== ===============================

DeliveryMediumType
------------------

==================================== ====== ===========
Name                                 Number Description
==================================== ====== ===========
:code:`DELIVERY_MEDIUM_UNKNOWN`      0                 
:code:`DELIVERY_MEDIUM_BABEL`        1                 
:code:`DELIVERY_MEDIUM_GOOGLE_VOICE` 2                 
:code:`DELIVERY_MEDIUM_LOCAL_SMS`    3                 
==================================== ====== ===========

InvitationAffinity
------------------

=============================== ====== ===========
Name                            Number Description
=============================== ====== ===========
:code:`INVITE_AFFINITY_UNKNOWN` 0                 
:code:`INVITE_AFFINITY_HIGH`    1                 
:code:`INVITE_AFFINITY_LOW`     2                 
=============================== ====== ===========

ParticipantType
---------------

===================================== ====== ===========
Name                                  Number Description
===================================== ====== ===========
:code:`PARTICIPANT_TYPE_UNKNOWN`      0                 
:code:`PARTICIPANT_TYPE_GAIA`         2                 
:code:`PARTICIPANT_TYPE_GOOGLE_VOICE` 3                 
===================================== ====== ===========

InvitationStatus
----------------

================================== ====== ===========
Name                               Number Description
================================== ====== ===========
:code:`INVITATION_STATUS_UNKNOWN`  0                 
:code:`INVITATION_STATUS_PENDING`  1                 
:code:`INVITATION_STATUS_ACCEPTED` 2                 
================================== ====== ===========

ForceHistory
------------

============================= ====== ===========
Name                          Number Description
============================= ====== ===========
:code:`FORCE_HISTORY_UNKNOWN` 0                 
:code:`FORCE_HISTORY_NO`      1                 
============================= ====== ===========

NetworkType
-----------

================================= ====== ===========
Name                              Number Description
================================= ====== ===========
:code:`NETWORK_TYPE_UNKNOWN`      0                 
:code:`NETWORK_TYPE_BABEL`        1                 
:code:`NETWORK_TYPE_GOOGLE_VOICE` 2                 
================================= ====== ===========

BlockState
----------

=========================== ====== ===========
Name                        Number Description
=========================== ====== ===========
:code:`BLOCK_STATE_UNKNOWN` 0                 
:code:`BLOCK_STATE_BLOCK`   1                 
:code:`BLOCK_STATE_UNBLOCK` 2                 
=========================== ====== ===========

ReplyToInviteType
-----------------

==================================== ====== ===========
Name                                 Number Description
==================================== ====== ===========
:code:`REPLY_TO_INVITE_TYPE_UNKNOWN` 0                 
:code:`REPLY_TO_INVITE_TYPE_ACCEPT`  1                 
:code:`REPLY_TO_INVITE_TYPE_DECLINE` 2                 
==================================== ====== ===========

ClientId
--------

Identifies the client.

============================== ====== ===============================================
Name                           Number Description                                    
============================== ====== ===============================================
:code:`CLIENT_ID_UNKNOWN`      0                                                     
:code:`CLIENT_ID_ANDROID`      1      Hangouts app for Android.                      
:code:`CLIENT_ID_IOS`          2      Hangouts app for iOS.                          
:code:`CLIENT_ID_CHROME`       3      Hangouts Chrome extension.                     
:code:`CLIENT_ID_WEB_GPLUS`    5      Hangouts web interface in Google Plus.         
:code:`CLIENT_ID_WEB_GMAIL`    6      Hangouts web interface in Gmail.               
:code:`CLIENT_ID_ULTRAVIOLET`  13     Hangouts Chrome app ("ultraviolet").           
:code:`CLIENT_ID_WEB_HANGOUTS` 44     Hangouts web app (https://hangouts.google.com).
============================== ====== ===============================================

ClientBuildType
---------------

Build type of the client.

================================= ====== ============================
Name                              Number Description                 
================================= ====== ============================
:code:`BUILD_TYPE_UNKNOWN`        0                                  
:code:`BUILD_TYPE_PRODUCTION_WEB` 1      Web app (not used anymore?).
:code:`BUILD_TYPE_PRODUCTION_APP` 3      Native app.                 
================================= ====== ============================

ResponseStatus
--------------

Status of the response from the server to the client.

======================================== ====== ===========
Name                                     Number Description
======================================== ====== ===========
:code:`RESPONSE_STATUS_UNKNOWN`          0                 
:code:`RESPONSE_STATUS_OK`               1                 
:code:`RESPONSE_STATUS_UNEXPECTED_ERROR` 3                 
:code:`RESPONSE_STATUS_INVALID_REQUEST`  4                 
======================================== ====== ===========

PhotoUrlStatus
--------------

Status of EntityProperties.photo_url.

==================================== ====== ===============================
Name                                 Number Description                    
==================================== ====== ===============================
:code:`PHOTO_URL_STATUS_UNKNOWN`     0                                     
:code:`PHOTO_URL_STATUS_PLACEHOLDER` 1      URL is a placeholder.          
:code:`PHOTO_URL_STATUS_USER_PHOTO`  2      URL is a photo set by the user.
==================================== ====== ===============================

Gender
------

====================== ====== ===========
Name                   Number Description
====================== ====== ===========
:code:`GENDER_UNKNOWN` 0                 
:code:`GENDER_MALE`    1                 
:code:`GENDER_FEMALE`  2                 
====================== ====== ===========

ProfileType
-----------

============================ ====== ===========
Name                         Number Description
============================ ====== ===========
:code:`PROFILE_TYPE_NONE`    0                 
:code:`PROFILE_TYPE_ES_USER` 1                 
============================ ====== ===========

ConfigurationBitType
--------------------

A type of binary configuration option.

==================================================================== ====== ===========
Name                                                                 Number Description
==================================================================== ====== ===========
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN`                               0                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_1`                             1                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_2`                             2                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_3`                             3                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_4`                             4                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_5`                             5                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_6`                             6                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_7`                             7                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_8`                             8                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_9`                             9                 
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_10`                            10                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_11`                            11                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_12`                            12                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_13`                            13                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_14`                            14                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_15`                            15                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_16`                            16                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_17`                            17                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_18`                            18                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_19`                            19                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_20`                            20                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_21`                            21                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_22`                            22                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_23`                            23                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_24`                            24                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_25`                            25                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_26`                            26                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_27`                            27                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_28`                            28                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_29`                            29                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_30`                            30                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_31`                            31                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_32`                            32                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_33`                            33                
:code:`CONFIGURATION_BIT_TYPE_DESKTOP_AUTO_EMOJI_CONVERSION_ENABLED` 34                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_35`                            35                
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_36`                            36                
:code:`CONFIGURATION_BIT_TYPE_DESKTOP_COMPACT_MODE_ENABLED`          38                
==================================================================== ====== ===========

RichPresenceType
----------------

======================================== ====== ===========
Name                                     Number Description
======================================== ====== ===========
:code:`RICH_PRESENCE_TYPE_UNKNOWN`       0                 
:code:`RICH_PRESENCE_TYPE_IN_CALL_STATE` 1                 
:code:`RICH_PRESENCE_TYPE_UNKNOWN_3`     3                 
:code:`RICH_PRESENCE_TYPE_UNKNOWN_4`     4                 
:code:`RICH_PRESENCE_TYPE_UNKNOWN_5`     5                 
:code:`RICH_PRESENCE_TYPE_DEVICE`        2                 
:code:`RICH_PRESENCE_TYPE_LAST_SEEN`     6                 
======================================== ====== ===========

FieldMask
---------

============================ ====== ===========
Name                         Number Description
============================ ====== ===========
:code:`FIELD_MASK_REACHABLE` 1                 
:code:`FIELD_MASK_AVAILABLE` 2                 
:code:`FIELD_MASK_MOOD`      3                 
:code:`FIELD_MASK_IN_CALL`   6                 
:code:`FIELD_MASK_DEVICE`    7                 
:code:`FIELD_MASK_LAST_SEEN` 10                
============================ ====== ===========

DeleteType
----------

=============================== ====== ===========
Name                            Number Description
=============================== ====== ===========
:code:`DELETE_TYPE_UNKNOWN`     0                 
:code:`DELETE_TYPE_UPPER_BOUND` 1                 
=============================== ====== ===========

SyncFilter
----------

============================ ====== ===========
Name                         Number Description
============================ ====== ===========
:code:`SYNC_FILTER_UNKNOWN`  0                 
:code:`SYNC_FILTER_INBOX`    1                 
:code:`SYNC_FILTER_ARCHIVED` 2                 
============================ ====== ===========

SoundState
----------

=========================== ====== ===========
Name                        Number Description
=========================== ====== ===========
:code:`SOUND_STATE_UNKNOWN` 0                 
:code:`SOUND_STATE_ON`      1                 
:code:`SOUND_STATE_OFF`     2                 
=========================== ====== ===========

CallerIdSettingsMask
--------------------

======================================== ====== ===========
Name                                     Number Description
======================================== ====== ===========
:code:`CALLER_ID_SETTINGS_MASK_UNKNOWN`  0                 
:code:`CALLER_ID_SETTINGS_MASK_PROVIDED` 1                 
======================================== ====== ===========

PhoneVerificationStatus
-----------------------

========================================== ====== ===========
Name                                       Number Description
========================================== ====== ===========
:code:`PHONE_VERIFICATION_STATUS_UNKNOWN`  0                 
:code:`PHONE_VERIFICATION_STATUS_VERIFIED` 1                 
========================================== ====== ===========

PhoneDiscoverabilityStatus
--------------------------

================================================================== ====== ===========
Name                                                               Number Description
================================================================== ====== ===========
:code:`PHONE_DISCOVERABILITY_STATUS_UNKNOWN`                       0                 
:code:`PHONE_DISCOVERABILITY_STATUS_OPTED_IN_BUT_NOT_DISCOVERABLE` 2                 
================================================================== ====== ===========

PhoneValidationResult
---------------------

=========================================== ====== ===========
Name                                        Number Description
=========================================== ====== ===========
:code:`PHONE_VALIDATION_RESULT_IS_POSSIBLE` 0                 
=========================================== ====== ===========

OffnetworkAddressType
---------------------

======================================= ====== ===========
Name                                    Number Description
======================================= ====== ===========
:code:`OFFNETWORK_ADDRESS_TYPE_UNKNOWN` 0                 
:code:`OFFNETWORK_ADDRESS_TYPE_EMAIL`   1                 
======================================= ====== ===========

GroupLinkSharingStatus
----------------------

========================================= ====== ===========
Name                                      Number Description
========================================= ====== ===========
:code:`GROUP_LINK_SHARING_STATUS_UNKNOWN` 0                 
:code:`GROUP_LINK_SHARING_STATUS_ON`      1                 
:code:`GROUP_LINK_SHARING_STATUS_OFF`     2                 
========================================= ====== ===========

