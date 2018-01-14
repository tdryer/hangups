"""Example of using hangups to send chat message containing a map location."""

import hangups

from common import run_example


async def send_map_location(client, args):
    request = hangups.hangouts_pb2.SendChatMessageRequest(
        request_header=client.get_request_header(),
        event_request_header=hangups.hangouts_pb2.EventRequestHeader(
            conversation_id=hangups.hangouts_pb2.ConversationId(
                id=args.conversation_id
            ),
            client_generated_id=client.get_client_generated_id(),
        ),
        location=hangups.hangouts_pb2.Location(
            place=hangups.hangouts_pb2.Place(
                name=args.name,
                address=hangups.hangouts_pb2.EmbedItem(
                    postal_address=hangups.hangouts_pb2.EmbedItem.PostalAddress(
                        street_address=args.address
                    ),
                ),
                geo=hangups.hangouts_pb2.EmbedItem(
                    geo_coordinates=hangups.hangouts_pb2.EmbedItem.GeoCoordinates(
                        latitude=float(args.latitude),
                        longitude=float(args.longitude)
                    ),
                ),
            ),
        ),
    )
    await client.send_chat_message(request)


if __name__ == '__main__':
    run_example(
        send_map_location, '--conversation-id', '--latitude', '--longitude',
        '--name', '--address'
    )
