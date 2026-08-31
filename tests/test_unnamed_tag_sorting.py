"""Unnamed tags must reach `unnamed_tags`, not collapse into `named_tags[""]` (review #243).

`read_directory` sorts tags with ``if tag_header.name is None``, but
``read_tag_header_dm4`` constructed the header with ``tag_name or ""``. So the test could
never fire: every unnamed tag was filed under ``named_tags[""]``, where a dict has one slot
per key and each tag overwrote the last, and ``unnamed_tags`` was always empty.

DM4 uses unnamed tags for ordered sequences, image dimensions among them, so this discarded
data rather than merely misplacing it -- an image's X and Y both went to the same slot and only
one survived. Measured on `Glumi1_3VBSED_stack_00_slice_0476.dm4`:

    before:  Dimensions named_tags=[''] unnamed_tags=0   -> IndexError on unnamed_tags[0]
    after:   Dimensions named_tags=[]   unnamed_tags=2   -> (9000, 9000)

9000x9000 is 81,000,000 elements, which matches the element count in the Data tag header
exactly, so the recovered dimensions are confirmed by a second independent source.

The directory branch was unaffected because ``_read_tag_dir_header_dm4`` passes the name
through unchanged, which is why ``unnamed_subdirs`` worked while ``unnamed_tags`` never did,
and why `ImageList` could be traversed at all.

Worth recording how long this survived: the annotation on ``DM4TagHeader.name`` was ``str``
while ``DM4DirHeader.name`` was ``Optional[str]``, and the ``or ""`` existed to satisfy it.
A type annotation silently disabled a runtime branch. Both are now Optional.

These tests build DM4 byte streams in memory, so they need no fixture.
"""

from __future__ import annotations

import io
import struct
import unittest

from dm4.dm4file import read_tag_header_dm4
from dm4.headers import DM4DirHeader


def encode_tag(name: bytes | None, payload_type: int = 4, value: int = 7) -> bytes:
    """One DM4 data tag: type byte, name, byte length, then '%%%%' and the data info."""
    body = b'%%%%' + struct.pack('>Q', 1) + struct.pack('>q', payload_type)
    body += struct.pack('>H', value)
    out = struct.pack('>B', 21)
    out += struct.pack('>H', 0 if name is None else len(name))
    if name:
        out += name
    out += struct.pack('>Q', len(body))
    out += body
    return out


class TestTheHeaderKeepsAnAbsentNameAbsent(unittest.TestCase):

    def test_an_unnamed_tag_has_name_none(self):
        header = read_tag_header_dm4(io.BytesIO(encode_tag(None)), '<')
        self.assertIsNone(header.name,
                          'an unnamed tag reported name == "", so read_directory could not '
                          'tell it apart from a tag genuinely named ""')

    def test_a_named_tag_keeps_its_name(self):
        header = read_tag_header_dm4(io.BytesIO(encode_tag(b'PixelDepth')), '<')
        self.assertEqual('PixelDepth', header.name)

    def test_the_two_header_kinds_agree_about_absent_names(self):
        """DM4DirHeader always used None; the mismatch is what produced the defect."""
        tag = read_tag_header_dm4(io.BytesIO(encode_tag(None)), '<')

        dir_stream = io.BytesIO(
            struct.pack('>B', 20) + struct.pack('>H', 0)
            + struct.pack('>Q', 0) + struct.pack('<b', 1) + struct.pack('<b', 1)
            + struct.pack('>Q', 0))
        directory = read_tag_header_dm4(dir_stream, '<')

        self.assertIsInstance(directory, DM4DirHeader)
        self.assertIsNone(directory.name)
        self.assertIsNone(tag.name)


class _FakeFile:
    """Drives read_directory over a synthetic tag stream."""

    def __init__(self, payload: bytes, num_tags: int):
        from dm4.dm4file import DM4File

        self.handle = DM4File.__new__(DM4File)
        self.handle._hfile = io.BytesIO(payload)
        self.handle._endian_str = '<'
        self.root = DM4DirHeader(20, None, len(payload), True, True, num_tags, 0)

    def read_directory(self):
        return self.handle.read_directory(self.root)


class TestReadDirectorySortsThemApart(unittest.TestCase):

    def test_several_unnamed_tags_all_survive(self):
        """The heart of it: a dict keyed on "" kept only the last of them."""
        payload = b''.join(encode_tag(None, value=v) for v in (11, 22, 33))
        result = _FakeFile(payload, 3).read_directory()

        self.assertEqual(3, len(result.unnamed_tags),
                         'unnamed tags collapsed; DM4 stores ordered sequences this way, so '
                         'this loses data rather than misplacing it')
        self.assertEqual({}, result.named_tags)

    def test_unnamed_tags_keep_their_file_order(self):
        """Dimensions are X then Y; order is the only thing distinguishing them."""
        payload = b''.join(encode_tag(None, value=v) for v in (11, 22, 33))
        result = _FakeFile(payload, 3).read_directory()

        offsets = [tag.header_offset for tag in result.unnamed_tags]
        self.assertEqual(sorted(offsets), offsets)

    def test_named_and_unnamed_tags_are_separated(self):
        payload = (encode_tag(b'DataType') + encode_tag(None)
                   + encode_tag(b'PixelDepth') + encode_tag(None))
        result = _FakeFile(payload, 4).read_directory()

        self.assertEqual({'DataType', 'PixelDepth'}, set(result.named_tags))
        self.assertEqual(2, len(result.unnamed_tags))

    def test_a_directory_of_only_named_tags_is_unchanged(self):
        """The common case must not have moved."""
        payload = encode_tag(b'Data') + encode_tag(b'PixelDepth')
        result = _FakeFile(payload, 2).read_directory()

        self.assertEqual({'Data', 'PixelDepth'}, set(result.named_tags))
        self.assertEqual([], result.unnamed_tags)

    def test_an_empty_string_key_no_longer_appears(self):
        payload = b''.join(encode_tag(None) for _ in range(2))
        result = _FakeFile(payload, 2).read_directory()

        self.assertNotIn('', result.named_tags,
                         'the "" key is the signature of the old behaviour')


class TestTheDimensionsPatternWorks(unittest.TestCase):
    """The shape the README documents and the importer relies on."""

    def test_two_dimensions_are_readable_by_index(self):
        payload = encode_tag(None, value=9000) + encode_tag(None, value=7842)
        result = _FakeFile(payload, 2).read_directory()

        self.assertEqual(2, len(result.unnamed_tags))
        # Indexing is what raised IndexError before the fix.
        self.assertIsNotNone(result.unnamed_tags[0])
        self.assertIsNotNone(result.unnamed_tags[1])

    def test_indexing_the_second_dimension_would_have_raised_before(self):
        payload = encode_tag(None, value=9000) + encode_tag(None, value=7842)
        result = _FakeFile(payload, 2).read_directory()

        try:
            result.unnamed_tags[1]
        except IndexError:  # pragma: no cover
            self.fail('unnamed_tags[1] raised, which is exactly the reported symptom')


if __name__ == '__main__':
    unittest.main()
