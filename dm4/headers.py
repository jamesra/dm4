from typing import NamedTuple, Optional


class DM4Header(NamedTuple):
    version: int
    root_length: int
    little_endian: bool


class DM4TagHeader(NamedTuple):
    type: int
    name: str
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
    header_size=4 + 8 + 4,
    root_tag_dir_header_size=1 + 1 + 8,
)
