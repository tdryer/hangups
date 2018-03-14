"""Example of using hangups to upload an image."""

import hangups

from common import run_example


async def upload_image(client, args):
    # Upload image to obtain image_id:
    image_file = open(args.image, 'rb')
    uploaded_image = await client.upload_image(
        image_file, return_uploaded_image=True
    )

    # Send a chat message referencing the uploaded image_id:
    request = hangups.hangouts_pb2.SendChatMessageRequest(
        request_header=client.get_request_header(),
        event_request_header=hangups.hangouts_pb2.EventRequestHeader(
            conversation_id=hangups.hangouts_pb2.ConversationId(
                id=args.conversation_id
            ),
            client_generated_id=client.get_client_generated_id(),
        ),
        existing_media=hangups.hangouts_pb2.ExistingMedia(
            photo=hangups.hangouts_pb2.Photo(
                photo_id=uploaded_image.image_id,
            ),
        ),
    )
    await client.send_chat_message(request)


if __name__ == '__main__':
    run_example(upload_image, '--conversation-id', '--image')
