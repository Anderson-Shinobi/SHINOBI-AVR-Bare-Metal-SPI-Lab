"""Regression checks for the original Wokwi SPI SPCR/GPIO probe VCD.

These verify simulator digital observations, NOT actual SPCR UART readback
or physical SPI compliance.
"""
import bisect
from collections import Counter
from hashlib import sha256
from pathlib import Path
from statistics import median
import unittest

ROOT = Path(__file__).resolve().parents[1]
VCD = ROOT / "evidence/shinobi-spi-spcr-gpio-probe-2026-10-11.vcd"
HASH = "9ad29fd607e3ae938691ea8814495b10b779f813fcafd291e82fda3fbd997119"


def parse_vcd():
    ids, signals = {}, {}
    now = 0
    defined = False
    for row in VCD.read_text(encoding="utf-8").splitlines():
        if row.startswith("$var "):
            fields = row.split()
            ids[fields[3]] = fields[4]
            signals[fields[4]] = []
        elif row.startswith("$enddefinitions "):
            defined = True
        elif defined and row.startswith("#"):
            now = int(row[1:])
        elif defined and len(row) >= 2 and row[0] in "01":
            name = ids.get(row[1:])
            if name is not None:
                signals[name].append((now, int(row[0])))
    return signals


def at(sig, t):
    stamps = [x[0] for x in sig]
    j = bisect.bisect_right(stamps, t) - 1
    if j < 0:
        raise ValueError("No initial value for timestamp")
    return sig[j][1]


def mode_at(e, t):
    return at(e["MODE_LSB"], t) + 2 * at(e["MODE_MSB"], t)


def windows(e):
    rows = []
    mark = e["WINDOW"]
    last = max(t for seq in e.values() for t, _ in seq)
    for i, (start, level) in enumerate(mark):
        if level != 1:
            continue
        end = mark[i + 1][0] if i + 1 < len(mark) else last
        if end <= start + 1:
            continue
        enabled = at(e["SPI_ENABLED"], start + 1)
        mode = mode_at(e, start + 1)
        sck_begin = at(e["SCK"], start + 1)
        sck_end = at(e["SCK"], end - 1)
        ss = at(e["SS"], start + 1)
        edges = [t for t, v in e["SCK"] if start < t < end]
        rows.append((mode, enabled, sck_begin, sck_end, len(edges), ss,
                     end - start))
    return rows


def frames(e):
    periods, result = [], []
    for i, (start, level) in enumerate(e["SS"][:-1]):
        if level != 0:
            continue
        end, after = e["SS"][i + 1]
        assert after == 1
        clock = [(t, v) for t, v in e["SCK"] if start <= t < end]
        if len(clock) < 4:
            continue  # Initial empty SS=LOW snapshot.
        mode = mode_at(e, start + 1)
        bursts = []
        for edge in clock:
            if not bursts or edge[0] - bursts[-1][-1][0] > 1500:
                bursts.append([edge])
            else:
                bursts[-1].append(edge)
        bursts = [burst for burst in bursts if len(burst) > 4]
        assert len(bursts) == 3
        values = []
        for burst in bursts:
            rises = [t for t, v in burst if v == 1]
            if len(rises) == 9:
                rises = rises[1:]  # Wokwi CPHA=1 start-edge artifact.
            assert len(rises) == 8
            periods.extend(b - a for a, b in zip(rises, rises[1:]))
            decoded = []
            for name in ("MOSI", "MISO"):
                byte = 0
                for t in rises:
                    byte = byte * 2 + at(e[name], t + 250)
                decoded.append(byte)
            values.append(tuple(decoded))
        result.append((mode, values, (end - start) / 1000))
    return result, periods


class TestSpcrGpioVcd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signals = parse_vcd()

    def test_capture_integrity(self):
        self.assertEqual(VCD.stat().st_size, 13481)
        self.assertEqual(sha256(VCD.read_bytes()).hexdigest(), HASH)
        self.assertEqual(set(self.signals),
                         {"SCK", "MOSI", "MISO", "SS", "MODE_LSB",
                          "MODE_MSB", "WINDOW", "SPI_ENABLED"})

    def test_gpio_positive_control_and_spi_idle(self):
        win = windows(self.signals)
        self.assertEqual(len(win), 27)
        gpio = [w for w in win if w[1] == 0]
        spi = [w for w in win if w[1] == 1]
        self.assertEqual(len(gpio), 9)
        self.assertEqual(len(spi), 18)
        for mode, enabled, initial, final, transitions, ss, duration in gpio:
            self.assertEqual((initial, final, transitions, ss), (1, 1, 0, 1))
            self.assertGreater(duration, 200_000_000)
        for mode, enabled, initial, final, transitions, ss, duration in spi:
            self.assertEqual((initial, final, transitions, ss), (0, 0, 0, 1))
        self.assertEqual(sum(mode in (2, 3) for mode, *_ in spi), 8)

    def test_27_loopback_bytes_and_1mhz_clock(self):
        result, periods = frames(self.signals)
        self.assertEqual([mode for mode, *_ in result],
                         [0, 1, 2, 3, 0, 1, 2, 3, 0])
        self.assertEqual(median(periods), 1000)
        self.assertEqual(Counter(periods), Counter({1000: 185, 999: 2, 1001: 2}))
        self.assertEqual(self.signals["MOSI"], self.signals["MISO"])
        for mode, values, duration_us in result:
            self.assertEqual(values, [(0xA5, 0xA5), (0x3C, 0x3C),
                                      (0x5A, 0x5A)])
            self.assertTrue(69 <= duration_us <= 72)


if __name__ == "__main__":
    unittest.main()
