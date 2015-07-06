"""
https://github.com/dpp-name/protobuf-json/blob/master/protobuf_json.py

Methods in this module assume encoding/decoding to JavaScript strings is done
separately.
"""

import logging

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message


logger = logging.getLogger(__name__)


# TODO: raise exception for missing required fields
# TODO: document/test error checking
# TODO: catch oneof violations for encode/decode


def decode(pb_message, pblite):
    """Decode pblite to Protocol Buffer message."""
    assert pblite is not None

    # Reverse-engineering aid
    known_field_numbers = [field.number for field
                           in pb_message.DESCRIPTOR.fields]
    for field_number, _ in enumerate(pblite, start=1):
        if field_number not in known_field_numbers:
            value = pblite[field_number - 1]
            if value is not None:
                logger.debug(
                    'Message {} contains unknown field {} with value {}'
                    .format(pb_message.__class__.__name__, field_number,
                            repr(value))
                )

    for field in pb_message.DESCRIPTOR.fields:
        try:
            value = pblite[field.number - 1]
        except IndexError:
            value = None
        if value is None:
            pass  # Use default value for field
        elif field.label == FieldDescriptor.LABEL_REPEATED:
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                # value is repeated message
                for repeated_value in value:
                    decode(getattr(pb_message, field.name).add(),
                           repeated_value)
            else:
                # value is repeated scalar
                getattr(pb_message, field.name).extend(value)
        else:
            if field.type == FieldDescriptor.TYPE_MESSAGE:
                # value is optional message
                decode(getattr(pb_message, field.name), value)
            else:
                # value is optional scalar
                # TODO: handle invalid type here and other places
                try:
                    setattr(pb_message, field.name, value)
                except TypeError as e:
                    logger.warning(
                        'Message {} ignoring field {} with invalid type: {}'
                        .format(pb_message.__class__.__name__, field.name, e)
                    )
                except ValueError as e:
                    logger.warning(
                        'Message {} ignoring field {} with unknown value: {}'
                        .format(pb_message.__class__.__name__, field.name,
                                repr(value))
                    )


def encode(pb):
    """Encode Protocol Buffer message to pblite."""
    assert isinstance(pb, Message)
    pblite = []
    # ListFields only returns fields that are set, so use this to only encode
    # necessary fields
    for field_descriptor, field_value in pb.ListFields():
        if field_descriptor.label == FieldDescriptor.LABEL_REPEATED:
            if field_descriptor.type == FieldDescriptor.TYPE_MESSAGE:
                # value is repeated message
                encoded_value = [encode(item) for item in field_value]
            else:
                # value is repeated scalar
                encoded_value = list(field_value)
        else:
            if field_descriptor.type == FieldDescriptor.TYPE_MESSAGE:
                # value is optional message
                encoded_value = encode(field_value)
            else:
                # value is optional scalar
                encoded_value = field_value

        # add any necessary padding to the list
        required_padding = max(field_descriptor.number - len(pblite), 0)
        pblite.extend([None] * required_padding)

        pblite[field_descriptor.number - 1] = encoded_value

    return pblite
