from __future__ import annotations
from typing import NamedTuple, Optional


class DM4Header(NamedTuple):
    version: int
    root_length: int
    little_endian: bool


class DM4TagHeader(NamedTuple):
    type: int
    # Optional, matching DM4DirHeader: unnamed tags are how DM4 stores ordered sequences such
    # as image dimensions, and read_directory separates them on `name is None`.
    name: Optional[str]
    byte_length: int
    array_length: int
    data_type_code: int
    header_offset: int
    data_offset: int


class DM4DirHeader(NamedTuple):
    type: int
    name: Optional[str]
    byte_length: int
    sorted: bool
    closed: bool
    num_tags: int
    data_offset: int


class DM4Tag(NamedTuple):
    name: str
    data_type_code: int
    data: object


class DM4DataType(NamedTuple):
    num_bytes: int
    signed: bool
    type_format: str


class DM4Config(NamedTuple):
    """
    Configuration for reading a DM4 file, these are unlikely to change
    """

    data_type_dict: dict[int, DM4DataType]
    header_size: int
    root_tag_dir_header_size: int


class DM4TagDir(NamedTuple):
    """Description of a directory in a DM4 file"""
    name: str
    dm4_tag: DM4DirHeader
    named_subdirs: dict[str, DM4TagDir]
    unnamed_subdirs: list[DM4TagDir]
    named_tags: dict[str, DM4TagHeader]
    unnamed_tags: list[DM4TagHeader]


TAG_TYPE_END = 0
"""Tag type byte that ends a directory's tag list early."""
TAG_TYPE_DIRECTORY = 20
"""Tag type byte for a directory of further tags."""
TAG_TYPE_DATA = 21
"""Tag type byte for a tag that holds data."""

TAG_DATA_TYPE_GROUP = 15
"""Data type code for a group (struct) of fields."""
TAG_DATA_TYPE_ARRAY = 20
"""Data type code for an array. Same value as TAG_TYPE_DIRECTORY, but a different field of the file."""

UINT64_SIZE = 8
"""Width in bytes of the big-endian uint64 DM4 uses for lengths and counts."""
INT64_SIZE = 8
"""Width in bytes of each big-endian int64 entry in a tag's data type list."""

format_config = DM4Config(
    {
        2: DM4DataType(2, True, "h"),  # 2byte signed integer
        3: DM4DataType(4, True, "i"),  # 4byte signed integer
        4: DM4DataType(2, False, "H"),  # 2byte unsigned integer
        5: DM4DataType(4, False, "I"),  # 4byte unsigned integer
        6: DM4DataType(4, False, "f"),  # 4byte float
        7: DM4DataType(8, False, "d"),  # 8byte float
        8: DM4DataType(1, False, "?"),
        9: DM4DataType(1, False, "c"),
        10: DM4DataType(1, True, "b"),
        11: DM4DataType(8, True, "q"),
        12: DM4DataType(8, True, "Q"),
    },
    header_size=4 + UINT64_SIZE + 4,
    root_tag_dir_header_size=1 + 1 + UINT64_SIZE,
)
