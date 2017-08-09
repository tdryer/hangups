"""Decoder and encoder for the pblite format.

pblite (sometimes also known as protojson) is a format for serializing Protocol
Buffers into JavaScript objects. Messages are represented as arrays where the
tag number of a value is given by its position in the array.

Methods in this module assume encoding/decoding to JavaScript strings is done
separately.

Google's implementation for JavaScript is available in closure-library:
    https://github.com/google/closure-library/tree/master/closure/goog/proto2
"""

import base64
import itertools
import logging

# pylint: disable=no-name-in-module,import-error
from google.protobuf.descriptor import FieldDescriptor
# pylint: enable=no-name-in-module,import-error


logger = logging.getLogger(__name__)


def _decode_field(message, field, value):
    """Decode optional or required field."""
    if field.type == FieldDescriptor.TYPE_MESSAGE:
        decode(getattr(message, field.name), value)
    else:
        try:
            if field.type == FieldDescriptor.TYPE_BYTES:
                value = base64.b64decode(value)
            setattr(message, field.name, value)
        except (ValueError, TypeError) as e:
            # ValueError: invalid enum value, negative unsigned int value, or
            # invalid base64
            # TypeError: mismatched type
            logger.warning('Message %r ignoring field %s: %s',
                           message.__class__.__name__, field.name, e)


def _decode_repeated_field(message, field, value_list):
    """Decode repeated field."""
    if field.type == FieldDescriptor.TYPE_MESSAGE:
        for value in value_list:
            decode(getattr(message, field.name).add(), value)
    else:
        try:
            for value in value_list:
                if field.type == FieldDescriptor.TYPE_BYTES:
                    value = base64.b64decode(value)
                getattr(message, field.name).append(value)
        except (ValueError, TypeError) as e:
            # ValueError: invalid enum value, negative unsigned int value, or
            # invalid base64
            # TypeError: mismatched type
            logger.warning('Message %r ignoring repeated field %s: %s',
                           message.__class__.__name__, field.name, e)
            # Ignore any values already decoded by clearing list
            message.ClearField(field.name)


def decode(message, pblite, ignore_first_item=False):
    """Decode pblite to Protocol Buffer message.

    This method is permissive of decoding errors and will log them as warnings
    and continue decoding where possible.

    The first element of the outer pblite list must often be ignored using the
    ignore_first_item parameter because it contains an abbreviation of the name
    of the protobuf message (eg.  cscmrp for ClientSendChatMessageResponseP)
    that's not part of the protobuf.

    Args:
        message: protocol buffer message instance to decode into.
        pblite: list representing a pblite-serialized message.
        ignore_first_item: If True, ignore the item at index 0 in the pblite
            list, making the item at index 1 correspond to field 1 in the
            message.
    """
    if not isinstance(pblite, list):
        logger.warning('Ignoring invalid message: expected list, got %r',
                       type(pblite))
        return
    if ignore_first_item:
        pblite = pblite[1:]
    # If the last item of the list is a dict, use it as additional field/value
    # mappings. This seems to be an optimization added for dealing with really
    # high field numbers.
    if pblite and isinstance(pblite[-1], dict):
        extra_fields = {int(field_number): value for field_number, value
                        in pblite[-1].items()}
        pblite = pblite[:-1]
    else:
        extra_fields = {}
    fields_values = itertools.chain(enumerate(pblite, start=1),
                                    extra_fields.items())
    for field_number, value in fields_values:
        if value is None:
            continue
        try:
            field = message.DESCRIPTOR.fields_by_number[field_number]
        except KeyError:
            # If the tag number is unknown and the value is non-trivial, log a
            # message to aid reverse-engineering the missing field in the
            # message.
            if value not in [[], '', 0]:
                logger.debug('Message %r contains unknown field %s with value '
                             '%r', message.__class__.__name__, field_number,
                             value)
            continue
        if field.label == FieldDescriptor.LABEL_REPEATED:
            _decode_repeated_field(message, field, value)
        else:
            _decode_field(message, field, value)
