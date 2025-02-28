"""
Helper functions for working with dm4 files
"""

import sys
from typing import Union
import array
from dm4.dm4file import DM4File
from dm4.headers import DM4TagDir, DM4TagHeader, DM4DirHeader


def _is_python3():
    return sys.version_info[0] == 3


def try_convert_unsigned_short_to_unicode(data: array.array, count_limit: int = 2048):
    """Attempt to convert arrays of 16-bit integers of less than specified length to a unicode string."""

    if not isinstance(data, array.array):
        return data

    if data.typecode == 'H' and len(data) < count_limit:
        try:
            if _is_python3():
                data = data.tobytes().decode('utf-16')
            else:
                data = data.tostring().decode('utf-16')
        except UnicodeDecodeError as e:
            pass
        except UnicodeEncodeError as e:
            pass

    return data


def print_tag_data(dmfile: DM4File, tag: Union[DM4TagHeader, DM4DirHeader], indent_level: int):
    """Print data associated with a dm4 tag"""

    if tag.byte_length > 2048:
        print(indent_level * '\t' + '%s\t' % (tag.name) + "Array length %d too long to read" % (tag.array_length))
        return

    try:
        data = dmfile.read_tag_data(tag)
    except NotImplementedError as e:
        print(indent_level * '\t' + '***' + str(e) + '***')
        return

    data = try_convert_unsigned_short_to_unicode(data)

    if _is_python3():
        print(indent_level * '\t' + '%s\t%s' % (tag.name, str(data)))
    else:
        if isinstance(data, array.array) and data.typecode == 'H':  # Unconverted unicode or image data
            print(indent_level * '\t' + '%s\t%s' % (tag.name, "Unconverted array of unsigned 16-bit integers"))
        elif isinstance(data, unicode):
            print(indent_level * '\t' + '%s\t%s' % (tag.name, data))
        else:
            if tag.name is None:
                print(indent_level * '\t' + 'Unnamed tag\t%s' % (str(data)))
            else:
                print(indent_level * '\t' + tag.name.encode('ascii', 'ignore') + '\t%s' % (str(data)))


def print_tag_directory_tree(dmfile: DM4File,
                             dir_obj: DM4TagDir,
                             indent_level: int = 0):
    """Print all of the tags and directories contained in a dm4 file"""

    for tag in dir_obj.unnamed_tags:
        print_tag_data(dmfile, tag, indent_level)

    for k in sorted(dir_obj.named_tags.keys()):
        tag = dir_obj.named_tags[k]
        print_tag_data(dmfile, tag, indent_level)

    for subdir in dir_obj.unnamed_subdirs:
        print(indent_level * '\t' + "Unnamed directory")
        print_tag_directory_tree(dmfile, subdir, indent_level + 1)

    for k in sorted(dir_obj.named_subdirs.keys()):
        subdir = dir_obj.named_subdirs[k]
        print(indent_level * '\t' + k)
        print_tag_directory_tree(dmfile, subdir, indent_level + 1)

    indent_level -= 1
