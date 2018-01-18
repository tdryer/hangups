"""Example of using hangups to retrieve suggested contacts."""

import hangups

from common import run_example


async def retrieve_suggested_contacts(client, _):
    request = hangups.hangouts_pb2.GetSuggestedEntitiesRequest(
        request_header=client.get_request_header(),
        max_count=100,
    )
    res = await client.get_suggested_entities(request)

    # Print the list of entities in the response.
    for entity in res.entity:
        print('{} ({})'.format(
            entity.properties.display_name, entity.id.gaia_id
        ))


if __name__ == '__main__':
    run_example(retrieve_suggested_contacts)
