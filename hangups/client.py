"""Abstract class for writing chat clients."""

import aiohttp
import asyncio
import json
import logging
import random
import time
import os

from hangups import (javascript, exceptions, http_utils, channel, event,
                     hangouts_pb2, pblite, version)

logger = logging.getLogger(__name__)
ORIGIN_URL = 'https://talkgadget.google.com'
IMAGE_UPLOAD_URL = 'http://docs.google.com/upload/photos/resumable'
# Timeout to send for setactiveclient requests:
ACTIVE_TIMEOUT_SECS = 120
# Minimum timeout between subsequent setactiveclient requests:
SETACTIVECLIENT_LIMIT_SECS = 60


class Client(object):
    """Instant messaging client for Hangouts.

    Maintains a connections to the servers, emits events, and accepts commands.
    """

    def __init__(self, cookies):
        """Create new client.

        cookies is a dictionary of authentication cookies.
        """

        # Event fired when the client connects for the first time with
        # arguments ().
        self.on_connect = event.Event('Client.on_connect')
        # Event fired when the client reconnects after being disconnected with
        # arguments ().
        self.on_reconnect = event.Event('Client.on_reconnect')
        # Event fired when the client is disconnected with arguments ().
        self.on_disconnect = event.Event('Client.on_disconnect')
        # Event fired when a StateUpdate arrives with arguments (state_update).
        self.on_state_update = event.Event('Client.on_state_update')

        self._cookies = cookies
        proxy = os.environ.get('HTTP_PROXY')
        if proxy:
            self._connector = aiohttp.ProxyConnector(proxy)
        else:
            self._connector = aiohttp.TCPConnector()

        self._channel = channel.Channel(self._cookies, self._connector)
        # Future for Channel.listen
        self._listen_future = None

        self._request_header = hangouts_pb2.RequestHeader(
            # Ignore most of the RequestHeader fields since they aren't
            # required.
            client_version=hangouts_pb2.ClientVersion(
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

    @asyncio.coroutine
    def connect(self):
        """Establish a connection to the chat server.

        Returns when an error has occurred, or Client.disconnect has been
        called.
        """
        # Forward the Channel events to the Client events.
        self._channel.on_connect.add_observer(self.on_connect.fire)
        self._channel.on_reconnect.add_observer(self.on_reconnect.fire)
        self._channel.on_disconnect.add_observer(self.on_disconnect.fire)
        self._channel.on_receive_array.add_observer(self._on_receive_array)

        # Listen for StateUpdate messages from the Channel until it
        # disconnects.
        self._listen_future = asyncio.async(self._channel.listen())
        try:
            yield from self._listen_future
        except asyncio.CancelledError:
            pass
        self._connector.close()
        logger.info('Client.connect returning because Channel.listen returned')

    @asyncio.coroutine
    def disconnect(self):
        """Gracefully disconnect from the server.

        When disconnection is complete, Client.connect will return.
        """
        logger.info('Disconnecting gracefully...')
        self._listen_future.cancel()
        try:
            yield from self._listen_future
        except asyncio.CancelledError:
            pass
        logger.info('Disconnected gracefully')

    def get_request_header(self):
        """Return populated RequestHeader message.

        Use this method for constructing request messages when calling Hangouts
        APIs.
        """
        # resource is allowed to be null if it's not available yet (the Chrome
        # client does this for the first getentitybyid call)
        if self._client_id is not None:
            self._request_header.client_identifier.resource = self._client_id
        return self._request_header

    @staticmethod
    def get_client_generated_id():
        """Return ID for client_generated_id fields.

        Use this method for constructing request messages when calling Hangouts
        APIs.
        """
        return random.randint(0, 2**32)

    @asyncio.coroutine
    def set_active(self):
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
                    request = hangouts_pb2.GetSelfInfoRequest(
                        request_header=self.get_request_header(),
                    )
                    get_self_info_response = yield from self.get_self_info(
                        request
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
                request = hangouts_pb2.SetActiveClientRequest(
                    request_header=self.get_request_header(),
                    is_active=True,
                    full_jid="{}/{}".format(self._email, self._client_id),
                    timeout_secs=ACTIVE_TIMEOUT_SECS,
                )
                yield from self.set_active_client(request)
            except exceptions.NetworkError as e:
                logger.warning('Failed to set active client: {}'.format(e))
            else:
                logger.info('Set active client for {} seconds'
                            .format(ACTIVE_TIMEOUT_SECS))

    @asyncio.coroutine
    def upload_image(self, image_file, filename=None):
        """Upload an image that can be later attached to a chat message.

        image_file is a file-like object containing an image.

        The name of the uploaded file may be changed by specifying the filename
        argument.

        Raises hangups.NetworkError if the request fails.

        Returns ID of uploaded image.
        """
        image_filename = (filename if filename
                          else os.path.basename(image_file.name))
        image_data = image_file.read()

        # Create image and request upload URL
        res1 = yield from self._base_request(
            IMAGE_UPLOAD_URL,
            'application/x-www-form-urlencoded;charset=UTF-8',
            'json',
            json.dumps({
                "protocolVersion": "0.8",
                "createSessionRequest": {
                    "fields": [{
                        "external": {
                            "name": "file",
                            "filename": image_filename,
                            "put": {},
                            "size": len(image_data),
                        }
                    }]
                }
            }))
        upload_url = (json.loads(res1.body.decode())['sessionStatus']
                      ['externalFieldTransfers'][0]['putInfo']['url'])

        # Upload image data and get image ID
        res2 = yield from self._base_request(
            upload_url, 'application/octet-stream', 'json', image_data
        )
        return (json.loads(res2.body.decode())['sessionStatus']
                ['additionalInfo']
                ['uploader_service.GoogleRupioAdditionalInfo']
                ['completionInfo']['customerSpecificInfo']['photoid'])

    ##########################################################################
    # Private methods
    ##########################################################################

    def _get_cookie(self, name):
        """Return a cookie for raise error if that cookie was not provided."""
        try:
            return self._cookies[name]
        except KeyError:
            raise KeyError("Cookie '{}' is required".format(name))

    @asyncio.coroutine
    def _on_receive_array(self, array):
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
                yield from self._add_channel_services()
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
                        yield from self.on_state_update.fire(state_update)
                else:
                    logger.info('Ignoring message: %r', pblite_message[0])

    @asyncio.coroutine
    def _add_channel_services(self):
        """Add services to the channel.

        The services we add to the channel determine what kind of data we will
        receive on it. The "babel" service includes what we need for Hangouts.
        If this fails for some reason, hangups will never receive any events.

        This needs to be re-called whenever we open a new channel (when there's
        a new SID and client_id.
        """
        logger.info('Adding channel services...')
        # Based on what Hangouts for Chrome does over 2 requests, this is
        # trimmed down to 1 request that includes the bare minimum to make
        # things work.
        map_list = [dict(p=json.dumps({"3": {"1": {"1": "babel"}}}))]
        yield from self._channel.send_maps(map_list)
        logger.info('Channel services added')

    @asyncio.coroutine
    def _pb_request(self, endpoint, request_pb, response_pb):
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
        res = yield from self._base_request(
            'https://clients6.google.com/chat/v1/{}'.format(endpoint),
            'application/json+protobuf',  # The request body is pblite.
            'protojson',  # The response should be pblite.
            json.dumps(pblite.encode(request_pb))
        )
        pblite.decode(response_pb, javascript.loads(res.body.decode()),
                      ignore_first_item=True)
        logger.debug('Received Protocol Buffer response:\n%s', response_pb)
        status = response_pb.response_header.status
        if status != hangouts_pb2.RESPONSE_STATUS_OK:
            description = response_pb.response_header.error_description
            raise exceptions.NetworkError(
                'Request failed with status {}: \'{}\''
                .format(status, description)
            )

    @asyncio.coroutine
    def _base_request(self, url, content_type, response_type, data):
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
        sapisid_cookie = self._get_cookie('SAPISID')
        headers = channel.get_authorization_headers(sapisid_cookie)
        headers['content-type'] = content_type
        required_cookies = ['SAPISID', 'HSID', 'SSID', 'APISID', 'SID']
        cookies = {cookie: self._get_cookie(cookie)
                   for cookie in required_cookies}
        params = {
            # "alternative representation type" (desired response format).
            'alt': response_type,
        }
        res = yield from http_utils.fetch(
            'post', url, headers=headers, cookies=cookies, params=params,
            data=data, connector=self._connector
        )
        return res

    ###########################################################################
    # API request methods - wrappers for self._pb_request for calling
    # particular APIs.
    ###########################################################################

    @asyncio.coroutine
    def add_user(self, add_user_request):
        """Invite users to join an existing group conversation."""
        response = hangouts_pb2.AddUserResponse()
        yield from self._pb_request('conversations/adduser',
                                    add_user_request, response)
        return response

    @asyncio.coroutine
    def create_conversation(self, create_conversation_request):
        """Create a new conversation."""
        response = hangouts_pb2.CreateConversationResponse()
        yield from self._pb_request('conversations/createconversation',
                                    create_conversation_request, response)
        return response

    @asyncio.coroutine
    def delete_conversation(self, delete_conversation_request):
        """Leave a one-to-one conversation.

        One-to-one conversations are "sticky"; they can't actually be deleted.
        This API clears the event history of the specified conversation up to
        delete_upper_bound_timestamp, hiding it if no events remain.
        """
        response = hangouts_pb2.DeleteConversationResponse()
        yield from self._pb_request('conversations/deleteconversation',
                                    delete_conversation_request, response)
        return response

    @asyncio.coroutine
    def easter_egg(self, easter_egg_request):
        """Send an easter egg event to a conversation."""
        response = hangouts_pb2.EasterEggResponse()
        yield from self._pb_request('conversations/easteregg',
                                    easter_egg_request, response)
        return response

    @asyncio.coroutine
    def get_conversation(self, get_conversation_request):
        """Return conversation info and recent events."""
        response = hangouts_pb2.GetConversationResponse()
        yield from self._pb_request('conversations/getconversation',
                                    get_conversation_request, response)
        return response

    @asyncio.coroutine
    def get_entity_by_id(self, get_entity_by_id_request):
        """Return info about a list of users."""
        response = hangouts_pb2.GetEntityByIdResponse()
        yield from self._pb_request('contacts/getentitybyid',
                                    get_entity_by_id_request, response)
        return response

    @asyncio.coroutine
    def get_self_info(self, get_self_info_request):
        """Return info about the current user."""
        response = hangouts_pb2.GetSelfInfoResponse()
        yield from self._pb_request('contacts/getselfinfo',
                                    get_self_info_request, response)
        return response

    @asyncio.coroutine
    def query_presence(self, query_presence_request):
        """Return presence status for a list of users."""
        response = hangouts_pb2.QueryPresenceResponse()
        yield from self._pb_request('presence/querypresence',
                                    query_presence_request, response)
        return response

    @asyncio.coroutine
    def remove_user(self, remove_user_request):
        """Leave a group conversation."""
        response = hangouts_pb2.RemoveUserResponse()
        yield from self._pb_request('conversations/removeuser',
                                    remove_user_request, response)
        return response

    @asyncio.coroutine
    def rename_conversation(self, rename_conversation_request):
        """Rename a conversation.

        Both group and one-to-one conversations may be renamed, but the
        official Hangouts clients have mixed support for one-to-one
        conversations with custom names.
        """
        response = hangouts_pb2.RenameConversationResponse()
        yield from self._pb_request('conversations/renameconversation',
                                    rename_conversation_request, response)
        return response

    @asyncio.coroutine
    def search_entities(self, search_entities_request):
        """Return info for users based on a query."""
        response = hangouts_pb2.SearchEntitiesResponse()
        yield from self._pb_request('contacts/searchentities',
                                    search_entities_request, response)
        return response

    @asyncio.coroutine
    def send_chat_message(self, send_chat_message_request):
        """Send a chat message to a conversation."""
        response = hangouts_pb2.SendChatMessageResponse()
        yield from self._pb_request('conversations/sendchatmessage',
                                    send_chat_message_request, response)
        return response

    @asyncio.coroutine
    def set_active_client(self, set_active_client_request):
        """Set the active client."""
        response = hangouts_pb2.SetActiveClientResponse()
        yield from self._pb_request('clients/setactiveclient',
                                    set_active_client_request, response)
        return response

    @asyncio.coroutine
    def set_conversation_notification_level(
            self, set_conversation_notification_level_request
    ):
        """Set the notification level of a conversation."""
        response = hangouts_pb2.SetConversationNotificationLevelResponse()
        yield from self._pb_request(
            'conversations/setconversationnotificationlevel',
            set_conversation_notification_level_request, response
        )
        return response

    @asyncio.coroutine
    def set_focus(self, set_focus_request):
        """Set focus to a conversation."""
        response = hangouts_pb2.SetFocusResponse()
        yield from self._pb_request('conversations/setfocus',
                                    set_focus_request, response)
        return response

    @asyncio.coroutine
    def set_presence(self, set_presence_request):
        """Set the presence status."""
        response = hangouts_pb2.SetPresenceResponse()
        yield from self._pb_request('presence/setpresence',
                                    set_presence_request, response)
        return response

    @asyncio.coroutine
    def set_typing(self, set_typing_request):
        """Set the typing status of a conversation."""
        response = hangouts_pb2.SetTypingResponse()
        yield from self._pb_request('conversations/settyping',
                                    set_typing_request, response)
        return response

    @asyncio.coroutine
    def sync_all_new_events(self, sync_all_new_events_request):
        """List all events occurring at or after a timestamp."""
        response = hangouts_pb2.SyncAllNewEventsResponse()
        yield from self._pb_request('conversations/syncallnewevents',
                                    sync_all_new_events_request, response)
        return response

    @asyncio.coroutine
    def sync_recent_conversations(self, sync_recent_conversations_request):
        """Return info on recent conversations and their events."""
        response = hangouts_pb2.SyncRecentConversationsResponse()
        yield from self._pb_request('conversations/syncrecentconversations',
                                    sync_recent_conversations_request,
                                    response)
        return response

    @asyncio.coroutine
    def update_watermark(self, update_watermark_request):
        """Update the watermark (read timestamp) of a conversation."""
        response = hangouts_pb2.UpdateWatermarkResponse()
        yield from self._pb_request('conversations/updatewatermark',
                                    update_watermark_request, response)
        return response
