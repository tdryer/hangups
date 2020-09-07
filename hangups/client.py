"""Abstract class for writing chat clients."""

import asyncio
import base64
import binascii
import collections
import json
import logging
import os
import random
import time

import google.protobuf.message

from hangups import (exceptions, http_utils, channel, event, hangouts_pb2,
                     pblite, version)

logger = logging.getLogger(__name__)
IMAGE_UPLOAD_URL = 'https://docs.google.com/upload/photos/resumable'
# Timeout to send for setactiveclient requests:
ACTIVE_TIMEOUT_SECS = 120
# Minimum timeout between subsequent setactiveclient requests:
SETACTIVECLIENT_LIMIT_SECS = 60
# API key for `key` parameter (from Hangouts web client)
API_KEY = 'AIzaSyD7InnYR3VKdb4j2rMUEbTCIr2VyEazl6k'
# Base URL for API requests:
BASE_URL = 'https://chat-pa.clients6.google.com'


class Client:
    """Instant messaging client for Hangouts.

    Maintains a connections to the servers, emits events, and accepts commands.

    Args:
        cookies (dict): Google session cookies. Get these using
            :func:`get_auth`.
        max_retries (int): (optional) Maximum number of connection attempts
            hangups will make before giving up. Defaults to 5.
        retry_backoff_base (int): (optional) The base term for the exponential
            backoff. The following equation is used when calculating the number
            of seconds to wait prior to each retry:
            retry_backoff_base^(# of retries attempted thus far)
            Defaults to 2.
    """

    def __init__(self, cookies, max_retries=5, retry_backoff_base=2):
        self._max_retries = max_retries
        self._retry_backoff_base = retry_backoff_base

        self.on_connect = event.Event('Client.on_connect')
        """
        :class:`.Event` fired when the client connects for the first time.
        """

        self.on_reconnect = event.Event('Client.on_reconnect')
        """
        :class:`.Event` fired when the client reconnects after being
        disconnected.
        """

        self.on_disconnect = event.Event('Client.on_disconnect')
        """
        :class:`.Event` fired when the client is disconnected.
        """

        self.on_state_update = event.Event('Client.on_state_update')
        """
        :class:`.Event` fired when an update arrives from the server.

        Args:
            state_update: A ``StateUpdate`` message.
        """

        # http_utils.Session instance (populated by .connect()):
        self._session = None

        # Cookies required to initialize Session:
        self._cookies = cookies

        # channel.Channel instance (populated by .connect()):
        self._channel = None

        # Future for Channel.listen (populated by .connect()):
        self._listen_future = None

        self._request_header = hangouts_pb2.RequestHeader(
            # Ignore most of the RequestHeader fields since they aren't
            # required. Sending a recognized client_id is important because it
            # changes the behaviour of some APIs (eg. get_conversation will
            # filter out EVENT_TYPE_GROUP_LINK_SHARING_MODIFICATION without
            # it).
            client_version=hangouts_pb2.ClientVersion(
                client_id=hangouts_pb2.CLIENT_ID_WEB_HANGOUTS,
                major_version='hangups-{}'.format(version.__version__),
            ),
            language_code='en',
        )

        # String identifying this client (populated later):
        self._client_id = None

        # String email address for this account (populated later):
        self._email = None

        # Active client management parameters:
        # Time in seconds that the client as last set as active:
        self._last_active_secs = 0.0
        # ActiveClientState enum int value or None:
        self._active_client_state = None

    ##########################################################################
    # Public methods
    ##########################################################################

    async def connect(self):
        """Establish a connection to the chat server.

        Returns when an error has occurred, or :func:`disconnect` has been
        called.
        """
        proxy = os.environ.get('HTTP_PROXY')
        self._session = http_utils.Session(self._cookies, proxy=proxy)
        try:
            self._channel = channel.Channel(
                self._session, self._max_retries, self._retry_backoff_base
            )

            # Forward the Channel events to the Client events.
            self._channel.on_connect.add_observer(self.on_connect.fire)
            self._channel.on_reconnect.add_observer(self.on_reconnect.fire)
            self._channel.on_disconnect.add_observer(self.on_disconnect.fire)
            self._channel.on_receive_array.add_observer(self._on_receive_array)

            # Wrap the coroutine in a Future so it can be cancelled.
            self._listen_future = asyncio.ensure_future(self._channel.listen())
            # Listen for StateUpdate messages from the Channel until it
            # disconnects.
            try:
                await self._listen_future
            except asyncio.CancelledError:
                # If this task is cancelled, we need to cancel our child task
                # as well. We don't need an additional yield because listen
                # cancels immediately.
                self._listen_future.cancel()
            logger.info(
                'Client.connect returning because Channel.listen returned'
            )
        finally:
            await self._session.close()

    async def disconnect(self):
        """Gracefully disconnect from the server.

        When disconnection is complete, :func:`connect` will return.
        """
        logger.info('Graceful disconnect requested')
        # Cancel the listen task. We don't need an additional yield because
        # listen cancels immediately.
        self._listen_future.cancel()

    def get_request_header(self):
        """Return ``request_header`` for use when constructing requests.

        Returns:
            Populated request header.
        """
        # resource is allowed to be null if it's not available yet (the Chrome
        # client does this for the first getentitybyid call)
        if self._client_id is not None:
            self._request_header.client_identifier.resource = self._client_id
        return self._request_header

    @staticmethod
    def get_client_generated_id():
        """Return ``client_generated_id`` for use when constructing requests.

        Returns:
            Client generated ID.
        """
        return random.randint(0, 2**32)

    async def set_active(self):
        """Set this client as active.

        While a client is active, no other clients will raise notifications.
        Call this method whenever there is an indication the user is
        interacting with this client. This method may be called very
        frequently, and it will only make a request when necessary.
        """
        is_active = (self._active_client_state ==
                     hangouts_pb2.ACTIVE_CLIENT_STATE_IS_ACTIVE)
        timed_out = (time.time() - self._last_active_secs >
                     SETACTIVECLIENT_LIMIT_SECS)
        if not is_active or timed_out:
            # Update these immediately so if the function is called again
            # before the API request finishes, we don't start extra requests.
            self._active_client_state = (
                hangouts_pb2.ACTIVE_CLIENT_STATE_IS_ACTIVE
            )
            self._last_active_secs = time.time()

            # The first time this is called, we need to retrieve the user's
            # email address.
            if self._email is None:
                try:
                    get_self_info_request = hangouts_pb2.GetSelfInfoRequest(
                        request_header=self.get_request_header(),
                    )
                    get_self_info_response = await self.get_self_info(
                        get_self_info_request
                    )
                except exceptions.NetworkError as e:
                    logger.warning('Failed to find email address: {}'
                                   .format(e))
                    return
                self._email = (
                    get_self_info_response.self_entity.properties.email[0]
                )

            # If the client_id hasn't been received yet, we can't set the
            # active client.
            if self._client_id is None:
                logger.info(
                    'Cannot set active client until client_id is received'
                )
                return

            try:
                set_active_request = hangouts_pb2.SetActiveClientRequest(
                    request_header=self.get_request_header(),
                    is_active=True,
                    full_jid="{}/{}".format(self._email, self._client_id),
                    timeout_secs=ACTIVE_TIMEOUT_SECS,
                )
                await self.set_active_client(set_active_request)
            except exceptions.NetworkError as e:
                logger.warning('Failed to set active client: {}'.format(e))
            else:
                logger.info('Set active client for {} seconds'
                            .format(ACTIVE_TIMEOUT_SECS))

    async def upload_image(self, image_file, filename=None, *,
                           return_uploaded_image=False):
        """Upload an image that can be later attached to a chat message.

        Args:
            image_file: A file-like object containing an image.
            filename (str): (optional) Custom name for the uploaded file.
            return_uploaded_image (bool): (optional) If True, return
                :class:`.UploadedImage` instead of image ID. Defaults to False.

        Raises:
            hangups.NetworkError: If the upload request failed.

        Returns:
            :class:`.UploadedImage` instance, or ID of the uploaded image.
        """
        image_filename = filename or os.path.basename(image_file.name)
        image_data = image_file.read()

        # request an upload URL
        res = await self._base_request(
            IMAGE_UPLOAD_URL,
            'application/x-www-form-urlencoded;charset=UTF-8', 'json',
            json.dumps({
                "protocolVersion": "0.8",
                "createSessionRequest": {
                    "fields": [{
                        "external": {
                            "name": "file",
                            "filename": image_filename,
                            "put": {},
                            "size": len(image_data)
                        }
                    }]
                }
            })
        )

        try:
            upload_url = self._get_upload_session_status(res)[
                'externalFieldTransfers'
            ][0]['putInfo']['url']
        except KeyError:
            raise exceptions.NetworkError(
                'image upload failed: can not acquire an upload url'
            )

        # upload the image data using the upload_url to get the upload info
        res = await self._base_request(
            upload_url, 'application/octet-stream', 'json', image_data
        )

        try:
            raw_info = (
                self._get_upload_session_status(res)['additionalInfo']
                ['uploader_service.GoogleRupioAdditionalInfo']
                ['completionInfo']['customerSpecificInfo']
            )
            image_id = raw_info['photoid']
            url = raw_info['url']
        except KeyError:
            raise exceptions.NetworkError(
                'image upload failed: can not fetch upload info'
            )

        result = UploadedImage(image_id=image_id, url=url)
        return result if return_uploaded_image else result.image_id

    ##########################################################################
    # Private methods
    ##########################################################################

    @staticmethod
    def _get_upload_session_status(res):
        """Parse the image upload response to obtain status.

        Args:
            res: http_utils.FetchResponse instance, the upload response

        Returns:
            dict, sessionStatus of the response

        Raises:
            hangups.NetworkError: If the upload request failed.
        """
        response = json.loads(res.body.decode())
        if 'sessionStatus' not in response:
            try:
                info = (
                    response['errorMessage']['additionalInfo']
                    ['uploader_service.GoogleRupioAdditionalInfo']
                    ['completionInfo']['customerSpecificInfo']
                )
                reason = '{} : {}'.format(info['status'], info['message'])
            except KeyError:
                reason = 'unknown reason'
            raise exceptions.NetworkError('image upload failed: {}'.format(
                reason
            ))
        return response['sessionStatus']

    async def _on_receive_array(self, array):
        """Parse channel array and call the appropriate events."""
        if array[0] == 'noop':
            pass  # This is just a keep-alive, ignore it.
        else:
            wrapper = json.loads(array[0]['p'])
            # Wrapper appears to be a Protocol Buffer message, but encoded via
            # field numbers as dictionary keys. Since we don't have a parser
            # for that, parse it ad-hoc here.
            if '3' in wrapper:
                # This is a new client_id.
                self._client_id = wrapper['3']['2']
                logger.info('Received new client_id: %r', self._client_id)
                # Once client_id is received, the channel is ready to have
                # services added.
                await self._add_channel_services()
            if '2' in wrapper:
                pblite_message = json.loads(wrapper['2']['2'])
                if pblite_message[0] == 'cbu':
                    # This is a (Client)BatchUpdate containing StateUpdate
                    # messages.
                    batch_update = hangouts_pb2.BatchUpdate()
                    pblite.decode(batch_update, pblite_message,
                                  ignore_first_item=True)
                    for state_update in batch_update.state_update:
                        logger.debug('Received StateUpdate:\n%s', state_update)
                        header = state_update.state_update_header
                        self._active_client_state = header.active_client_state
                        await self.on_state_update.fire(state_update)
                else:
                    logger.info('Ignoring message: %r', pblite_message[0])

    async def _add_channel_services(self):
        """Add services to the channel.

        The services we add to the channel determine what kind of data we will
        receive on it.

        The "babel" service includes what we need for Hangouts. If this fails
        for some reason, hangups will never receive any events. The
        "babel_presence_last_seen" service is also required to receive presence
        notifications.

        This needs to be re-called whenever we open a new channel (when there's
        a new SID and client_id.
        """
        logger.info('Adding channel services...')
        # Based on what Hangouts for Chrome does over 2 requests, this is
        # trimmed down to 1 request that includes the bare minimum to make
        # things work.
        services = ["babel", "babel_presence_last_seen"]
        map_list = [
            dict(p=json.dumps({"3": {"1": {"1": service}}}))
            for service in services
        ]
        await self._channel.send_maps(map_list)
        logger.info('Channel services added')

    async def _pb_request(self, endpoint, request_pb, response_pb):
        """Send a Protocol Buffer formatted chat API request.

        Args:
            endpoint (str): The chat API endpoint to use.
            request_pb: The request body as a Protocol Buffer message.
            response_pb: The response body as a Protocol Buffer message.

        Raises:
            NetworkError: If the request fails.
        """
        logger.debug('Sending Protocol Buffer request %s:\n%s', endpoint,
                     request_pb)
        res = await self._base_request(
            '{}/chat/v1/{}'.format(BASE_URL, endpoint),
            'application/x-protobuf',  # Request body is Protocol Buffer.
            'proto',  # Response body is Protocol Buffer.
            request_pb.SerializeToString()
        )
        try:
            response_pb.ParseFromString(base64.b64decode(res.body))
        except binascii.Error as e:
            raise exceptions.NetworkError(
                'Failed to decode base64 response: {}'.format(e)
            )
        except google.protobuf.message.DecodeError as e:
            raise exceptions.NetworkError(
                'Failed to decode Protocol Buffer response: {}'.format(e)
            )
        logger.debug('Received Protocol Buffer response:\n%s', response_pb)
        status = response_pb.response_header.status
        if status != hangouts_pb2.RESPONSE_STATUS_OK:
            description = response_pb.response_header.error_description
            raise exceptions.NetworkError(
                'Request failed with status {}: \'{}\''
                .format(status, description)
            )

    async def _base_request(self, url, content_type, response_type, data):
        """Send a generic authenticated POST request.

        Args:
            url (str): URL of request.
            content_type (str): Request content type.
            response_type (str): The desired response format. Valid options
                are: 'json' (JSON), 'protojson' (pblite), and 'proto' (binary
                Protocol Buffer). 'proto' requires manually setting an extra
                header 'X-Goog-Encode-Response-If-Executable: base64'.
            data (str): Request body data.

        Returns:
            FetchResponse: Response containing HTTP code, cookies, and body.

        Raises:
            NetworkError: If the request fails.
        """
        headers = {
            'content-type': content_type,
            # This header is required for Protocol Buffer responses. It causes
            # them to be base64 encoded:
            'X-Goog-Encode-Response-If-Executable': 'base64',
        }
        params = {
            # "alternative representation type" (desired response format).
            'alt': response_type,
            # API key (required to avoid 403 Forbidden "Daily Limit for
            # Unauthenticated Use Exceeded. Continued use requires signup").
            'key': API_KEY,
        }
        res = await self._session.fetch(
            'post', url, headers=headers, params=params, data=data,
        )
        return res

    ###########################################################################
    # API request methods - wrappers for self._pb_request for calling
    # particular APIs.
    ###########################################################################

    async def add_user(self, add_user_request):
        """Invite users to join an existing group conversation."""
        response = hangouts_pb2.AddUserResponse()
        await self._pb_request('conversations/adduser',
                               add_user_request, response)
        return response

    async def create_conversation(self, create_conversation_request):
        """Create a new conversation."""
        response = hangouts_pb2.CreateConversationResponse()
        await self._pb_request('conversations/createconversation',
                               create_conversation_request, response)
        return response

    async def delete_conversation(self, delete_conversation_request):
        """Leave a one-to-one conversation.

        One-to-one conversations are "sticky"; they can't actually be deleted.
        This API clears the event history of the specified conversation up to
        ``delete_upper_bound_timestamp``, hiding it if no events remain.
        """
        response = hangouts_pb2.DeleteConversationResponse()
        await self._pb_request('conversations/deleteconversation',
                               delete_conversation_request, response)
        return response

    async def easter_egg(self, easter_egg_request):
        """Send an easter egg event to a conversation."""
        response = hangouts_pb2.EasterEggResponse()
        await self._pb_request('conversations/easteregg',
                               easter_egg_request, response)
        return response

    async def get_conversation(self, get_conversation_request):
        """Return conversation info and recent events."""
        response = hangouts_pb2.GetConversationResponse()
        await self._pb_request('conversations/getconversation',
                               get_conversation_request, response)
        return response

    async def get_entity_by_id(self, get_entity_by_id_request):
        """Return one or more user entities.

        Searching by phone number only finds entities when their phone number
        is in your contacts (and not always even then), and can't be used to
        find Google Voice contacts.
        """
        response = hangouts_pb2.GetEntityByIdResponse()
        await self._pb_request('contacts/getentitybyid',
                               get_entity_by_id_request, response)
        return response

    async def get_group_conversation_url(self,
                                         get_group_conversation_url_request):
        """Get URL to allow others to join a group conversation."""
        response = hangouts_pb2.GetGroupConversationUrlResponse()
        await self._pb_request('conversations/getgroupconversationurl',
                               get_group_conversation_url_request,
                               response)
        return response

    async def get_self_info(self, get_self_info_request):
        """Return info about the current user."""
        response = hangouts_pb2.GetSelfInfoResponse()
        await self._pb_request('contacts/getselfinfo',
                               get_self_info_request, response)
        return response

    async def get_suggested_entities(self, get_suggested_entities_request):
        """Return suggested contacts."""
        response = hangouts_pb2.GetSuggestedEntitiesResponse()
        await self._pb_request('contacts/getsuggestedentities',
                               get_suggested_entities_request, response)
        return response

    async def query_presence(self, query_presence_request):
        """Return presence status for a list of users."""
        response = hangouts_pb2.QueryPresenceResponse()
        await self._pb_request('presence/querypresence',
                               query_presence_request, response)
        return response

    async def remove_user(self, remove_user_request):
        """Remove a participant from a group conversation."""
        response = hangouts_pb2.RemoveUserResponse()
        await self._pb_request('conversations/removeuser',
                               remove_user_request, response)
        return response

    async def rename_conversation(self, rename_conversation_request):
        """Rename a conversation.

        Both group and one-to-one conversations may be renamed, but the
        official Hangouts clients have mixed support for one-to-one
        conversations with custom names.
        """
        response = hangouts_pb2.RenameConversationResponse()
        await self._pb_request('conversations/renameconversation',
                               rename_conversation_request, response)
        return response

    async def search_entities(self, search_entities_request):
        """Return user entities based on a query."""
        response = hangouts_pb2.SearchEntitiesResponse()
        await self._pb_request('contacts/searchentities',
                               search_entities_request, response)
        return response

    async def send_chat_message(self, send_chat_message_request):
        """Send a chat message to a conversation."""
        response = hangouts_pb2.SendChatMessageResponse()
        await self._pb_request('conversations/sendchatmessage',
                               send_chat_message_request, response)
        return response

    async def modify_otr_status(self, modify_otr_status_request):
        """Enable or disable message history in a conversation."""
        response = hangouts_pb2.ModifyOTRStatusResponse()
        await self._pb_request('conversations/modifyotrstatus',
                               modify_otr_status_request, response)
        return response

    async def send_offnetwork_invitation(
            self, send_offnetwork_invitation_request
    ):
        """Send an email to invite a non-Google contact to Hangouts."""
        response = hangouts_pb2.SendOffnetworkInvitationResponse()
        await self._pb_request('devices/sendoffnetworkinvitation',
                               send_offnetwork_invitation_request,
                               response)
        return response

    async def set_active_client(self, set_active_client_request):
        """Set the active client."""
        response = hangouts_pb2.SetActiveClientResponse()
        await self._pb_request('clients/setactiveclient',
                               set_active_client_request, response)
        return response

    async def set_conversation_notification_level(
            self, set_conversation_notification_level_request
    ):
        """Set the notification level of a conversation."""
        response = hangouts_pb2.SetConversationNotificationLevelResponse()
        await self._pb_request(
            'conversations/setconversationnotificationlevel',
            set_conversation_notification_level_request, response
        )
        return response

    async def set_focus(self, set_focus_request):
        """Set focus to a conversation."""
        response = hangouts_pb2.SetFocusResponse()
        await self._pb_request('conversations/setfocus',
                               set_focus_request, response)
        return response

    async def set_group_link_sharing_enabled(
            self, set_group_link_sharing_enabled_request
    ):
        """Set whether group link sharing is enabled for a conversation."""
        response = hangouts_pb2.SetGroupLinkSharingEnabledResponse()
        await self._pb_request('conversations/setgrouplinksharingenabled',
                               set_group_link_sharing_enabled_request,
                               response)
        return response

    async def set_presence(self, set_presence_request):
        """Set the presence status."""
        response = hangouts_pb2.SetPresenceResponse()
        await self._pb_request('presence/setpresence',
                               set_presence_request, response)
        return response

    async def set_typing(self, set_typing_request):
        """Set the typing status of a conversation."""
        response = hangouts_pb2.SetTypingResponse()
        await self._pb_request('conversations/settyping',
                               set_typing_request, response)
        return response

    async def sync_all_new_events(self, sync_all_new_events_request):
        """List all events occurring at or after a timestamp."""
        response = hangouts_pb2.SyncAllNewEventsResponse()
        await self._pb_request('conversations/syncallnewevents',
                               sync_all_new_events_request, response)
        return response

    async def sync_recent_conversations(
            self, sync_recent_conversations_request
    ):
        """Return info on recent conversations and their events."""
        response = hangouts_pb2.SyncRecentConversationsResponse()
        await self._pb_request('conversations/syncrecentconversations',
                               sync_recent_conversations_request,
                               response)
        return response

    async def update_watermark(self, update_watermark_request):
        """Update the watermark (read timestamp) of a conversation."""
        response = hangouts_pb2.UpdateWatermarkResponse()
        await self._pb_request('conversations/updatewatermark',
                               update_watermark_request, response)
        return response


UploadedImage = collections.namedtuple('UploadedImage', ['image_id', 'url'])
"""Details about an uploaded image.

Args:
    image_id (str): Image ID of uploaded image.
    url (str): URL of uploaded image.
"""
