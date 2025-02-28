"""
A Digital Micrograph 4 (DM4) file reader.

1.0.1 Initial release
1.0.2 Switched to using Optional typing hint instead of Union for Python <= 3.8 compatibility
"""

__version__ = "1.0.2"

from dm4.headers import DM4DataType, DM4DirHeader, DM4Header, DM4TagHeader, DM4Config, DM4TagDir, format_config
from dm4.dm4file import DM4File
