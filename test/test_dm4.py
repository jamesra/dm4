
import unittest
import os
import dm4reader

def print_tag_data(dmfile, tag, indent_level):
    if tag.byte_length > 2048:
        print("Array length %d too long to read" % (tag.array_length))
    else:
        print(indent_level * '\t' + '%s\t%s' % (tag.name, str(dmfile.read_tag_data(tag))))

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
        dmfullpath = os.path.join(dmdir,'Glumi1_3VBSED_stack_01_slice_0476.dm4')
        dmfile = dm4reader.DM4File.open(dmfullpath)
        
        tags = dmfile.walk_tags()
        print_tag_directory_tree(dmfile, tags)
         
        dmfile.close()