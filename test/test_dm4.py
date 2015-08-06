
import unittest
import os
import dm4reader

def print_tag_dict(dmfile, tags, indent_level=0):         
    for k in sorted(tags.keys()):
        tag = tags[k]
        if isinstance(tag, dict):
            if k is None:
                k = 'Unnamed tag directory'
            print(indent_level * '\t' + k)
            print_tag_dict(dmfile, tag, indent_level + 1)
        elif isinstance(tag, dm4reader.DM4TagHeader):
            #print(indent_level * '\t' + str(k) + '\t%d\t' % (value.data_type_code) + str(value.data))
            if tag.byte_length > 2048:
                print("Array length %d too long to read" % (tag.array_length))
            else:
                print(indent_level * '\t' + str(k) + '\t' + str(dmfile.read_tag_data(tag)))
        else:
            print(indent_level * '\t' + str(k) + '\t' + str(tags[k]))
    
    indent_level -= 1

class testDM4(unittest.TestCase):

    def test(self):
        dmdir = os.path.join('D:\\','Data','Nietz')
        dmfullpath = os.path.join(dmdir,'Glumi1_3VBSED_stack_01_slice_0476.dm4')
        dmfile = dm4reader.DM4File.open(dmfullpath)
        
        tags = dmfile.walk_tags()
        print_tag_dict(dmfile, tags)
         
        dmfile.close()