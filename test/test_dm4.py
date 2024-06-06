"""
The DM4 files I have are huge and not a good fit for github.  Any dm4 file should work for testing this code.  Set
the path using the dm4_input_filename property.
"""

import unittest
import os
import dm4
import array

import six
from PIL import Image

import dm4.dm4file

Image.MAX_IMAGE_PIXELS = None

import numpy as np


def try_convert_unsigned_short_to_unicode(data, count_limit: int = 2048):
    """Attempt to convert arrays of 16-bit integers of less than specified length to a unicode string."""

    if not isinstance(data, array.array):
        return data

    if data.typecode == 'H' and len(data) < count_limit:
        try:
            if six.PY3:
                data = data.tobytes().decode('utf-16')
            else:
                data = data.tostring().decode('utf-16')
        except UnicodeDecodeError as e:
            pass
        except UnicodeEncodeError as e:
            pass

    return data


def print_tag_data(dmfile, tag, indent_level: int):
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

    if six.PY3:
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


def print_tag_directory_tree(dmfile: dm4.dm4file.DM4File,
                             dir_obj: dm4.dm4file.DM4File.DM4TagDir,
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


class testDM4(unittest.TestCase):

    @property
    def dm4_input_filename(self) -> str:
        """The name of a dm4 file to read during the test.  Change this to suit your test input file"""
        return 'Prefix_3VBSED_stack_00_slice_0855.dm4'

    @property
    def dm4_input_dirname(self) -> str:
        """The directory containing a dm4 file"""
        # return os.path.join('J:\\', 'NM_SRC_renum', 'Montage_000')
        return os.path.join('D:', 'Data', 'cped_raw', 'cped_renum_sm', 'Montage_000')

    @property
    def ImageDimensionsTag(self):
        return self.tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData'].named_subdirs[
            'Dimensions']

    def ReadImageShape(self) -> tuple[int, int]:
        xdim = self.dm4file.read_tag_data(self.ImageDimensionsTag.unnamed_tags[0])
        ydim = self.dm4file.read_tag_data(self.ImageDimensionsTag.unnamed_tags[1])

        return ydim, xdim

    @property
    def dm4_input_fullpath(self) -> str:
        return os.path.join(self.dm4_input_dirname, self.dm4_input_filename)

    def test(self):
        with dm4.dm4file.DM4File.open(self.dm4_input_fullpath) as self.dm4file:
            self.tags = self.dm4file.read_directory()
            print_tag_directory_tree(self.dm4file, self.tags)

        # self.Extract_Image(self.dm4file , self.tags, self.dm4_input_filename)

    def Extract_Image(self,
                      dmfile: dm4.DM4File,
                      tags: dm4.dm4file.DM4File.DM4TagDir,
                      image_filename: str):
        data_tag = tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData'].named_tags['Data']

        file_basename = os.path.basename(image_filename)
        output_dirname = 'C:\\Temp'
        output_filename = os.path.basename(file_basename + '.tif')

        output_fullpath = os.path.join(output_dirname, output_filename)

        np_array = np.array(dmfile.read_tag_data(data_tag), dtype=np.uint16)
        np_array = np.reshape(np_array, self.ReadImageShape())

        image = Image.fromarray(np_array, 'I;16')
        image.save(output_fullpath)

        dmfile.close()
