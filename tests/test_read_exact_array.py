"""Reading a DM4 data array must not hold two copies of it (review #157).

`read_tag_data_array` built its result with `array.fromfile`, which grows the buffer as it
reads, so the interpreter holds both the old and the new allocation across each reallocation.
Measured on a real 154.5 MiB DM4 image (`Glumi1_3VBSED_stack_00_slice_0476.dm4`, 9000x9000 at
16 bpp) with tracemalloc:

    read_tag_data_array (array.fromfile)   peak 318.6 MiB   2.06x tile
    exact prealloc + readinto             peak 154.5 MiB   1.00x tile

and the exact version is also **1.45x faster** (median 0.038s against 0.056s over 5 repeats),
since it is one allocation and one bulk read rather than a sequence of reallocating ones.

Worth recording what the measurement corrected, because it changes where the fix belongs.
#157 attributed the excess to a *caller* -- "a second full copy via `.tobytes()`". It is not
there. Every caller pattern measured at the same 318.6 MiB peak:

    importer ReadImageAsNumpy pattern      peak 318.6 MiB   2.06x
    importer ReadImageAsPIL pattern        peak 318.6 MiB   2.06x
    np.frombuffer over the array.array     peak 318.6 MiB   2.06x
    PIL.frombuffer over a memoryview       peak 318.6 MiB   2.06x

The read's own transient peak dominates, so `.tobytes()` never exceeds it, and the zero-copy
caller rewrites that look like the obvious fix save nothing at all -- they even raise the
*resident* figure from 1.00x to 1.06x, because the array.array has to stay alive as the buffer
owner. All the available saving was in the read.

These tests use in-memory streams, so they are fast and need no fixture.
"""

from __future__ import annotations

import array
import io
import struct
import sys
import unittest

from dm4.dm4file import _read_exact_array, system_byte_order


class TestItReadsTheSameBytes(unittest.TestCase):

    def test_a_short_array_round_trips(self):
        values = [1, 2, 3, 4, 5, 65535, 0]
        raw = array.array('H', values).tobytes()
        result = _read_exact_array(io.BytesIO(raw), 'H', len(values))
        self.assertEqual(values, list(result))

    def test_it_matches_array_fromfile_exactly(self):
        """The replacement must be indistinguishable from what it replaced."""
        for type_format in ('b', 'B', 'h', 'H', 'i', 'I', 'f', 'd'):
            with self.subTest(type_format=type_format):
                template = array.array(type_format)
                count = 257
                source = array.array(
                    type_format,
                    [(i % 100) if type_format not in ('f', 'd') else i * 0.5
                     for i in range(count)])
                raw = source.tobytes()

                legacy = array.array(type_format)
                legacy.fromfile(io.BytesIO(raw), count)
                exact = _read_exact_array(io.BytesIO(raw), type_format, count)

                self.assertEqual(legacy.typecode, exact.typecode)
                self.assertEqual(legacy.itemsize, exact.itemsize)
                self.assertEqual(list(legacy), list(exact))
                self.assertEqual(template.itemsize, exact.itemsize)

    def test_it_returns_an_array_array_so_callers_are_unaffected(self):
        result = _read_exact_array(io.BytesIO(b'\x01\x00\x02\x00'), 'H', 2)
        self.assertIsInstance(result, array.array)
        self.assertEqual('H', result.typecode)

    def test_a_zero_length_array_is_empty_and_reads_nothing(self):
        stream = io.BytesIO(b'\xff' * 16)
        result = _read_exact_array(stream, 'H', 0)
        self.assertEqual(0, len(result))
        self.assertEqual(0, stream.tell(), 'a zero-length read must not consume the stream')

    def test_it_stops_at_the_requested_count(self):
        """Trailing bytes belong to the next tag and must not be consumed."""
        raw = array.array('H', [7, 8, 9, 10]).tobytes()
        stream = io.BytesIO(raw)
        result = _read_exact_array(stream, 'H', 2)
        self.assertEqual([7, 8], list(result))
        self.assertEqual(4, stream.tell())
        self.assertEqual([9, 10], list(array.array('H', stream.read())))


class TestTruncationStillRaises(unittest.TestCase):
    """array.fromfile raises EOFError on a short file; that contract is load-bearing."""

    def test_a_truncated_stream_raises_eof_error(self):
        raw = array.array('H', [1, 2, 3]).tobytes()
        with self.assertRaises(EOFError):
            _read_exact_array(io.BytesIO(raw), 'H', 100)

    def test_it_matches_array_fromfile_on_truncation(self):
        raw = array.array('H', [1, 2, 3]).tobytes()
        legacy = array.array('H')
        with self.assertRaises(EOFError):
            legacy.fromfile(io.BytesIO(raw), 100)
        with self.assertRaises(EOFError):
            _read_exact_array(io.BytesIO(raw), 'H', 100)

    def test_the_error_says_how_short_the_file_was(self):
        raw = array.array('H', [1, 2, 3]).tobytes()
        with self.assertRaises(EOFError) as caught:
            _read_exact_array(io.BytesIO(raw), 'H', 100)
        message = str(caught.exception)
        self.assertIn('6 of 200 bytes', message)
        self.assertIn('truncated', message)

    def test_an_empty_stream_raises_rather_than_returning_zeros(self):
        """The buffer is preallocated, so a silent success would return a zeroed tile."""
        with self.assertRaises(EOFError):
            _read_exact_array(io.BytesIO(b''), 'H', 8)


class _DribblingStream(io.RawIOBase):
    """Returns a few bytes per readinto, as a socket or slow pipe would."""

    def __init__(self, payload: bytes, chunk: int):
        self._payload = payload
        self._chunk = chunk
        self._offset = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        remaining = len(self._payload) - self._offset
        if remaining <= 0:
            return 0
        count = min(self._chunk, remaining, len(buffer))
        buffer[:count] = self._payload[self._offset:self._offset + count]
        self._offset += count
        return count


class TestPartialReadsAreLoopedNotDropped(unittest.TestCase):
    """readinto may return fewer bytes than asked for without being at EOF."""

    def test_a_stream_that_dribbles_still_fills_the_array(self):
        values = list(range(300))
        payload = array.array('H', values).tobytes()
        for chunk in (1, 3, 7, 64, 599):
            with self.subTest(chunk=chunk):
                stream = _DribblingStream(payload, chunk)
                result = _read_exact_array(stream, 'H', len(values))
                self.assertEqual(values, list(result))

    def test_a_dribbling_stream_that_ends_early_raises(self):
        payload = array.array('H', [1, 2, 3]).tobytes()
        stream = _DribblingStream(payload, 2)
        with self.assertRaises(EOFError):
            _read_exact_array(stream, 'H', 50)


class TestItHoldsOnlyOneBuffer(unittest.TestCase):
    """The point of the change: peak allocation is the array, not twice the array."""

    def test_peak_allocation_is_close_to_the_array_size(self):
        import tracemalloc

        count = 2_000_000  # 4 MB at 'H'; large enough that a doubling is unmistakable
        payload = array.array('H', bytes(2)) * count
        raw = payload.tobytes()
        del payload

        stream = io.BytesIO(raw)
        tracemalloc.start()
        tracemalloc.reset_peak()
        result = _read_exact_array(stream, 'H', count)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        expected = count * 2
        self.assertEqual(count, len(result))
        self.assertLess(peak, expected * 1.5,
                        f'peak {peak} is more than 1.5x the {expected}-byte array, so a '
                        f'second full buffer is being held')

    def test_array_fromfile_really_does_peak_higher(self):
        """Guards the premise; if array.array stops reallocating, this fix is redundant."""
        import tracemalloc

        count = 2_000_000
        payload = array.array('H', bytes(2)) * count
        raw = payload.tobytes()
        del payload

        tracemalloc.start()
        tracemalloc.reset_peak()
        legacy = array.array('H')
        legacy.fromfile(io.BytesIO(raw), count)
        _, legacy_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        del legacy

        tracemalloc.start()
        tracemalloc.reset_peak()
        exact = _read_exact_array(io.BytesIO(raw), 'H', count)
        _, exact_peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        del exact

        self.assertLess(exact_peak, legacy_peak,
                        f'exact prealloc peaked at {exact_peak}, array.fromfile at '
                        f'{legacy_peak}; the fix is not saving anything')


class TestByteOrderHelperUnchanged(unittest.TestCase):
    """The byteswap decision sits next to the changed code, so pin it."""

    def test_it_reports_the_running_interpreter_order(self):
        self.assertEqual('<' if sys.byteorder == 'little' else '>', system_byte_order())

    def test_it_agrees_with_struct(self):
        native = struct.pack('=H', 1)
        little = struct.pack('<H', 1)
        self.assertEqual('<' if native == little else '>', system_byte_order())


if __name__ == '__main__':
    unittest.main()
