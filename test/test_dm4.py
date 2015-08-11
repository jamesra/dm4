
import unittest
import os
import dm4reader
import array

import six
import nornir_imageregistration.core as core

import PIL

import numpy as np


def try_convert_unsigned_short_to_unicode(data, count_limit=2048):
    '''Convert an array of less than specified length to a unicode string'''
    
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
    if tag.byte_length > 2048:
        print(indent_level * '\t' + '%s\t' % (tag.name) + "Array length %d too long to read" % (tag.array_length))
        return 
    
    data = dmfile.read_tag_data(tag)
    data = try_convert_unsigned_short_to_unicode(data)
    
    if six.PY3:
        print(indent_level * '\t' + '%s\t%s' % (tag.name, str(data)))
    else:
        if isinstance(data, array.array) and data.typecode == 'H': #Unconverted unicode or image data
            print(indent_level * '\t' + '%s\t%s' % (tag.name, "Unconverted array of unsigned 16-bit integers"))
        elif isinstance(data, unicode):
            print(indent_level * '\t' + '%s\t%s' % (tag.name, data))
        else:
            if tag.name is None:
                print(indent_level * '\t' + 'Unnamed tag\t%s' % ( str(data)))
            else:
                print(indent_level * '\t' + tag.name.encode('ascii', 'ignore') + '\t%s' % ( str(data)))

def print_tag_directory_tree(dmfile, dir_obj, indent_level=0):
    
    for tag in dir_obj.unnamed_tags:
        print_tag_data(dmfile, tag,indent_level)
        
    for k in sorted(dir_obj.named_tags.keys()):
        tag = dir_obj.named_tags[k]
        print_tag_data(dmfile, tag,indent_level)
        
    for subdir in dir_obj.unnamed_subdirs:
        print(indent_level * '\t' + "Unnamed directory")
        print_tag_directory_tree(dmfile, subdir, indent_level + 1)
        
    for k in sorted(dir_obj.named_subdirs.keys()):
        subdir = dir_obj.named_subdirs[k]
        print(indent_level * '\t' + k)
        print_tag_directory_tree(dmfile, subdir, indent_level + 1)
    
    indent_level -= 1

class testDM4(unittest.TestCase):

    def test(self):
        dmdir = os.path.join('D:\\','Data','Nietz')
        image_filename = 'Glumi1_3VBSED_stack_05_slice_0476.dm4'
        dmfullpath = os.path.join(dmdir,image_filename)
        dmfile = dm4reader.DM4File.open(dmfullpath)
        
        tags = dmfile.walk_tags()
        print_tag_directory_tree(dmfile, tags)
        
        self.Extract_Image(dmfile, tags, image_filename)
        
        
    def Extract_Image(self, dmfile, tags, image_filename):
        data_tag = tags.named_subdirs['ImageList'].unnamed_subdirs[1].named_subdirs['ImageData'].named_tags['Data'] 
        
        file_basename = os.path.basename(image_filename)
        output_dirname = 'C:\\Temp'
        output_filename = os.path.basename(file_basename + '.tif')
        
        output_fullpath = os.path.join(output_dirname, output_filename)
         
        np_array = np.array(dmfile.read_tag_data(data_tag), dtype=np.uint16)
        np_array = np.reshape(np_array, (9000,9000))
        #np_array = core.NormalizeImage(np_array)
        #core.ShowGrayscale(np_array)
        #core.SaveImage(output_fullpath, np_array)
        #image = PIL.Image.frombuffer("I", (9000,9000), dmfile.read_tag_data(data_tag), "raw", "I", 0,1)
        image = PIL.Image.fromarray(np_array, 'I;16')
        image.save(output_fullpath) 
          
        dmfile.close()