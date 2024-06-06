from __future__ import annotations
import contextlib
from typing import NamedTuple, BinaryIO, Generator, Any
import struct
import array
import sys

import dm4
from dm4.headers import DM4TagHeader, DM4Header, DM4DirHeader
from dm4 import format_config


class DM4File:
    """
    Provides functions for reading data from a DM4 file.
    Maintains an open file handle to the DM4 file.
    """
    _hfile: BinaryIO | None  # Set to None only when the file is closed
    header: DM4Header
    _endian_str: str  # '>' == Little Endian, '<' == Big Endian
    root_tag_dir_header: DM4DirHeader

    @property
    def endian_str(self) -> str:
        """
        '>' == Little Endian
        '<' == Big Endian
        """
        return self._endian_str

    @property
    def hfile(self) -> BinaryIO | None:
        """Handle to the DM4 file.  Set to None only when the file has been closed"""
        return self._hfile

    def __init__(self, filedata: BinaryIO):
        """
        :param file filedata: file handle to dm4 file
        """
        self._hfile = filedata
        self.header = read_header_dm4(self.hfile)
        self._endian_str = _get_struct_endian_str(self.header.little_endian)

        self.root_tag_dir_header = read_root_tag_dir_header_dm4(self.hfile, endian=self.endian_str)

    def close(self):
        """Manually close the file handle if one is not using a context manager"""
        self._hfile.close()
        self._hfile = None

    @staticmethod
    @contextlib.contextmanager
    def open(filename: str) -> Generator[BinaryIO, None, None]:
        """
        Use this method to open a DM4 file.  The file will be closed when the context is exited.

        with DM4File.open(filename) as dm4file:
            do stuff

        :param str filename: Name of DM4 file to open
        :rtype: DM4File
        :return: DM4File object
        """
        hfile = open(filename, "rb")
        try:
            yield DM4File(hfile)
        finally:
            hfile.close()

    def read_tag_data(self, tag: DM4TagHeader) -> Any:
        """Read the data associated with the passed tag"""
        return _read_tag_data(self.hfile, tag, self.endian_str)

    class DM4TagDir(NamedTuple):
        name: str
        dm4_tag: DM4DirHeader
        named_subdirs: dict[str, DM4File.DM4TagDir]
        unnamed_subdirs: list[DM4File.DM4TagDir]
        named_tags: dict[str, DM4TagHeader]
        unnamed_tags: list[DM4TagHeader]

    def read_directory(self, directory_tag: DM4DirHeader | None = None) -> DM4TagDir:
        """
        Read the directories and tags from a dm4 file.  The first step in working with a dm4 file.
        :return: A named collection containing information about the directory
        """

        if directory_tag is None:
            directory_tag = self.root_tag_dir_header

        dir_obj = DM4File.DM4TagDir(directory_tag.name, directory_tag, {}, [], {}, [])

        for iTag in range(0, directory_tag.num_tags):
            tag = read_tag_header_dm4(self.hfile, self.endian_str)
            if tag is None:
                break

            if tag_is_directory(tag):
                if tag.name is None:
                    dir_obj.unnamed_subdirs.append(self.read_directory(tag))
                else:
                    dir_obj.named_subdirs[tag.name] = self.read_directory(tag)
            else:
                if tag.name is None:
                    dir_obj.unnamed_tags.append(tag)
                else:
                    dir_obj.named_tags[tag.name] = tag

        return dir_obj


def tag_is_directory(tag: DM4TagHeader) -> bool:
    return tag.type == 20


def read_header_dm4(dmfile: BinaryIO) -> DM4Header:
    dmfile.seek(0)
    version = struct.unpack_from('>I', dmfile.read(4))[0]  # int.from_bytes(dmfile.read(4), byteorder='big')
    rootlength = struct.unpack_from('>Q', dmfile.read(8))[0]
    byteorder = struct.unpack_from('>I', dmfile.read(4))[0]

    little_endian = byteorder == 1

    return DM4Header(version, rootlength, little_endian)


def _get_endian_str(endian: str | int) -> str:
    """
    DM4 header encodes little endian as byte value 1 in the header
    :return: 'big' or 'little' for use with python's int.frombytes function
    """
    if isinstance(endian, str):
        return endian

    assert (isinstance(endian, int))
    if endian == 1:
        return 'little'

    return 'big'


def _get_struct_endian_str(endian: str | int | bool) -> str:
    """
    DM4 header encodes little endian as byte value 1 in the header.  However, when that convention is followed the wrong
    values are read.  So this implementation is reversed.
    :return: '>' or '<' for use with python's struct.unpack function
    """
    if isinstance(endian, str):
        if endian == 'little':
            return '>'  # Little Endian
        else:
            return '<'  # Big Endian
    else:
        if endian == 1:
            return '>'  # Little Endian
        else:
            return '<'  # Big Endian


def read_root_tag_dir_header_dm4(dmfile: BinaryIO, endian: str | int):
    """Read the root directory information from a dm4 file.
       File seek position is left at end of root_tag_dir_header"""
    if not isinstance(endian, str):
        endian = _get_struct_endian_str(endian)

    dmfile.seek(dm4.format_config.header_size)

    issorted = struct.unpack_from(endian + 'b', dmfile.read(1))[0]  # type: bool
    isclosed = struct.unpack_from(endian + 'b', dmfile.read(1))[0]  # type: bool
    num_tags = struct.unpack_from('>Q', dmfile.read(8))[0]  # DM4 specifies this property as always big endian

    return DM4DirHeader(20, None, 0, issorted, isclosed, num_tags, dm4.format_config.header_size)


def read_tag_header_dm4(dmfile: BinaryIO, endian: str) -> DM4TagHeader | DM4DirHeader | None:
    """Read the tag from the file.  Leaves file at the end of the tag data, ready to read the next tag from the file"""
    tag_header_offset = dmfile.tell()
    tag_type = struct.unpack_from(endian + 'B', dmfile.read(1))[0]
    if tag_type == 20:
        return _read_tag_dir_header_dm4(dmfile, endian)
    if tag_type == 0:
        return None

    tag_name = _read_tag_name(dmfile)
    tag_byte_length = struct.unpack_from('>Q', dmfile.read(8))[0]  # DM4 specifies this property as always big endian

    tag_data_offset = dmfile.tell()

    _check_tag_verification_str(dmfile)

    (tag_array_length, tag_array_types) = _read_tag_data_info(dmfile)

    dmfile.seek(tag_data_offset + tag_byte_length)
    return DM4TagHeader(tag_type, tag_name, tag_byte_length, tag_array_length, tag_array_types[0], tag_header_offset,
                        tag_data_offset)


def _read_tag_name(dmfile: BinaryIO) -> str | None:
    # DM4 specifies this property as always big endian
    tag_name_len = struct.unpack_from('>H', dmfile.read(2))[0]
    tag_name = None
    if tag_name_len > 0:
        data = dmfile.read(tag_name_len)
        try:
            tag_name = data.decode('utf-8', errors='ignore')
        except UnicodeDecodeError:
            tag_name = None
            pass

    return tag_name


def _read_tag_dir_header_dm4(dmfile: BinaryIO, endian: str) -> DM4DirHeader:
    tag_name = _read_tag_name(dmfile)
    tag_byte_length = struct.unpack_from('>Q', dmfile.read(8))[0]  # DM4 specifies this property as always big endian
    issorted = struct.unpack_from(endian + 'b', dmfile.read(1))[0]
    isclosed = struct.unpack_from(endian + 'b', dmfile.read(1))[0]
    num_tags = struct.unpack_from('>Q', dmfile.read(8))[0]  # DM4 specifies this property as always big endian

    data_offset = dmfile.tell()

    return DM4DirHeader(20, tag_name, tag_byte_length, issorted, isclosed, num_tags, data_offset)


def _check_tag_verification_str(dmfile: BinaryIO) -> None:
    """
    DM4 has four bytes of % symbols in the tag.  Ensure it is there. Raises ValueError if the verification string is not present
    """
    garbage_str = dmfile.read(4).decode('utf-8')
    if garbage_str != '%%%%':
        raise ValueError(
            "Invalid tag data garbage string.  This suggests the file is not in DM4 format or is corrupted")


def _read_tag_data_info(dmfile: BinaryIO) -> tuple[int, tuple[int, ...]]:
    # DM4 specifies this property as always big endian
    tag_array_length = struct.unpack_from('>Q', dmfile.read(8))[0]
    format_str = '>' + tag_array_length * 'q'  # Big endian signed long

    tag_array_types = struct.unpack_from(format_str, dmfile.read(8 * tag_array_length))  # type: tuple[int, ...]

    return tag_array_length, tag_array_types


def _read_tag_data(dmfile: BinaryIO, tag: DM4TagHeader, endian: str) -> Any:
    assert (tag.type == 21)
    try:
        endian = _get_struct_endian_str(endian)
        dmfile.seek(tag.data_offset)

        _check_tag_verification_str(dmfile)
        (tag_array_length, tag_array_types) = _read_tag_data_info(dmfile)

        tag_data_type_code = tag_array_types[0]

        if tag_data_type_code == 15:
            return read_tag_data_group(dmfile, tag, endian)
        elif tag_data_type_code == 20:
            return read_tag_data_array(dmfile, tag, endian)

        if tag_data_type_code not in dm4.format_config.data_type_dict:
            # You can replace the exception with "return None" if you want to get the data you can
            # from the file and ignore reading the unknown data types
            raise ValueError("Unknown data type code " + str(tag_data_type_code))
            # print("Unknown data type " + str(tag_data_type_code))
            # return None

        return _read_tag_data_value(dmfile, endian, tag_data_type_code)

    finally:
        # Ensure we are in the correct position to read the next tag regardless of how reading this tag goes
        dmfile.seek(tag.data_offset + tag.byte_length)


def _read_tag_data_value(dmfile: BinaryIO, endian: str, type_code: int) -> Any:
    if type_code not in dm4.format_config.data_type_dict:
        raise ValueError("Unknown data type code " + str(type_code))

    data_type = dm4.format_config.data_type_dict[type_code]
    format_str = _get_struct_endian_str(endian) + data_type.type_format
    byte_data = dmfile.read(data_type.num_bytes)

    return struct.unpack_from(format_str, byte_data)[0]


def read_tag_data_group(dmfile: BinaryIO, tag: DM4TagHeader, endian: str) -> list[Any]:
    endian = _get_struct_endian_str(endian)
    dmfile.seek(tag.data_offset)

    _check_tag_verification_str(dmfile)
    (tag_array_length, tag_array_types) = _read_tag_data_info(dmfile)

    tag_data_type = tag_array_types[0]
    assert (tag_data_type == 15)

    length_groupname = tag_array_types[1]
    number_of_entries_in_group = tag_array_types[2]
    field_data = tag_array_types[3:]

    field_types_list = []  # type: list[int]

    for iField in range(0, number_of_entries_in_group):
        fieldname_length = field_data[iField * 2]
        fieldname_type = field_data[(iField * 2) + 1]  # type: int
        field_types_list.append(fieldname_type)

    fields_data = []
    for field_type in field_types_list:
        field_data = _read_tag_data_value(dmfile, endian, field_type)
        fields_data.append(field_data)

    return fields_data


def system_byte_order() -> str:
    """Fetches the system byte order with the < or > character convention used by struct unpack"""
    return '<' if sys.byteorder == 'little' else '>'


def read_tag_data_array(dmfile: BinaryIO, tag: DM4TagHeader, endian: str) -> array.array:
    dmfile.seek(tag.data_offset)

    _check_tag_verification_str(dmfile)

    (tag_array_length, tag_array_types) = _read_tag_data_info(dmfile)

    assert (tag_array_types[0] == 20)
    array_data_type_code = tag_array_types[1]
    array_length = tag_array_types[2]

    if array_data_type_code == 15:
        raise NotImplementedError("Array of groups length %d and type %d" % (array_length, array_data_type_code))

    assert (len(tag_array_types) == 3)

    data_type = format_config.data_type_dict[array_data_type_code]

    data = array.array(data_type.type_format)
    data.fromfile(dmfile, array_length)

    # Correct the byte order if the machine order doesn't match the file order
    if endian != system_byte_order():
        data.byteswap()

    return data
