"""Example of using hangups to retrieve suggested contacts."""

import asyncio

import hangups


# Path where OAuth refresh token is saved, allowing hangups to remember your
# credentials.
REFRESH_TOKEN_PATH = 'refresh_token.txt'


def main():
    """Main entry point."""

    # Obtain hangups authentication cookies, prompting for username and
    # password from standard in if necessary.
    cookies = hangups.auth.get_auth_stdin(REFRESH_TOKEN_PATH)

    # Instantiate hangups Client instance.
    client = hangups.Client(cookies)

    # Add an observer to the on_connect event to run the
    # retrieve_suggested_contacts coroutine when hangups has finished
    # connecting.
    client.on_connect.add_observer(lambda: asyncio.async(
        retrieve_suggested_contacts(client)
    ))

    # Start an asyncio event loop by running Client.connect. This will not
    # return until Client.disconnect is called, or hangups becomes
    # disconnected.
    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.connect())


@asyncio.coroutine
def retrieve_suggested_contacts(client):
    """Send message using connected hangups.Client instance."""

    # Instantiate a GetSuggestedEntitiesRequest Protocol Buffer message
    # describing the request.
    request = hangups.hangouts_pb2.GetSuggestedEntitiesRequest(
        request_header=client.get_request_header(),
        max_count=100,
    )

    try:
        # Make the request to the Hangouts API.
        res = yield from client.get_suggested_entities(request)

        # Print the list of entities in the response.
        for entity in res.entity:
            print('{} ({})'.format(entity.properties.display_name,
                                   entity.id.gaia_id))
    finally:
        # Disconnect the hangups Client to make client.connect return.
        yield from client.disconnect()


if __name__ == '__main__':
    main()
