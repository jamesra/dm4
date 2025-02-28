###
dm4
###

A pure python file reader for Digital Micrograph's DM4 file format

This package would not have been possible without the documentation provided by Dr Chris Boothroyd at http://www.er-c.org/cbb/info/dmformat/ Thank you.

############
Installation
############

Install using pip from the command line::

   pip install dm4

#######
Example
#######
   
Below is a short example of reading the image data from a dm4 file.  A more complete example can be found in the tests.::

   import dm4
   import PIL

   input_path = "your_filename_here.dm4"

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

####
Todo
####

Reading arrays of groups has not been implemented.
