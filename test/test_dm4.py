
import unittest
import os
import dm4reader
import array

import six 
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

import numpy as np


def try_convert_unsigned_short_to_unicode(data, count_limit=2048):
    '''Attempt to convert arrays of 16-bit integers of less than specified length to a unicode string.'''
    
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
        
    
def print_tag_data(dmfile, tag, indent_level):
    '''Print data associated with a dm4 tag'''
    
    if tag.byte_length > 2048:
        print(indent_level * '\t' + '%s\t' % (tag.name) + "Array length %d too long to read" % (tag.array_length))
        return 
    
    data = dmfile.read_tag_data(tag)
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

def print_tag_directory_tree(dmfile, dir_obj, indent_level=0):
    '''Print all of the tags and directories contained in a dm4 file'''
    
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
    def dm4_input_filename(self):
        '''The name of the dm4 file to read during the test.  Change this to suit your test input file'''
        #return 'Glumi1_3VBSED_stack_05_slice_0476.dm4'
        return 'SigmaDM4_previous_version.dm4'
    
    @property
    def dm4_input_dirname(self):
        '''The directory containing the dm4 file'''
        #return os.path.join('D:\\', 'Data', 'Neitz')
        #return os.path.join('J:\\', 'NM_SRC_renum', 'Montage_000')
        return os.path.join('J:\\')
    
    @property
    def ImageDimensionsTag(self):
        return self.tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData'].named_subdirs['Dimensions']
    
    def ReadImageShape(self):  
        XDim = self.dm4file.read_tag_data(self.ImageDimensionsTag.unnamed_tags[0])
        YDim = self.dm4file.read_tag_data(self.ImageDimensionsTag.unnamed_tags[1])
        
        return (YDim, XDim)
    
    @property
    def dm4_input_fullpath(self):
        return os.path.join(self.dm4_input_dirname, self.dm4_input_filename)

    def test(self):
        
        self.dm4file = dm4reader.DM4File.open(self.dm4_input_fullpath)
        
        self.tags = self.dm4file .read_directory()
        print_tag_directory_tree(self.dm4file , self.tags)
        
        #self.Extract_Image(self.dm4file , self.tags, self.dm4_input_filename)
        
        
    def Extract_Image(self, dmfile, tags, image_filename):
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
