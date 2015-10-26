"""Generate reStructuredText documentation from Protocol Buffers."""

import argparse
import subprocess
import sys
import tempfile
import textwrap

from google.protobuf import descriptor_pb2


INFINITY = 10000
# pylint: disable=no-member
LABEL_TO_STR = {value: name.lower()[6:] for name, value in
                descriptor_pb2.FieldDescriptorProto.Label.items()}
TYPE_TO_STR = {value: name.lower()[5:] for name, value in
               descriptor_pb2.FieldDescriptorProto.Type.items()}
# pylint: enable=no-member


def print_table(col_tuple, row_tuples):
    """Print column headers and rows as a reStructuredText table.

    Args:
        col_tuple: Tuple of column name strings.
        row_tuples: List of tuples containing row data.
    """
    col_widths = [max(len(str(row[col])) for row in [col_tuple] + row_tuples)
                  for col in range(len(col_tuple))]
    format_str = ' '.join('{{:<{}}}'.format(col_width)
                          for col_width in col_widths)
    header_border = ' '.join('=' * col_width for col_width in col_widths)
    print(header_border)
    print(format_str.format(*col_tuple))
    print(header_border)
    for row_tuple in row_tuples:
        print(format_str.format(*row_tuple))
    print(header_border)
    print()


def make_subsection(text):
    """Format text as reStructuredText subsection.

    Args:
        text: Text string to format.

    Returns:
        Formatted text string.
    """
    return '{}\n{}\n'.format(text, '-' * len(text))


def make_link(text):
    """Format text as reStructuredText link.

    Args:
        text: Text string to format.

    Returns:
        Formatted text string.
    """
    return '`{}`_'.format(text)


def make_code(text):
    """Format text as reStructuredText code.

    Args:
        text: Text string to format.

    Returns:
        Formatted text string.
    """
    return ':code:`{}`'.format(text)


def make_comment(text):
    """Format text as reStructuredText comment.

    Args:
        text: Text string to format.

    Returns:
        Formatted text string.
    """
    return '.. {}\n'.format(text)


def get_comment_from_location(location):
    """Return comment text from location.

    Args:
        location: descriptor_pb2.SourceCodeInfo.Location instance to get
            comment from.

    Returns:
        Comment as string.

    """
    return textwrap.dedent(location.leading_comments or
                           location.trailing_comments)


def generate_enum_doc(enum_descriptor, locations, path, name_prefix=''):
    """Generate doc for an enum.

    Args:
        enum_descriptor: descriptor_pb2.EnumDescriptorProto instance for enum
            to generate docs for.
        locations: Dictionary of location paths tuples to
            descriptor_pb2.SourceCodeInfo.Location instances.
        path: Path tuple to the enum definition.
        name_prefix: Optional prefix for this enum's name.
    """
    print(make_subsection(name_prefix + enum_descriptor.name))
    location = locations[path]
    if location.HasField('leading_comments'):
        print(textwrap.dedent(location.leading_comments))

    row_tuples = []
    for value_index, value in enumerate(enum_descriptor.value):
        field_location = locations[path + (2, value_index)]
        row_tuples.append((
            make_code(value.name),
            value.number,
            textwrap.fill(get_comment_from_location(field_location), INFINITY),
        ))
    print_table(('Name', 'Number', 'Description'), row_tuples)


def generate_message_doc(message_descriptor, locations, path, name_prefix=''):
    """Generate docs for message and nested messages and enums.

    Args:
        message_descriptor: descriptor_pb2.DescriptorProto instance for message
            to generate docs for.
        locations: Dictionary of location paths tuples to
            descriptor_pb2.SourceCodeInfo.Location instances.
        path: Path tuple to the message definition.
        name_prefix: Optional prefix for this message's name.
    """
    # message_type is 4
    prefixed_name = name_prefix + message_descriptor.name
    print(make_subsection(prefixed_name))
    location = locations[path]
    if location.HasField('leading_comments'):
        print(textwrap.dedent(location.leading_comments))

    row_tuples = []
    for field_index, field in enumerate(message_descriptor.field):
        field_location = locations[path + (2, field_index)]
        if field.type not in [11, 14]:
            type_str = TYPE_TO_STR[field.type]
        else:
            type_str = make_link(field.type_name.lstrip('.'))
        row_tuples.append((
            make_code(field.name),
            field.number,
            type_str,
            LABEL_TO_STR[field.label],
            textwrap.fill(get_comment_from_location(field_location), INFINITY),
        ))
    print_table(('Field', 'Number', 'Type', 'Label', 'Description'),
                row_tuples)

    # Generate nested messages
    nested_types = enumerate(message_descriptor.nested_type)
    for index, nested_message_desc in nested_types:
        generate_message_doc(nested_message_desc, locations,
                             path + (3, index),
                             name_prefix=prefixed_name + '.')

    # Generate nested enums
    for index, nested_enum_desc in enumerate(message_descriptor.enum_type):
        generate_enum_doc(nested_enum_desc, locations, path + (4, index),
                          name_prefix=prefixed_name + '.')


def compile_protofile(proto_file_path):
    """Compile proto file to descriptor set.

    Args:
        proto_file_path: Path to proto file to compile.

    Returns:
        Path to file containing compiled descriptor set.

    Raises:
        SystemExit if the compilation fails.
    """
    out_file = tempfile.mkstemp()[1]
    try:
        subprocess.check_output(['protoc', '--include_source_info',
                                 '--descriptor_set_out', out_file,
                                 proto_file_path])
    except subprocess.CalledProcessError as e:
        sys.exit('protoc returned status {}'.format(e.returncode))
    return out_file


def main():
    """Parse arguments and print generated documentation to stdout."""
    parser = argparse.ArgumentParser()
    parser.add_argument('protofilepath')
    args = parser.parse_args()

    out_file = compile_protofile(args.protofilepath)
    with open(out_file, 'rb') as proto_file:
        # pylint: disable=no-member
        file_descriptor_set = descriptor_pb2.FileDescriptorSet.FromString(
            proto_file.read()
        )
        # pylint: enable=no-member

    for file_descriptor in file_descriptor_set.file:
        # Build dict of location tuples
        locations = {}
        for location in file_descriptor.source_code_info.location:
            locations[tuple(location.path)] = location
        # Add comment to top
        print(make_comment('This file was automatically generated from {} and '
                           'should not be edited directly.'
                           .format(args.protofilepath)))
        # Generate documentation
        for index, message_desc in enumerate(file_descriptor.message_type):
            generate_message_doc(message_desc, locations, (4, index))
        for index, enum_desc in enumerate(file_descriptor.enum_type):
            generate_enum_doc(enum_desc, locations, (5, index))


if __name__ == '__main__':
    main()
