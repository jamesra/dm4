"""
A Digital Micrograph 4 (DM4) file reader.

1.0.1 Initial release
1.0.2 Switched to using Optional typing hint instead of Union for Python <= 3.8 compatibility
1.0.3 DM4TagDir is now imported with dm4 module to simplify typing.
      Invoking the dm4 module as a script now prints the tag directory tree of a passed DM4 file.
      Removed dependency on the six module
"""

__version__ = "1.0.2"

from dm4.headers import DM4DataType, DM4DirHeader, DM4Header, DM4TagHeader, DM4Config, DM4TagDir, format_config
from dm4.dm4file import DM4File
from dm4.helpers import print_tag_directory_tree, print_tag_data
