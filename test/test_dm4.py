"""
The DM4 files I have are huge and not a good fit for github.  Any dm4 file should work for testing this code.  Set
the path using the dm4_input_filename property.

Note: This test is structured for a dm4 file produced by a specific microscope.  Other platforms may change the directory
structure and tags.  Use the print_tag_directory_tree function to explore the structure of your dm4 file as needed.
"""

import unittest
import os
import dm4
import array

import six
import PIL  # For example code
from PIL import Image

from dm4 import DM4DirHeader, DM4File, DM4TagHeader, DM4TagDir
import dm4.dm4file
from typing import Union

# Eliminating the MAX_IMAGE_PIXELS check in PIL is often necessary when dealing with multi-GB images often produced by microscopy platforms.
Image.MAX_IMAGE_PIXELS = None

import numpy as np


def try_convert_unsigned_short_to_unicode(data: array.array, count_limit: int = 2048):
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


def print_tag_directory_tree(dmfile: dm4.DM4File,
                             dir_obj: dm4.DM4TagDir,
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
        return 'Glumi1_3VBSED_stack_00_slice_0476.dm4'

    @property
    def dm4_input_dirname(self) -> str:
        """The directory containing a dm4 file"""
        if 'TESTINPUTPATH' in os.environ:
            return os.environ['TESTINPUTPATH']

        raise ValueError('TESTINPUTPATH environment variable not set')

    @property
    def FirstImageDimensionsTag(self) -> DM4TagDir:
        """Returns the dimension tag for the first image in the dm4 file."""
        return self.tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData'].named_subdirs[
            'Dimensions']

    def ReadImageShape(self, image_dimensions_tag: DM4TagDir) -> tuple[int, int]:
        """Returns the shape of an image stored in the dm4 file"""
        XDim = self.dm4file.read_tag_data(image_dimensions_tag.unnamed_tags[0])
        YDim = self.dm4file.read_tag_data(image_dimensions_tag.unnamed_tags[1])

        return YDim, XDim

    @property
    def dm4_input_fullpath(self) -> str:
        return os.path.join(self.dm4_input_dirname, self.dm4_input_filename)

    def test(self):
        with dm4.dm4file.DM4File.open(self.dm4_input_fullpath) as self.dm4file:
            self.tags = self.dm4file.read_directory()
            print_tag_directory_tree(self.dm4file, self.tags)

        # self.Extract_Image(self.dm4file , self.tags, self.dm4_input_filename)

    def Extract_Image(self,
                      dmfile: DM4File,
                      tags: DM4TagDir,
                      image_filename: str):
        data_tag = tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData'].named_tags['Data']

        file_basename = os.path.basename(image_filename)
        output_dirname = 'C:\\Temp'
        output_filename = os.path.basename(file_basename + '.tif')

        output_fullpath = os.path.join(output_dirname, output_filename)

        np_array = np.array(dmfile.read_tag_data(data_tag), dtype=np.uint16)
        np_array = np.reshape(np_array, self.ReadImageShape(self.FirstImageDimensionsTag))

        image = Image.fromarray(np_array, 'I;16')
        image.save(output_fullpath)

        dmfile.close()

    def test_readme_example(self):
        """The code in the try block should match the readme example to ensure the documentation code is correct"""

        output_fullpath = "sample.tif"

        try:

            # Example code goes below

            input_path = self.dm4_input_fullpath

            with dm4.DM4File.open(input_path) as dm4file:
                tags = dm4file.read_directory()

                image_data_tag = tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData']
                image_tag = image_data_tag.named_tags['Data']

                XDim = dm4file.read_tag_data(image_data_tag.named_subdirs['Dimensions'].unnamed_tags[0])
                YDim = dm4file.read_tag_data(image_data_tag.named_subdirs['Dimensions'].unnamed_tags[1])

                image_array = np.array(dm4file.read_tag_data(image_tag), dtype=np.uint16)
                image_array = np.reshape(image_array, (YDim, XDim))

                output_fullpath = "sample.tif"
                image = PIL.Image.fromarray(image_array, 'I;16')
                image.save(output_fullpath)

        finally:
            if os.path.exists(output_fullpath):
                os.remove(output_fullpath)
            else:
                raise ValueError(f"Output file {output_fullpath} was not created")
