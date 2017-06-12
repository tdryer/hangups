"""Example of using hangups to send map location to a conversation."""

import asyncio

import hangups

from common import run_example


@asyncio.coroutine
def send_map_location(client, args):
    lat, lng = (float(l) for l in args.location.split(','))

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
                location_info=hangups.hangouts_pb2.Place.LocationInfo(
                    latlng=hangups.hangouts_pb2.Place.LocationInfo.LatLng(
                        lat=lat,
                        lng=lng
                    ),
                ),
                name=args.name,
                display_info=hangups.hangouts_pb2.Place.DisplayInfo(
                    description=hangups.hangouts_pb2.Place.DisplayInfo.Description(
                        text=args.description
                    ),
                ),
            ),
        ),
    )
    yield from client.send_chat_message(request)


if __name__ == '__main__':
    run_example(send_map_location,
                '--conversation-id', '--location', '--name', '--description')
