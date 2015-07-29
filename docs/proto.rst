.. This file was automatically generated from hangups/hangouts.proto and should be be edited directly.

DoNotDisturbSetting
-------------------

============================ ====== ======== ===========
Field                        Type   Label    Description
============================ ====== ======== ===========
:code:`do_not_disturb`       bool   optional            
:code:`expiration_timestamp` uint64 optional            
============================ ====== ======== ===========

NotificationSettings
--------------------

==================== ====================== ======== ===========
Field                Type                   Label    Description
==================== ====================== ======== ===========
:code:`dnd_settings` `DoNotDisturbSetting`_ optional            
==================== ====================== ======== ===========

ConversationID
--------------

========== ====== ======== ===========
Field      Type   Label    Description
========== ====== ======== ===========
:code:`id` string optional            
========== ====== ======== ===========

UserID
------

TODO: should be ParticipantId?

=============== ====== ======== ===========
Field           Type   Label    Description
=============== ====== ======== ===========
:code:`gaia_id` string optional            
:code:`chat_id` string optional            
=============== ====== ======== ===========

DeviceStatus
------------

================ ==== ======== =============================
Field            Type Label    Description                  
================ ==== ======== =============================
:code:`unknown1` bool optional TODO: desktop, mobile, tablet
:code:`unknown2` bool optional                              
:code:`unknown3` bool optional                              
================ ==== ======== =============================

Presence
--------

===================== =============== ======== ===========
Field                 Type            Label    Description
===================== =============== ======== ===========
:code:`reachable`     bool            optional            
:code:`available`     bool            optional            
:code:`device_status` `DeviceStatus`_ optional            
:code:`mood_setting`  `MoodSetting`_  optional            
===================== =============== ======== ===========

PresenceResult
--------------

================ =========== ======== ===========
Field            Type        Label    Description
================ =========== ======== ===========
:code:`user_id`  `UserID`_   optional            
:code:`presence` `Presence`_ optional            
================ =========== ======== ===========

ClientIdentifier
----------------

================= ====== ======== ==============================
Field             Type   Label    Description                   
================= ====== ======== ==============================
:code:`resource`  string optional (client_id in hangups)        
:code:`header_id` string optional unknown (header_id in hangups)
================= ====== ======== ==============================

ClientPresenceState
-------------------

================== ========================== ======== ===========
Field              Type                       Label    Description
================== ========================== ======== ===========
:code:`identifier` `ClientIdentifier`_        optional            
:code:`state`      `ClientPresenceStateType`_ optional            
================== ========================== ======== ===========

UserEventState
--------------

=========================== ==================== ======== ===========
Field                       Type                 Label    Description
=========================== ==================== ======== ===========
:code:`user_id`             `UserID`_            optional            
:code:`client_generated_id` string               optional            
:code:`notification_level`  `NotificationLevel`_ optional            
=========================== ==================== ======== ===========

Formatting
----------

===================== ==== ======== ===========
Field                 Type Label    Description
===================== ==== ======== ===========
:code:`bold`          bool optional            
:code:`italic`        bool optional            
:code:`strikethrough` bool optional            
:code:`underline`     bool optional            
===================== ==== ======== ===========

LinkData
--------

=================== ====== ======== ===========
Field               Type   Label    Description
=================== ====== ======== ===========
:code:`link_target` string optional            
=================== ====== ======== ===========

Segment
-------

================== ============== ======== =============================================================
Field              Type           Label    Description                                                  
================== ============== ======== =============================================================
:code:`type`       `SegmentType`_ required Hangouts for Chrome misbehaves if this field isn't serialized
:code:`text`       string         optional may be empty for linebreaks                                  
:code:`formatting` `Formatting`_  optional                                                              
:code:`link_data`  `LinkData`_    optional                                                              
================== ============== ======== =============================================================

EmbedItem
---------

============ ====== ======== =============================
Field        Type   Label    Description                  
============ ====== ======== =============================
:code:`type` uint64 repeated 249 (PLUS_PHOTO), 340, 335, 0
============ ====== ======== =============================

Attachment
----------

================== ============ ======== ===========
Field              Type         Label    Description
================== ============ ======== ===========
:code:`embed_item` `EmbedItem`_ optional            
================== ============ ======== ===========

MessageContent
--------------

================== ============= ======== ===========
Field              Type          Label    Description
================== ============= ======== ===========
:code:`segment`    `Segment`_    repeated            
:code:`attachment` `Attachment`_ repeated            
================== ============= ======== ===========

ChatMessage
-----------

======================= ================= ======== =============================================
Field                   Type              Label    Description                                  
======================= ================= ======== =============================================
:code:`message_content` `MessageContent`_ optional always 0? = 1; annotation (always None?) = 2;
======================= ================= ======== =============================================

MembershipChange
----------------

======================= ======================= ======== ===============
Field                   Type                    Label    Description    
======================= ======================= ======== ===============
:code:`type`            `MembershipChangeType`_ optional                
:code:`participant_ids` `UserID`_               repeated unknown [] = 2;
======================= ======================= ======== ===============

ConversationRename
------------------

================ ====== ======== ===========
Field            Type   Label    Description
================ ====== ======== ===========
:code:`new_name` string optional            
:code:`old_name` string optional            
================ ====== ======== ===========

HangoutEvent
------------

====================== =================== ======== ==============
Field                  Type                Label    Description   
====================== =================== ======== ==============
:code:`event_type`     `HangoutEventType`_ optional               
:code:`participant_id` `UserID`_           repeated unknown 1 = 7;
====================== =================== ======== ==============

OTRModification
---------------

====================== ===================== ======== ===========
Field                  Type                  Label    Description
====================== ===================== ======== ===========
:code:`old_otr_status` `OffTheRecordStatus`_ optional            
:code:`new_otr_status` `OffTheRecordStatus`_ optional            
:code:`old_otr_toggle` `OffTheRecordToggle`_ optional            
:code:`new_otr_toggle` `OffTheRecordToggle`_ optional            
====================== ===================== ======== ===========

Event
-----

=============================== ===================== ======== ===========================================
Field                           Type                  Label    Description                                
=============================== ===================== ======== ===========================================
:code:`conversation_id`         `ConversationID`_     optional                                            
:code:`sender_id`               `UserID`_             optional                                            
:code:`timestamp`               uint64                optional                                            
:code:`self_event_state`        `UserEventState`_     optional                                            
:code:`source_type`             `SourceType`_         optional                                            
:code:`chat_message`            `ChatMessage`_        optional TODO: some of these are probably in a oneof
:code:`membership_change`       `MembershipChange`_   optional                                            
:code:`conversation_rename`     `ConversationRename`_ optional                                            
:code:`hangout_event`           `HangoutEvent`_       optional                                            
:code:`event_id`                string                optional                                            
:code:`expiration_timestamp`    uint64                optional                                            
:code:`otr_modification`        `OTRModification`_    optional                                            
:code:`advances_sort_timestamp` bool                  optional                                            
:code:`otr_status`              `OffTheRecordStatus`_ optional                                            
:code:`persisted`               bool                  optional                                            
:code:`event_type`              `EventType`_          optional unknown ([1]) = 20;                        
=============================== ===================== ======== ===========================================

UserReadState
-------------

============================= ========= ======== ===============
Field                         Type      Label    Description    
============================= ========= ======== ===============
:code:`participant_id`        `UserID`_ optional                
:code:`latest_read_timestamp` uint64    optional TODO: always 0?
============================= ========= ======== ===============

DeliveryMedium
--------------

=================== ===================== ======== ===========
Field               Type                  Label    Description
=================== ===================== ======== ===========
:code:`medium_type` `DeliveryMediumType`_ optional            
=================== ===================== ======== ===========

DeliveryMediumOption
--------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`delivery_medium` `DeliveryMedium`_ optional            
:code:`current_default` bool              optional            
======================= ================= ======== ===========

UserConversationState
---------------------

============================== ======================= ======== ================================
Field                          Type                    Label    Description                     
============================== ======================= ======== ================================
:code:`client_generated_id`    string                  optional                                 
:code:`self_read_state`        `UserReadState`_        optional                                 
:code:`status`                 `ConversationStatus`_   optional                                 
:code:`notification_level`     `NotificationLevel`_    optional                                 
:code:`view`                   `ConversationView`_     repeated                                 
:code:`inviter_id`             `UserID`_               optional                                 
:code:`invite_timestamp`       uint64                  optional                                 
:code:`sort_timestamp`         uint64                  optional                                 
:code:`active_timestamp`       uint64                  optional when conversation became active?
:code:`delivery_medium_option` `DeliveryMediumOption`_ repeated                                 
============================== ======================= ======== ================================

ConversationParticipantData
---------------------------

======================== ================== ======== =====================================================================================================================
Field                    Type               Label    Description                                                                                                          
======================== ================== ======== =====================================================================================================================
:code:`id`               `UserID`_          optional                                                                                                                      
:code:`fallback_name`    string             optional                                                                                                                      
:code:`participant_type` `ParticipantType`_ optional TODO: one of these is invitation_status and the other is new_invitation_status unknown (2, 1) = 3; unknown (2, 3) = 6
======================== ================== ======== =====================================================================================================================

Conversation
------------

=============================== ============================== ======== =====================================
Field                           Type                           Label    Description                          
=============================== ============================== ======== =====================================
:code:`conversation_id`         `ConversationID`_              optional                                      
:code:`type`                    `ConversationType`_            optional                                      
:code:`name`                    string                         optional                                      
:code:`self_conversation_state` `UserConversationState`_       optional                                      
:code:`read_state`              `UserReadState`_               repeated                                      
:code:`otr_status`              `OffTheRecordStatus`_          optional unknown (0) = 9;                     
:code:`current_participant`     `UserID`_                      repeated unknown (1) = 11;                    
:code:`participant_data`        `ConversationParticipantData`_ repeated unknown ([1]) = 18; unknown (0) = 19;
=============================== ============================== ======== =====================================

EasterEgg
---------

=============== ====== ======== ===========
Field           Type   Label    Description
=============== ====== ======== ===========
:code:`message` string optional            
=============== ====== ======== ===========

BlockStateChange
----------------

======================= ============= ======== ===========
Field                   Type          Label    Description
======================= ============= ======== ===========
:code:`participant_id`  `UserID`_     optional            
:code:`new_block_state` `BlockState`_ optional            
======================= ============= ======== ===========

Photo
-----

===================================== ====== ======== ==================
Field                                 Type   Label    Description       
===================================== ====== ======== ==================
:code:`photo_id`                      string optional                   
:code:`delete_albumless_source_photo` bool   optional TODO: never tested
===================================== ====== ======== ==================

ExistingMedia
-------------

============= ======== ======== ===========
Field         Type     Label    Description
============= ======== ======== ===========
:code:`photo` `Photo`_ optional            
============= ======== ======== ===========

EventRequestHeader
------------------

=========================== ===================== ======== ===========
Field                       Type                  Label    Description
=========================== ===================== ======== ===========
:code:`conversation_id`     `ConversationID`_     optional            
:code:`client_generated_id` uint64                optional            
:code:`expected_otr`        `OffTheRecordStatus`_ optional            
=========================== ===================== ======== ===========

ClientVersion
-------------

========================= ================== ======== ==============================================
Field                     Type               Label    Description                                   
========================= ================== ======== ==============================================
:code:`client_id`         `ClientId`_        optional                                               
:code:`build_type`        `ClientBuildType`_ optional                                               
:code:`major_version`     string             optional client version string                         
:code:`version_timestamp` uint64             optional not a timestamp in iOS/Android                
:code:`device_os_version` string             optional OS version string, only used by native apps   
:code:`device_hardware`   string             optional device hardware name, only used by native apps
========================= ================== ======== ==============================================

RequestHeader
-------------

========================= =================== ======== ================
Field                     Type                Label    Description     
========================= =================== ======== ================
:code:`client_version`    `ClientVersion`_    optional TODO: incomplete
:code:`client_identifier` `ClientIdentifier`_ optional                 
:code:`language_code`     string              optional                 
========================= =================== ======== ================

ResponseHeader
--------------

=========================== ================= ======== ===========
Field                       Type              Label    Description
=========================== ================= ======== ===========
:code:`status`              `ResponseStatus`_ optional            
:code:`error_description`   string            optional            
:code:`debug_url`           string            optional            
:code:`request_trace_id`    string            optional            
:code:`current_server_time` uint64            optional            
=========================== ================= ======== ===========

Entity
------

================== =================== ======== ==============
Field              Type                Label    Description   
================== =================== ======== ==============
:code:`id`         `UserID`_           optional presence? = 8;
:code:`properties` `EntityProperties`_ optional TODO          
================== =================== ======== ==============

EntityProperties
----------------

======================== ================= ======== ===========
Field                    Type              Label    Description
======================== ================= ======== ===========
:code:`type`             `ProfileType`_    optional            
:code:`display_name`     string            optional            
:code:`first_name`       string            optional            
:code:`photo_url`        string            optional            
:code:`email`            string            repeated            
:code:`phone`            string            repeated            
:code:`in_users_domain`  bool              optional            
:code:`gender`           `Gender`_         optional            
:code:`photo_url_status` `PhotoUrlStatus`_ optional            
:code:`canonical_email`  string            optional            
======================== ================= ======== ===========

ConversationState
-----------------

================================ ========================= ======== ===========
Field                            Type                      Label    Description
================================ ========================= ======== ===========
:code:`conversation_id`          `ConversationID`_         optional            
:code:`conversation`             `Conversation`_           optional            
:code:`event`                    `Event`_                  repeated            
:code:`event_continuation_token` `EventContinuationToken`_ optional            
================================ ========================= ======== ===========

EventContinuationToken
----------------------

================================== ====== ======== ===========
Field                              Type   Label    Description
================================== ====== ======== ===========
:code:`event_id`                   string optional            
:code:`storage_continuation_token` string optional            
:code:`event_timestamp`            uint64 optional            
================================== ====== ======== ===========

EntityLookupSpec
----------------

=============== ====== ======== ===========
Field           Type   Label    Description
=============== ====== ======== ===========
:code:`gaia_id` string optional TODO       
=============== ====== ======== ===========

ConfigurationBit
----------------

============================== ======================= ======== ===========
Field                          Type                    Label    Description
============================== ======================= ======== ===========
:code:`configuration_bit_type` `ConfigurationBitType`_ optional            
:code:`value`                  bool                    optional            
============================== ======================= ======== ===========

RichPresenceState
-----------------

======================================= =========================== ======== ===========
Field                                   Type                        Label    Description
======================================= =========================== ======== ===========
:code:`get_rich_presence_enabled_state` `RichPresenceEnabledState`_ repeated            
======================================= =========================== ======== ===========

RichPresenceEnabledState
------------------------

=============== =================== ======== ===========
Field           Type                Label    Description
=============== =================== ======== ===========
:code:`type`    `RichPresenceType`_ optional            
:code:`enabled` bool                optional            
=============== =================== ======== ===========

DesktopOffSetting
-----------------

=================== ==== ======== ==============================
Field               Type Label    Description                   
=================== ==== ======== ==============================
:code:`desktop_off` bool optional State of "desktop off" setting
=================== ==== ======== ==============================

DesktopOffState
---------------

=================== ==== ======== ============================================
Field               Type Label    Description                                 
=================== ==== ======== ============================================
:code:`desktop_off` bool optional Whether Hangouts desktop is signed off or on
=================== ==== ======== ============================================

DndSetting
----------

====================== ====== ======== ================================================================================================================================================
Field                  Type   Label    Description                                                                                                                                     
====================== ====== ======== ================================================================================================================================================
:code:`do_not_disturb` bool   optional Enable or disable do-not-disturb mode Not to be confused with DoNotDisturbSetting, which is the same thing but with an timestamp for expiration.
:code:`timeout_secs`   uint64 optional do not disturb expiration, in seconds                                                                                                           
====================== ====== ======== ================================================================================================================================================

PresenceStateSetting
--------------------

==================== ========================== ======== =====================================
Field                Type                       Label    Description                          
==================== ========================== ======== =====================================
:code:`timeout_secs` uint64                     optional Change the client presence state type
:code:`type`         `ClientPresenceStateType`_ optional                                      
==================== ========================== ======== =====================================

MoodMessage
-----------

==================== ============== ======== ===========
Field                Type           Label    Description
==================== ============== ======== ===========
:code:`mood_content` `MoodContent`_ optional            
==================== ============== ======== ===========

MoodContent
-----------

=============== ========== ======== ===========
Field           Type       Label    Description
=============== ========== ======== ===========
:code:`segment` `Segment`_ repeated            
=============== ========== ======== ===========

MoodSetting
-----------

==================== ============== ======== ============================
Field                Type           Label    Description                 
==================== ============== ======== ============================
:code:`mood_message` `MoodMessage`_ optional Chat the user's mood message
==================== ============== ======== ============================

MoodState
---------

==================== ============== ======== ===========
Field                Type           Label    Description
==================== ============== ======== ===========
:code:`mood_setting` `MoodSetting`_ optional            
==================== ============== ======== ===========

DeleteAction
------------

==================================== ============= ======== ===========
Field                                Type          Label    Description
==================================== ============= ======== ===========
:code:`delete_action_timestamp`      uint64        optional            
:code:`delete_upper_bound_timestamp` uint64        optional            
:code:`delete_type`                  `DeleteType`_ optional            
==================================== ============= ======== ===========

InviteeID
---------

===================== ====== ======== ===========
Field                 Type   Label    Description
===================== ====== ======== ===========
:code:`gaia_id`       string optional            
:code:`fallback_name` string optional            
===================== ====== ======== ===========

StateUpdate
-----------

================================================ =============================================== ======== ===================================================================================================================================
Field                                            Type                                            Label    Description                                                                                                                        
================================================ =============================================== ======== ===================================================================================================================================
:code:`state_update_header`                      `StateUpdateHeader`_                            optional                                                                                                                                    
:code:`conversation`                             `Conversation`_                                 optional only gets sent when the state of the conversation changes TODO: seems like this should be a notification, but it's not in the oneof
:code:`event_notification`                       `EventNotification`_                            optional UnimplementedMessage conversation_notification = 2; // always null?                                                                
:code:`focus_notification`                       `SetFocusNotification`_                         optional                                                                                                                                    
:code:`typing_notification`                      `SetTypingNotification`_                        optional                                                                                                                                    
:code:`notification_level_notification`          `SetConversationNotificationLevelNotification`_ optional                                                                                                                                    
:code:`reply_to_invite_notification`             `ReplyToInviteNotification`_                    optional                                                                                                                                    
:code:`watermark_notification`                   `WatermarkNotification`_                        optional                                                                                                                                    
:code:`view_modification`                        `ConversationViewModification`_                 optional UnimplementedMessage unknown_1 = 9; UnimplementedMessage settings_notification = 10;  TODO: should be named as a notification?     
:code:`easter_egg_notification`                  `EasterEggNotification`_                        optional                                                                                                                                    
:code:`self_presence_notification`               `SelfPresenceNotification`_                     optional                                                                                                                                    
:code:`delete_notification`                      `DeleteActionNotification`_                     optional                                                                                                                                    
:code:`presence_notification`                    `PresenceNotification`_                         optional                                                                                                                                    
:code:`block_notification`                       `BlockNotification`_                            optional                                                                                                                                    
:code:`notification_setting_notification`        `SetNotificationSettingNotification`_           optional UnimplementedMessage invitation_watermark_notification = 18;                                                                       
:code:`rich_presence_enabled_state_notification` `RichPresenceEnabledStateNotification`_         optional                                                                                                                                    
================================================ =============================================== ======== ===================================================================================================================================

StateUpdateHeader
-----------------

============================= ======================= ======== ================================================================================================================
Field                         Type                    Label    Description                                                                                                     
============================= ======================= ======== ================================================================================================================
:code:`active_client_state`   `ActiveClientState`_    optional TODO                                                                                                            
:code:`request_trace_id`      string                  optional unknown = 2                                                                                                     
:code:`notification_settings` `NotificationSettings`_ optional                                                                                                                 
:code:`current_server_time`   uint64                  optional archive settings? ([1]) = 6 unknown = 7 optional ID of the client causing the update (3767219427742586121) ? = 8
============================= ======================= ======== ================================================================================================================

BatchUpdate
-----------

==================== ============== ======== ===========
Field                Type           Label    Description
==================== ============== ======== ===========
:code:`state_update` `StateUpdate`_ repeated            
==================== ============== ======== ===========

EventNotification
-----------------

============= ======== ======== ===========
Field         Type     Label    Description
============= ======== ======== ===========
:code:`event` `Event`_ optional            
============= ======== ======== ===========

SetFocusNotification
--------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`conversation_id` `ConversationID`_ optional            
:code:`user_id`         `UserID`_         optional            
:code:`timestamp`       uint64            optional            
:code:`type`            `FocusType`_      optional            
:code:`device`          `FocusDevice`_    optional            
======================= ================= ======== ===========

SetTypingNotification
---------------------

======================= ================= ======== ====================
Field                   Type              Label    Description         
======================= ================= ======== ====================
:code:`conversation_id` `ConversationID`_ optional                     
:code:`user_id`         `UserID`_         optional                     
:code:`timestamp`       uint64            optional                     
:code:`type`            `TypingType`_     optional TODO: should be type
======================= ================= ======== ====================

SetConversationNotificationLevelNotification
--------------------------------------------

======================= ==================== ======== ================
Field                   Type                 Label    Description     
======================= ==================== ======== ================
:code:`conversation_id` `ConversationID`_    optional                 
:code:`level`           `NotificationLevel`_ optional                 
:code:`timestamp`       uint64               optional unknown (0) = 3;
======================= ==================== ======== ================

ReplyToInviteNotification
-------------------------

======================= ==================== ======== ==================================================
Field                   Type                 Label    Description                                       
======================= ==================== ======== ==================================================
:code:`conversation_id` `ConversationID`_    optional TODO: untested [['UgwnHidpJTfc7G7BhUR4AaABAQ'], 1]
:code:`type`            `ReplyToInviteType`_ optional                                                   
======================= ==================== ======== ==================================================

WatermarkNotification
---------------------

============================= ================= ======== ===========
Field                         Type              Label    Description
============================= ================= ======== ===========
:code:`participant_id`        `UserID`_         optional            
:code:`conversation_id`       `ConversationID`_ optional            
:code:`latest_read_timestamp` uint64            optional            
============================= ================= ======== ===========

ConversationViewModification
----------------------------

======================= =================== ======== =================================================================================================
Field                   Type                Label    Description                                                                                      
======================= =================== ======== =================================================================================================
:code:`conversation_id` `ConversationID`_   optional                                                                                                  
:code:`old_view`        `ConversationView`_ optional                                                                                                  
:code:`new_view`        `ConversationView`_ optional archive: [['Ugz6j8W5_JUj9ltNeEl4AaABAQ'], 1, 2] unarchive: [['Ugz6j8W5_JUj9ltNeEl4AaABAQ'], 2, 1]
======================= =================== ======== =================================================================================================

EasterEggNotification
---------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`sender_id`       `UserID`_         optional            
:code:`conversation_id` `ConversationID`_ optional            
:code:`easter_egg`      `EasterEgg`_      optional            
======================= ================= ======== ===========

SelfPresenceNotification
------------------------

============================== ====================== ======== ================================
Field                          Type                   Label    Description                     
============================== ====================== ======== ================================
:code:`client_presence_state`  `ClientPresenceState`_ optional status of other clients and mood
:code:`do_not_disturb_setting` `DoNotDisturbSetting`_ optional                                 
:code:`desktop_off_setting`    `DesktopOffSetting`_   optional                                 
:code:`desktop_off_state`      `DesktopOffState`_     optional                                 
:code:`mood_state`             `MoodState`_           optional                                 
============================== ====================== ======== ================================

DeleteActionNotification
------------------------

======================= ================= ======== ==============================================================================================
Field                   Type              Label    Description                                                                                   
======================= ================= ======== ==============================================================================================
:code:`conversation_id` `ConversationID`_ optional delete conversation: [['Ugz6j8W5_JUj9ltNeEl4AaABAQ'], [1435638391438133, 1435637794504105, 1]]
:code:`delete_action`   `DeleteAction`_   optional                                                                                               
======================= ================= ======== ==============================================================================================

PresenceNotification
--------------------

================ ================= ======== ===========
Field            Type              Label    Description
================ ================= ======== ===========
:code:`presence` `PresenceResult`_ repeated            
================ ================= ======== ===========

BlockNotification
-----------------

========================== =================== ======== =========================================================================
Field                      Type                Label    Description                                                              
========================== =================== ======== =========================================================================
:code:`block_state_change` `BlockStateChange`_ repeated block someone [[[['102610215878429116806', '102610215878429116806'], 1]]]
========================== =================== ======== =========================================================================

SetNotificationSettingNotification
----------------------------------

===== ==== ===== ===========
Field Type Label Description
===== ==== ===== ===========
===== ==== ===== ===========

RichPresenceEnabledStateNotification
------------------------------------

=================================== =========================== ======== ===========
Field                               Type                        Label    Description
=================================== =========================== ======== ===========
:code:`rich_presence_enabled_state` `RichPresenceEnabledState`_ repeated            
=================================== =========================== ======== ===========

ConversationSpec
----------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`conversation_id` `ConversationID`_ optional TODO       
======================= ================= ======== ===========

AddUserRequest
--------------

============================ ===================== ======== ===========
Field                        Type                  Label    Description
============================ ===================== ======== ===========
:code:`request_header`       `RequestHeader`_      optional            
:code:`invitee_id`           `InviteeID`_          repeated            
:code:`event_request_header` `EventRequestHeader`_ optional            
============================ ===================== ======== ===========

AddUserResponse
---------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`created_event`   `Event`_          optional            
======================= ================= ======== ===========

CreateConversationRequest
-------------------------

=========================== =================== ======== ===========
Field                       Type                Label    Description
=========================== =================== ======== ===========
:code:`request_header`      `RequestHeader`_    optional            
:code:`type`                `ConversationType`_ optional            
:code:`client_generated_id` uint64              optional            
:code:`name`                string              optional            
:code:`invitee_id`          `InviteeID`_        repeated            
=========================== =================== ======== ===========

CreateConversationResponse
--------------------------

================================ ================= ======== ===========
Field                            Type              Label    Description
================================ ================= ======== ===========
:code:`response_header`          `ResponseHeader`_ optional            
:code:`conversation`             `Conversation`_   optional            
:code:`new_conversation_created` bool              optional            
================================ ================= ======== ===========

DeleteConversationRequest
-------------------------

==================================== ================= ======== ===========
Field                                Type              Label    Description
==================================== ================= ======== ===========
:code:`request_header`               `RequestHeader`_  optional            
:code:`conversation_id`              `ConversationID`_ optional            
:code:`delete_upper_bound_timestamp` uint64            optional            
==================================== ================= ======== ===========

DeleteConversationResponse
--------------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`delete_action`   `DeleteAction`_   optional            
======================= ================= ======== ===========

EasterEggRequest
----------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`request_header`  `RequestHeader`_  optional            
:code:`conversation_id` `ConversationID`_ optional            
:code:`easter_egg`      `EasterEgg`_      optional            
======================= ================= ======== ===========

EasterEggResponse
-----------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`timestamp`       uint64            optional            
======================= ================= ======== ===========

GetConversationRequest
----------------------

=================================== ========================= ======== ===================================
Field                               Type                      Label    Description                        
=================================== ========================= ======== ===================================
:code:`request_header`              `RequestHeader`_          optional                                    
:code:`conversation_spec`           `ConversationSpec`_       optional                                    
:code:`include_event`               bool                      optional include_conversation_metadata? = 3;
:code:`max_events_per_conversation` uint64                    optional unknown = 5;                       
:code:`event_continuation_token`    `EventContinuationToken`_ optional                                    
=================================== ========================= ======== ===================================

GetConversationResponse
-----------------------

========================== ==================== ======== ===========
Field                      Type                 Label    Description
========================== ==================== ======== ===========
:code:`response_header`    `ResponseHeader`_    optional            
:code:`conversation_state` `ConversationState`_ optional TODO       
========================== ==================== ======== ===========

GetEntityByIdRequest
--------------------

========================= =================== ======== ============
Field                     Type                Label    Description 
========================= =================== ======== ============
:code:`request_header`    `RequestHeader`_    optional             
:code:`batch_lookup_spec` `EntityLookupSpec`_ repeated unknown = 2;
========================= =================== ======== ============

GetEntityByIdResponse
---------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional TODO       
:code:`entity`          `Entity`_         repeated            
======================= ================= ======== ===========

GetSuggestedEntitiesRequest
---------------------------

====================== ================ ======== ===========
Field                  Type             Label    Description
====================== ================ ======== ===========
:code:`request_header` `RequestHeader`_ optional TODO       
====================== ================ ======== ===========

GetSuggestedEntitiesResponse
----------------------------

======================= =========================================== ======== ===========
Field                   Type                                        Label    Description
======================= =========================================== ======== ===========
:code:`response_header` `ResponseHeader`_                           optional TODO       
:code:`entity`          `Entity`_                                   repeated            
:code:`group1`          `GetSuggestedEntitiesResponse.EntityGroup`_ optional            
:code:`group2`          `GetSuggestedEntitiesResponse.EntityGroup`_ optional            
:code:`group3`          `GetSuggestedEntitiesResponse.EntityGroup`_ optional            
:code:`group4`          `GetSuggestedEntitiesResponse.EntityGroup`_ optional            
:code:`group5`          `GetSuggestedEntitiesResponse.EntityGroup`_ optional            
:code:`group6`          `GetSuggestedEntitiesResponse.EntityGroup`_ optional            
======================= =========================================== ======== ===========

GetSuggestedEntitiesResponse.EntityGroup
----------------------------------------

more entities in 4, 5, 6, 7, 8, 9
TODO: wtf is with these extra entities

============== =============================================== ======== ================================
Field          Type                                            Label    Description                     
============== =============================================== ======== ================================
:code:`entity` `GetSuggestedEntitiesResponse.EntityGroup.Foo`_ repeated unknown 0 = 1; unknown code = 2;
============== =============================================== ======== ================================

GetSuggestedEntitiesResponse.EntityGroup.Foo
--------------------------------------------

============== ========= ======== ===========
Field          Type      Label    Description
============== ========= ======== ===========
:code:`entity` `Entity`_ optional            
============== ========= ======== ===========

GetSelfInfoRequest
------------------

====================== ================ ======== ===========
Field                  Type             Label    Description
====================== ================ ======== ===========
:code:`request_header` `RequestHeader`_ optional TODO       
====================== ================ ======== ===========

GetSelfInfoResponse
-------------------

=========================== ==================== ======== ==============================
Field                       Type                 Label    Description                   
=========================== ==================== ======== ==============================
:code:`response_header`     `ResponseHeader`_    optional                               
:code:`self_entity`         `Entity`_            optional                               
:code:`configuration_bit`   `ConfigurationBit`_  repeated                               
:code:`rich_presence_state` `RichPresenceState`_ optional TODO: all kinds of extra stuff
=========================== ==================== ======== ==============================

QueryPresenceRequest
--------------------

====================== ================ ======== ===========
Field                  Type             Label    Description
====================== ================ ======== ===========
:code:`request_header` `RequestHeader`_ optional            
:code:`user_id`        `UserID`_        repeated            
:code:`field_mask`     `FieldMask`_     repeated            
====================== ================ ======== ===========

QueryPresenceResponse
---------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`presence_result` `PresenceResult`_ repeated            
======================= ================= ======== ===========

RemoveUserRequest
-----------------

============================ ===================== ======== ===========
Field                        Type                  Label    Description
============================ ===================== ======== ===========
:code:`request_header`       `RequestHeader`_      optional            
:code:`event_request_header` `EventRequestHeader`_ optional            
============================ ===================== ======== ===========

RemoveUserResponse
------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`created_event`   `Event`_          optional            
======================= ================= ======== ===========

RenameConversationRequest
-------------------------

============================ ===================== ======== ===========
Field                        Type                  Label    Description
============================ ===================== ======== ===========
:code:`request_header`       `RequestHeader`_      optional            
:code:`new_name`             string                optional TODO       
:code:`event_request_header` `EventRequestHeader`_ optional            
============================ ===================== ======== ===========

RenameConversationResponse
--------------------------

======================= ================= ======== =============================
Field                   Type              Label    Description                  
======================= ================= ======== =============================
:code:`response_header` `ResponseHeader`_ optional TODO                         
:code:`created_event`   `Event`_          optional TODO: use json to check name?
======================= ================= ======== =============================

SearchEntitiesRequest
---------------------

====================== ================ ======== ===========
Field                  Type             Label    Description
====================== ================ ======== ===========
:code:`request_header` `RequestHeader`_ optional            
:code:`query`          string           optional            
:code:`max_count`      uint64           optional            
====================== ================ ======== ===========

SearchEntitiesResponse
----------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`entity`          `Entity`_         repeated            
======================= ================= ======== ===========

SendChatMessageRequest
----------------------

============================ ===================== ======== ================
Field                        Type                  Label    Description     
============================ ===================== ======== ================
:code:`request_header`       `RequestHeader`_      optional TODO: incomplete
:code:`message_content`      `MessageContent`_     optional                 
:code:`existing_media`       `ExistingMedia`_      optional                 
:code:`event_request_header` `EventRequestHeader`_ optional                 
============================ ===================== ======== ================

SendChatMessageResponse
-----------------------

======================= ================= ======== ===============
Field                   Type              Label    Description    
======================= ================= ======== ===============
:code:`response_header` `ResponseHeader`_ optional                
:code:`created_event`   `Event`_          optional unknown [] = 4;
======================= ================= ======== ===============

SetActiveClientRequest
----------------------

====================== ================ ======== ===============================================================
Field                  Type             Label    Description                                                    
====================== ================ ======== ===============================================================
:code:`request_header` `RequestHeader`_ optional                                                                
:code:`is_active`      bool             optional Whether to set the client as active (true) or inactive (false).
:code:`full_jid`       string           optional 'email/resource'                                               
:code:`timeout_secs`   uint64           optional Timeout in seconds for client to remain active.                
====================== ================ ======== ===============================================================

SetActiveClientResponse
-----------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
======================= ================= ======== ===========

SetConversationLevelRequest
---------------------------

====================== ================ ======== ===========
Field                  Type             Label    Description
====================== ================ ======== ===========
:code:`request_header` `RequestHeader`_ optional TODO       
====================== ================ ======== ===========

SetConversationLevelResponse
----------------------------

===== ==== ===== ===========
Field Type Label Description
===== ==== ===== ===========
===== ==== ===== ===========

SetConversationNotificationLevelRequest
---------------------------------------

======================= ==================== ======== ===========
Field                   Type                 Label    Description
======================= ==================== ======== ===========
:code:`request_header`  `RequestHeader`_     optional            
:code:`conversation_id` `ConversationID`_    optional            
:code:`level`           `NotificationLevel`_ optional            
======================= ==================== ======== ===========

SetConversationNotificationLevelResponse
----------------------------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`timestamp`       uint64            optional            
======================= ================= ======== ===========

SetFocusRequest
---------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`request_header`  `RequestHeader`_  optional            
:code:`conversation_id` `ConversationID`_ optional            
:code:`type`            `FocusType`_      optional            
:code:`timeout_secs`    uint32            optional            
======================= ================= ======== ===========

SetFocusResponse
----------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`timestamp`       uint64            optional            
======================= ================= ======== ===========

SetPresenceRequest
------------------

============================== ======================= ======== ====================================================
Field                          Type                    Label    Description                                         
============================== ======================= ======== ====================================================
:code:`request_header`         `RequestHeader`_        optional                                                     
:code:`presence_state_setting` `PresenceStateSetting`_ optional One or more of the following field may be specified:
:code:`dnd_setting`            `DndSetting`_           optional                                                     
:code:`desktop_off_setting`    `DesktopOffSetting`_    optional                                                     
:code:`mood_setting`           `MoodSetting`_          optional                                                     
============================== ======================= ======== ====================================================

SetPresenceResponse
-------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
======================= ================= ======== ===========

SetTypingRequest
----------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`request_header`  `RequestHeader`_  optional            
:code:`conversation_id` `ConversationID`_ optional            
:code:`type`            `TypingType`_     optional            
======================= ================= ======== ===========

SetTypingResponse
-----------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
:code:`timestamp`       uint64            optional            
======================= ================= ======== ===========

SyncAllNewEventsRequest
-----------------------

=============================== ================ ======== ==============================================
Field                           Type             Label    Description                                   
=============================== ================ ======== ==============================================
:code:`request_header`          `RequestHeader`_ optional                                               
:code:`last_sync_timestamp`     uint64           optional timestamp after which to return all new events
:code:`max_response_size_bytes` uint64           optional TODO                                          
=============================== ================ ======== ==============================================

SyncAllNewEventsResponse
------------------------

========================== ==================== ======== ===========
Field                      Type                 Label    Description
========================== ==================== ======== ===========
:code:`response_header`    `ResponseHeader`_    optional            
:code:`sync_timestamp`     uint64               optional            
:code:`conversation_state` `ConversationState`_ repeated TODO       
========================== ==================== ======== ===========

SyncRecentConversationsRequest
------------------------------

=================================== ================ ======== ===========
Field                               Type             Label    Description
=================================== ================ ======== ===========
:code:`request_header`              `RequestHeader`_ optional            
:code:`max_conversations`           uint64           optional            
:code:`max_events_per_conversation` uint64           optional            
:code:`sync_filter`                 `SyncFilter`_    repeated            
=================================== ================ ======== ===========

SyncRecentConversationsResponse
-------------------------------

========================== ==================== ======== ===========
Field                      Type                 Label    Description
========================== ==================== ======== ===========
:code:`response_header`    `ResponseHeader`_    optional            
:code:`sync_timestamp`     uint64               optional            
:code:`conversation_state` `ConversationState`_ repeated            
========================== ==================== ======== ===========

UpdateWatermarkRequest
----------------------

=========================== ================= ======== ===========
Field                       Type              Label    Description
=========================== ================= ======== ===========
:code:`request_header`      `RequestHeader`_  optional            
:code:`conversation_id`     `ConversationID`_ optional            
:code:`last_read_timestamp` uint64            optional            
=========================== ================= ======== ===========

UpdateWatermarkResponse
-----------------------

======================= ================= ======== ===========
Field                   Type              Label    Description
======================= ================= ======== ===========
:code:`response_header` `ResponseHeader`_ optional            
======================= ================= ======== ===========

ActiveClientState
-----------------

Describes which Hangouts client is active.

============================== ====== =========================
Name                           Number Description              
============================== ====== =========================
:code:`NO_ACTIVE_CLIENT`       0      No client is active.     
:code:`IS_ACTIVE_CLIENT`       1      This client is active.   
:code:`OTHER_CLIENT_IS_ACTIVE` 2      Another client is active.
============================== ====== =========================

FocusType
---------

================= ====== ===========
Name              Number Description
================= ====== ===========
:code:`UNKNOWN`   0                 
:code:`FOCUSED`   1                 
:code:`UNFOCUSED` 2                 
================= ====== ===========

FocusDevice
-----------

=================== ====== ===========
Name                Number Description
=================== ====== ===========
:code:`UNSPECIFIED` 0                 
:code:`DESKTOP`     20                
:code:`MOBILE`      300               
=================== ====== ===========

TypingType
----------

====================== ====== ====================================
Name                   Number Description                         
====================== ====== ====================================
:code:`TYPING_UNKNOWN` 0                                          
:code:`TYPING_STARTED` 1      started typing                      
:code:`TYPING_PAUSED`  2      stopped typing with inputted text   
:code:`TYPING_STOPPED` 3      stopped typing with no inputted text
====================== ====== ====================================

ClientPresenceStateType
-----------------------

============================================ ====== ===========
Name                                         Number Description
============================================ ====== ===========
:code:`CLIENT_PRESENCE_STATE_UNKNOWN`        0                 
:code:`CLIENT_PRESENCE_STATE_NONE`           1                 
:code:`CLIENT_PRESENCE_STATE_DESKTOP_IDLE`   30                
:code:`CLIENT_PRESENCE_STATE_DESKTOP_ACTIVE` 40     TODO       
============================================ ====== ===========

NotificationLevel
-----------------

================================== ====== ===========
Name                               Number Description
================================== ====== ===========
:code:`NOTIFICATION_LEVEL_UNKNOWN` 0                 
:code:`QUIET`                      10                
:code:`RING`                       30                
================================== ====== ===========

SegmentType
-----------

================== ====== ===========
Name               Number Description
================== ====== ===========
:code:`TEXT`       0                 
:code:`LINE_BREAK` 1                 
:code:`LINK`       2                 
================== ====== ===========

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

====================================== ====== ===========
Name                                   Number Description
====================================== ====== ===========
:code:`OFF_THE_RECORD_TOGGLE_ENABLED`  0                 
:code:`OFF_THE_RECORD_TOGGLE_DISABLED` 1                 
====================================== ====== ===========

OffTheRecordStatus
------------------

===================================== ====== ===========
Name                                  Number Description
===================================== ====== ===========
:code:`OFF_THE_RECORD_STATUS_UNKNOWN` 0                 
:code:`OFF_THE_RECORD`                1                 
:code:`ON_THE_RECORD`                 2                 
===================================== ====== ===========

SourceType
----------

=========================== ====== ===========
Name                        Number Description
=========================== ====== ===========
:code:`SOURCE_TYPE_UNKNOWN` 0                 
=========================== ====== ===========

EventType
---------

======================================= ====== ===========
Name                                    Number Description
======================================= ====== ===========
:code:`EVENT_TYPE_UNKNOWN`              0                 
:code:`EVENT_TYPE_REGULAR_CHAT_MESSAGE` 1                 
:code:`EVENT_TYPE_ADD_USER`             4                 
:code:`EVENT_TYPE_REMOVE_USER`          5                 
:code:`EVENT_TYPE_CONVERSATION_RENAME`  6                 
:code:`EVENT_TYPE_HANGOUT`              7                 
:code:`EVENT_TYPE_OTR_MODIFICATION`     9                 
======================================= ====== ===========

ConversationType
----------------

================================= ====== ===========
Name                              Number Description
================================= ====== ===========
:code:`CONVERSATION_TYPE_UNKNOWN` 0                 
:code:`ONE_TO_ONE`                1                 
:code:`GROUP`                     2                 
================================= ====== ===========

ConversationStatus
------------------

=================================== ====== ===========
Name                                Number Description
=================================== ====== ===========
:code:`UNKNOWN_CONVERSATION_STATUS` 0                 
:code:`INVITED`                     1                 
:code:`ACTIVE`                      2                 
:code:`LEFT`                        3                 
=================================== ====== ===========

ConversationView
----------------

================================= ====== ===========
Name                              Number Description
================================= ====== ===========
:code:`UNKNOWN_CONVERSATION_VIEW` 0                 
:code:`INBOX_VIEW`                1                 
:code:`ARCHIVED_VIEW`             2                 
================================= ====== ===========

DeliveryMediumType
------------------

=============================== ====== ===========
Name                            Number Description
=============================== ====== ===========
:code:`DELIVERY_MEDIUM_UNKNOWN` 0                 
:code:`DELIVERY_MEDIUM_BABEL`   1                 
=============================== ====== ===========

ParticipantType
---------------

================================ ====== ===========
Name                             Number Description
================================ ====== ===========
:code:`PARTICIPANT_TYPE_UNKNOWN` 0                 
:code:`PARTICIPANT_TYPE_GAIA`    2                 
================================ ====== ===========

BlockState
----------

=========================== ====== ===========
Name                        Number Description
=========================== ====== ===========
:code:`BLOCK_STATE_UNKNOWN` 0                 
:code:`BLOCK`               1                 
:code:`UNBLOCK`             2                 
=========================== ====== ===========

ReplyToInviteType
-----------------

==================================== ====== ===========
Name                                 Number Description
==================================== ====== ===========
:code:`REPLY_TO_INVITE_TYPE_UNKNOWN` 0                 
:code:`ACCEPT`                       1                 
:code:`DECLINE`                      2                 
==================================== ====== ===========

ClientId
--------

============================= ====== =====================================
Name                          Number Description                          
============================= ====== =====================================
:code:`CLIENT_ID_UNKNOWN`     0                                           
:code:`CLIENT_ID_ANDROID`     1      Hangouts app for Android             
:code:`CLIENT_ID_IOS`         2      Hangouts app for iOS                 
:code:`CLIENT_ID_CHROME`      3      Hangouts Chrome extension            
:code:`CLIENT_ID_WEB_GPLUS`   5      Hangouts web interface in Google Plus
:code:`CLIENT_ID_WEB_GMAIL`   6      Hangouts web interface in Gmail      
:code:`CLIENT_ID_ULTRAVIOLET` 13     Hangouts Chrome app ("ultraviolet")  
============================= ====== =====================================

ClientBuildType
---------------

================================= ====== =======================================================================================
Name                              Number Description                                                                            
================================= ====== =======================================================================================
:code:`BUILD_TYPE_UNKNOWN`        0                                                                                             
:code:`BUILD_TYPE_PRODUCTION_WEB` 1      build type used by web apps                                                            
:code:`BUILD_TYPE_PRODUCTION_APP` 3      built type used by native apps hangups used to use this, but web apps seem to use 1 now
================================= ====== =======================================================================================

ResponseStatus
--------------

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

==================================== ====== ====================================
Name                                 Number Description                         
==================================== ====== ====================================
:code:`PHOTO_URL_STATUS_UNKNOWN`     0                                          
:code:`PHOTO_URL_STATUS_PLACEHOLDER` 1      photo_url is a placeholder          
:code:`PHOTO_URL_STATUS_USER_PHOTO`  2      photo_url is a photo set by the user
==================================== ====== ====================================

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

========================================= ====== ==============================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================
Name                                      Number Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
========================================= ====== ==============================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN`    0      TODO RICH_PRESENCE_ACTIVITY_PROMO_SHOWN RICH_PRESENCE_DEVICE_PROMO_SHOWN RICH_PRESENCE_LAST_SEEN_DESKTOP_PROMO_SHOWN RICH_PRESENCE_LAST_SEEN_MOBILE_PROMO_SHOWN RICH_PRESENCE_IN_CALL_STATE_PROMO_SHOWN RICH_PRESENCE_MOOD_PROMO_SHOWN GV_SMS_INTEGRATION_PROMO_SHOWN RICH_PRESENCE_LAST_SEEN_DESKTOP_PROMPT_SHOWN BUSINESS_FEATURES_ENABLED BUSINESS_FEATURES_PROMO_DISMISSED CONVERSATION_INVITE_SETTINGS_SET_TO_CUSTOM REPORT_ABUSE_NOTICE_ACKNOWLEDGED PHONE_VERIFICATION_MOBILE_PROMPT_SHOWN HANGOUT_P2P_NOTICE_ACKNOWLEDGED HANGOUT_P2P_ENABLED INVITE_NOTIFICATIONS_ENABLED DESKTOP_AUTO_EMOJI_CONVERSION_ENABLED ALLOWED_FOR_DOMAIN GMAIL_CHAT_ARCHIVE_ENABLED QUASAR_MARKETING_PROMO_DISMISSED GPLUS_SIGNUP_PROMO_DISMISSED GPLUS_UPGRADE_ALLOWED_FOR_DOMAIN CHAT_WITH_CIRCLES_ACCEPTED CHAT_WITH_CIRCLES_PROMO_DISMISSED PHOTO_SERVICE_REGISTERED GV_SMS_INTEGRATION_ENABLED CAN_OPT_INTO_GV_SMS_INTEGRATION BUSINESS_FEATURES_ELIGIBLE CAN_USE_GV_CALLER_ID_FEATURE
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_1`  1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_2`  2                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_3`  3                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_4`  4                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_5`  5                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_6`  6                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_7`  7                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_8`  8                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_9`  9                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_10` 10                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_11` 11                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_12` 12                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_13` 13                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_14` 14                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_15` 15                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_16` 16                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_17` 17                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_18` 18                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_19` 19                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_20` 20                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_21` 21                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_22` 22                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_23` 23                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_24` 24                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_25` 25                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_26` 26                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_27` 27                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_28` 28                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_29` 29                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_30` 30                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_31` 31                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_32` 32                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_33` 33                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
:code:`CONFIGURATION_BIT_TYPE_UNKNOWN_34` 34                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   
========================================= ====== ==============================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================

RichPresenceType
----------------

======================== ====== ============================================
Name                     Number Description                                 
======================== ====== ============================================
:code:`RP_TYPE_UNKNOWN`  0                                                  
:code:`RP_IN_CALL_STATE` 1                                                  
:code:`RP_UNKNOWN_3`     3      TODO RP_GLOBALLY_ENABLED RP_ACTIVITY RP_MOOD
:code:`RP_UNKNOWN_4`     4                                                  
:code:`RP_UNKNOWN_5`     5                                                  
:code:`RP_DEVICE`        2                                                  
:code:`RP_LAST_SEEN`     6                                                  
======================== ====== ============================================

FieldMask
---------

============================ ====== ===========
Name                         Number Description
============================ ====== ===========
:code:`FIELD_MASK_REACHABLE` 1                 
:code:`FIELD_MASK_AVAILABLE` 2                 
:code:`FIELD_MASK_DEVICE`    7                 
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
:code:`SYNC_FILTER_ARCHIVED` 2      TODO       
============================ ====== ===========

