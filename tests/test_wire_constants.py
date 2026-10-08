"""The named wire constants must equal the numbers the DM4 format uses on disk.

The values below are written as literals on purpose: they are the independent statement of the
format that `dm4.headers` constants and every reader must agree with. A synthetic file is built
with those literals and read back through `DM4File`, so changing a constant changes the parse.
"""

from __future__ import annotations

import io
import struct
import unittest

from hypothesis import given
from hypothesis import strategies as st

from dm4 import DM4File, headers
from dm4.dm4file import read_tag_header_dm4


def _data_tag(name: bytes, info_types: tuple[int, ...], payload: bytes) -> bytes:
    body = b'%%%%' + struct.pack('>Q', len(info_types)) + struct.pack(f'>{len(info_types)}q', *info_types) + payload
    return struct.pack('>BH', 21, len(name)) + name + struct.pack('>Q', len(body)) + body


def _dm4_file(tags: list[bytes], declared_tags: int) -> bytes:
    """Little-endian DM4: header, root directory counting `declared_tags`, tags, then an end tag."""
    body = struct.pack('>bbQ', 0, 0, declared_tags) + b''.join(tags) + b'\x00'
    return struct.pack('>IQI', 4, len(body), 1) + body


class TestConstantsMatchTheFormat(unittest.TestCase):

    def test_tag_type_values(self):
        self.assertEqual((0, 20, 21), (headers.TAG_TYPE_END, headers.TAG_TYPE_DIRECTORY, headers.TAG_TYPE_DATA))

    def test_data_type_codes(self):
        self.assertEqual((15, 20), (headers.TAG_DATA_TYPE_GROUP, headers.TAG_DATA_TYPE_ARRAY))

    def test_widths_equal_the_struct_widths_they_stand_for(self):
        self.assertEqual(struct.calcsize('>Q'), headers.UINT64_SIZE)
        self.assertEqual(struct.calcsize('>q'), headers.INT64_SIZE)

    def test_derived_header_sizes(self):
        self.assertEqual(16, headers.format_config.header_size)
        self.assertEqual(10, headers.format_config.root_tag_dir_header_size)


class TestSyntheticFileReadsBackThroughTheConstants(unittest.TestCase):

    def test_end_of_tags_byte_ends_the_directory_early(self):
        """A directory that declares more tags than it holds stops at the end tag instead of failing."""
        tag = _data_tag(b'a', (3,), struct.pack('<i', -5))
        with io.BytesIO(_dm4_file([tag], declared_tags=3)) as stream:
            directory = DM4File(stream).read_directory()
            self.assertEqual(['a'], list(directory.named_tags))
            self.assertEqual(-5, DM4File(stream).read_tag_data(directory.named_tags['a']))

    def test_end_tag_header_is_none(self):
        self.assertIsNone(read_tag_header_dm4(io.BytesIO(b'\x00'), '<'))

    def test_nested_directory_is_a_directory_and_a_data_tag_is_not(self):
        inner = _data_tag(b'x', (3,), struct.pack('<i', 1))
        sub = struct.pack('>BH', 20, 3) + b'sub' + struct.pack('>Q', 0) + struct.pack('>bbQ', 0, 0, 1) + inner
        with io.BytesIO(_dm4_file([sub], declared_tags=1)) as stream:
            root = DM4File(stream).read_directory()
            self.assertEqual(['sub'], list(root.named_subdirs))
            self.assertEqual(['x'], list(root.named_subdirs['sub'].named_tags))

    @given(st.lists(st.integers(0, 65535), min_size=0, max_size=40), st.integers(-2 ** 31, 2 ** 31 - 1))
    def test_value_array_and_group_tags_round_trip(self, values, scalar):
        array_tag = _data_tag(b'arr', (20, 4, len(values)), struct.pack(f'<{len(values)}H', *values))
        group_tag = _data_tag(b'grp', (15, 0, 2, 0, 3, 0, 4), struct.pack('<iH', scalar, 9))
        value_tag = _data_tag(b'val', (3,), struct.pack('<i', scalar))
        with io.BytesIO(_dm4_file([array_tag, group_tag, value_tag], declared_tags=3)) as stream:
            f = DM4File(stream)
            tags = f.read_directory().named_tags
            self.assertEqual(values, list(f.read_tag_data(tags['arr'])))
            self.assertEqual([scalar, 9], f.read_tag_data(tags['grp']))
            self.assertEqual(scalar, f.read_tag_data(tags['val']))


if __name__ == '__main__':
    unittest.main()
