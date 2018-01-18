"""Example of using hangups to lookup entities."""

import hangups

from common import run_example


async def lookup_entities(client, args):
    """Search for entities by phone number, email, or gaia_id."""
    lookup_spec = _get_lookup_spec(args.entity_identifier)
    request = hangups.hangouts_pb2.GetEntityByIdRequest(
        request_header=client.get_request_header(),
        batch_lookup_spec=[lookup_spec],
    )
    res = await client.get_entity_by_id(request)

    # Print the list of entities in the response.
    for entity_result in res.entity_result:
        for entity in entity_result.entity:
            print(entity)


def _get_lookup_spec(identifier):
    """Return EntityLookupSpec from phone number, email address, or gaia ID."""
    if identifier.startswith('+'):
        return hangups.hangouts_pb2.EntityLookupSpec(
            phone=identifier, create_offnetwork_gaia=True
        )
    elif '@' in identifier:
        return hangups.hangouts_pb2.EntityLookupSpec(
            email=identifier, create_offnetwork_gaia=True
        )
    else:
        return hangups.hangouts_pb2.EntityLookupSpec(gaia_id=identifier)


if __name__ == '__main__':
    run_example(lookup_entities, '--entity-identifier')
