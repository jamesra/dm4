"""
A Digital Micrograph 4 (DM4) file reader.
"""

__version__ = "1.0.1"

from dm4.headers import DM4DataType, DM4DirHeader, DM4Header, DM4TagHeader, DM4Config, format_config
from dm4.dm4file import DM4File
