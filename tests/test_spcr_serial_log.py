"""Verify the author's original Wokwi UART register-readback transcript.

Separate evidence: this text has no timestamps and must not be treated as a
one-to-one recording of the previously captured 9-transaction VCD.
"""
from collections import Counter
import hashlib
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "evidence" / "spcr_gpio_serial_monitor_original.md"
EXPECTED_HASH = "b289cc3a44714afc44cb90b291a9da4697a7b03cc2fe8ddad8f392496d229bc3"
MODE_RE = re.compile(
    r"^MODE=(\d) REQUESTED_SPCR=0x([0-9A-F]{2}) READBACK_SPCR=0x([0-9A-F]{2}) "
    r"READBACK_CPOL=([01]) READBACK_CPHA=([01]) GPIO_SCK=([01]) "
    r"SPI_IDLE_PRE=([01]) SPI_IDLE_POST=([01])$"
)
BYTE_RE = re.compile(r"^TX=0x([0-9A-F]{2}) RX=0x([0-9A-F]{2}) (LOOPBACK_PASS|FAIL_OR_TIMEOUT|LOOPBACK_MISMATCH)$")
EXPECTED_SPCR = (0x51, 0x55, 0x59, 0x5D)
EXPECTED_BYTES = (0xA5, 0x3C, 0x5A)


def decode():
    records = []
    current = None
    header_count = 0
    fence_count = 0
    for number, text in enumerate(CAPTURE.read_text(encoding="utf-8").splitlines(), 1):
        line = text.strip()
        if not line:
            continue
        if line == "```":
            fence_count += 1
            continue
        if line == "SHINOBI SPI: GPIO SCK control vs SPCR CPOL/CPHA readback":
            header_count += 1
            continue
        match = MODE_RE.fullmatch(line)
        if match:
            if current is not None:
                records.append(current)
            mode, req, got, cpol, cpha, gpio, pre, post = match.groups()
            current = (int(mode), int(req, 16), int(got, 16),
                       int(cpol), int(cpha), int(gpio), int(pre), int(post), [])
            continue
        match = BYTE_RE.fullmatch(line)
        if match:
            if current is None:
                raise AssertionError(f"Byte outside transaction at line {number}")
            tx, rx, status = match.groups()
            current[-1].append((int(tx, 16), int(rx, 16), status))
            continue
        raise AssertionError(f"Unexpected source line {number}: {line[:100]}")
    if current is not None:
        records.append(current)
    return records, header_count, fence_count


class TestSpcrSerialLog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.headers, cls.fences = decode()

    def test_original_integrity_and_source_shape(self):
        self.assertEqual(CAPTURE.stat().st_size, 26106)
        self.assertEqual(hashlib.sha256(CAPTURE.read_bytes()).hexdigest(), EXPECTED_HASH)
        self.assertEqual(self.headers, 1)
        self.assertEqual(self.fences, 2)

    def test_all_mode_register_readbacks(self):
        self.assertEqual(len(self.records), 124)
        self.assertEqual(Counter(record[0] for record in self.records),
                         Counter({0: 31, 1: 31, 2: 31, 3: 31}))
        self.assertEqual([record[0] for record in self.records], [0, 1, 2, 3] * 31)
        for mode, requested, readback, cpol, cpha, gpio, pre, post, chunks in self.records:
            self.assertEqual(requested, EXPECTED_SPCR[mode])
            self.assertEqual(readback, requested)
            self.assertEqual(cpol, (mode >> 1) & 1)
            self.assertEqual(cpha, mode & 1)
            self.assertEqual(gpio, 1)
            self.assertEqual((pre, post), (0, 0))

    def test_all_372_byte_loopbacks(self):
        self.assertEqual(sum(len(x[-1]) for x in self.records), 372)
        for record in self.records:
            self.assertEqual(record[-1],
                             [(b, b, "LOOPBACK_PASS") for b in EXPECTED_BYTES])


if __name__ == "__main__":
    unittest.main()
