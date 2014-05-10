"""Parser for long-polling responses from the talkgadget API."""

import pprint
import logging
import re

from hangups import javascript


logger = logging.getLogger(__name__)
PP = pprint.PrettyPrinter(indent=4)
LEN_REGEX = re.compile(r'([0-9]+)\n', re.MULTILINE)


def parse_push_data():
    """Consume characters from the push channel, and generate messages.

    A message begins with an integer stating its length in characters followed
    by a newline, followed by the message itself. Any number of messages may be
    present.
    """
    buf = ''
    while True:
        lengths = LEN_REGEX.findall(buf)
        if len(lengths) == 0:
            s = yield
            if s is not None:
                buf += s
        else:
            length = int(lengths[0])
            buf = buf[len(lengths[0]) + 1:]
            while len(buf) < length:
                s = yield
                if s is not None:
                    buf += s
            yield buf[:length]
            buf = buf[length:]


def parse_content_message(msg, number):
    """Parse content message."""
    # session ID, should be the same for every request
    session_id = msg[0][1][1][0]
    # payload type
    payload_type = msg[0][1][1][1][0]
    if payload_type == 'bfo':
        # payload is submessages in the list format
        payload = javascript.loads(msg[0][1][1][1][1])
        payload_type_pretty = 'list'
    elif payload_type == 'tm':
        # payload is object format
        payload = javascript.loads(msg[0][1][1][1][1])
        payload_type_pretty = 'object'
    elif payload_type == 'wh':
        # payload is null
        # These messages don't contain any information other than the
        # session_id, and appear to be just heartbeats.
        payload = None
        payload_type_pretty = 'null'
    else:
        raise ValueError('Unknown payload type: {}'.format(payload_type))
    return {'num': number, 'type': 'content', 'session_id': session_id,
            'payload': payload, 'payload_type': payload_type_pretty}


def parse_noop_message(msg, number):
    """Parse noop message.

    These contain no information and only seem to appear once as the first
    message when a channel is opened.
    """
    return {'num': number, 'type': 'noop'}


def parse_message(msg):
    """Parse a message to get its payload."""
    # the message number, increments with each message
    msg_number = msg[0][0]
    # the message type
    msg_type = msg[0][1][0]
    return {
        'noop': parse_noop_message,
        'c': parse_content_message,
    }[msg_type](msg, msg_number)


def parse_list_payload(payload):
    """Parse the list payload format into events."""
    # the payload begins with a constant header
    if payload[0] != 'cbu':
        raise ValueError('Invalid list payload header: {}'.format(payload[0]))

    # the first submessage is always present, so let's treat it light a header
    first_submsg = payload[1][0][0]
    if len(first_submsg) == 5:
        (unknown_int, unknown_none, unknown_str, unknown_none_or_list,
         timestamp) = first_submsg
        unknown_list = None
    elif len(first_submsg) == 6:
        (unknown_int, unknown_none, unknown_str, unknown_none_or_list,
         timestamp, unknown_list) = first_submsg
    else:
        raise ValueError('Cannot parse first submessage: {}'
                         .format(first_submsg))

    # The type of a submessage is determined by its position in the array
    submsgs = payload[1][0][1:]
    for submsg_type, submsg in enumerate(submsgs):
        if submsg is not None:
            logger.debug('Received submsg of type {}:\n{}'
                         .format(submsg_type, PP.pformat(submsg)))

        if submsg is None:
            pass # don't try to parse a null submsg
        elif submsg_type == 1:
            # parse chat message
            conversation_id = submsg[0][0][0]
            sender_ids = submsg[0][1]
            timestamp = submsg[0][2]
            content = submsg[0][6]
            type_ = content[2][0][0][0]
            if type_ == 0: # text
                type_, text, formatting = content[2][0][0]
                links = None
            elif type_ == 2: # link
                type_, text, formatting, links = content[2][0][0]
            else:
                raise ValueError('Unknown message type {} for message: {}'
                                 .format(type_, submsg))
            yield {
                'conversation_id': conversation_id,
                'timestamp': timestamp,
                'sender_ids': tuple(sender_ids),
                'text': text,
            }

        elif submsg_type == 2:
            # TODO: parse unknown (related to conversation focus?)
            # conversation_id, sender_ids, timestamp, 1/2, 20/300
            pass
        elif submsg_type == 3:
            # TODO: parse unknown
            # conversation_id, sender_ids, timestand, 1 or 2
            pass
        elif submsg_type == 6:
            # TODO: parse unknown
            # sender_ids, conversation_id, timestamp
            pass
        elif submsg_type == 11:
            # TODO: parse conversation update
            pass
        elif submsg_type == 12:
            # TODO: parse unknown
            pass
        elif submsg_type == 13:
            # TODO: parse unknown
            pass
        elif submsg_type == 14:
            # TODO: parse unknown
            pass
        else:
            logging.warning('submsg type {} is unknown'.format(submsg_type))
