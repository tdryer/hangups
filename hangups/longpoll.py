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

    Responses from the push endpoint consist of a sequence of messages. Each
    message is prefixed with its length followed by a newline.

    The length is actually the length of the string as reported by JavaScript.
    JavaScript's string length function returns the number of code units in the
    string, represented in UTF-16. We can emulate this by encoding everything
    in UTF-16 and multipling the reported length by 2.

    Note that when encoding a string in UTF-16, Python will prepend a
    byte-order character, so we need to remove the first two bytes.
    """
    buf = b'' # utf-16 encoded text
    while True:
        lengths = LEN_REGEX.findall(buf.decode('utf-16'))
        if len(lengths) == 0:
            s = yield
            if s is not None:
                buf += s.encode('utf-16')[2:]
        else:
            length = int(lengths[0]) * 2 # number of bytes in UTF-16 encoding
            # pop the length and newline from the buffer
            pop_length = len((lengths[0] + '\n').encode('utf-16')[2:])
            buf = buf[pop_length:]
            while len(buf) < length:
                s = yield
                if s is not None:
                    buf += s.encode('utf-16')[2:]
            yield buf[:length].decode('utf-16')
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
    elif payload_type == 'otr':
        # not sure what this is for, something to do with xmpp?
        payload = None
        payload_type_pretty = 'otr'
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

            # The message content is a list of message segments, which have a
            # type. For now, let's ignore the types and just use the textual
            # representation, appending all the segments into one string.
            message_text = ''
            message_content = submsg[0][6][2][0]
            for segment in message_content:
                # known types: 0: text, 1: linebreak, 2: link
                type_ = segment[0]
                message_text += segment[1]

            yield {
                'conversation_id': conversation_id,
                'timestamp': timestamp,
                'sender_ids': tuple(sender_ids),
                'text': message_text,
            }

        elif submsg_type == 2:
            # TODO: parse unknown (related to conversation focus?)
            # conversation_id, sender_ids, timestamp, 1/2, 20/300
            pass
        elif submsg_type == 3:
            # parse typing status
            # Note that the same status may be sent multiple times
            # consecutively, and that when a message is sent the typing status
            # will not change to stopped.
            TYPING_STATUSES = {
                1: 'typing', # the user is typing
                2: 'paused', # the user stopped typing with inputted text
                3: 'stopped', # the user stopped typing with no inputted text
            }
            conversation_id = submsg[0][0]
            user_ids = submsg[1]
            timestamp = submsg[2]
            try:
                typing_status = TYPING_STATUSES[submsg[3]]
            except KeyError:
                typing_status = None
                logging.warning('Unknown typing status: {}'.format(submsg[3]))
        elif submsg_type == 6:
            # TODO: parse unknown
            # sender_ids, conversation_id, timestamp
            pass
        elif submsg_type == 11:
            # TODO: parse conversation update
            yield {
                'conversation_id': submsg[0][0],
                # participant list items sometimes can be length 2 or 3
                # ids, name, ?
                'participants': {tuple(item[0]): item[1]
                                 for item in submsg[13]},
            }
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
