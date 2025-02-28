"""
The DM4 files I have are huge and not a good fit for github.  Any dm4 file should work for testing this code.  Set
the path using the dm4_input_filename property.

Note: This test is structured for a dm4 file produced by a specific microscope.  Other platforms may change the directory
structure and tags.  Use the print_tag_directory_tree function to explore the structure of your dm4 file as needed.
"""

import unittest
import os
import dm4
import numpy as np

import PIL  # For example code
from PIL import Image

from dm4 import DM4File, DM4TagDir, print_tag_directory_tree, print_tag_data
import dm4.dm4file

# Eliminating the MAX_IMAGE_PIXELS check in PIL is often necessary when dealing with multi-GB images often produced by microscopy platforms.
Image.MAX_IMAGE_PIXELS = None


class TestDM4(unittest.TestCase):

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
