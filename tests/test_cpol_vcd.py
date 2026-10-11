"""Regression checks for the Wokwi CPOL probe VCD (not a physical SPI certification)."""
from bisect import bisect_right
from collections import Counter
from hashlib import sha256
from pathlib import Path
from statistics import median
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "evidence/shinobi-spi-cpol-probe-2026-10-11.vcd"
EXPECTED_SHA256 = "5f1a9958a3ed533ff2b1c5a17d55e817470b650b8ed2139a40b205366d26fb3d"


def parse():
    by_id, signals = {}, {}
    now = 0
    in_data = False
    for line in CAPTURE.read_text(encoding="utf-8").splitlines():
        if line.startswith("$var "):
            parts = line.split()
            by_id[parts[3]] = parts[4]
            signals[parts[4]] = []
        elif line.startswith("$enddefinitions"):
            in_data = True
        elif in_data and line.startswith("#"):
            now = int(line[1:])
        elif in_data and len(line) >= 2 and line[0] in "01" and line[1:] in by_id:
            signals[by_id[line[1:]]].append((now, int(line[0])))
    return signals


def at(signal, t):
    times = [x[0] for x in signal]
    i = bisect_right(times, t) - 1
    if i < 0:
        raise AssertionError("Requested sample precedes initial state")
    return signal[i][1]


def decoded(signals):
    frames, periods = [], []
    sck = signals["SCK"]
    for i, (start, level) in enumerate(signals["SS"][:-1]):
        if level:
            continue
        end, following = signals["SS"][i + 1]
        assert following == 1
        activity = [(t, v) for t, v in sck if start <= t < end]
        if len(activity) <= 1:
            continue  # Startup SS=0 snapshot, not a transfer.
        mode = at(signals["MODE_LSB"], start+1) + 2 * at(signals["MODE_MSB"], start+1)
        bursts = []
        for edge in activity:
            if not bursts or edge[0]-bursts[-1][-1][0] > 1500:
                bursts.append([edge])
            else:
                bursts[-1].append(edge)
        bursts = [burst for burst in bursts if len(burst)>4]
        assert len(bursts) == 3
        bytepairs = []
        for burst in bursts:
            rises = [t for t, v in burst if v==1]
            if len(rises) == 9:
                rises = rises[1:]  # VCD's initial zero-time CPHA boundary artifact.
            assert len(rises) == 8
            periods.extend(b-a for a, b in zip(rises, rises[1:]))
            result = []
            for signal in ("MOSI", "MISO"):
                n = 0
                for t in rises:
                    n = (n << 1) | at(signals[signal], t+250)
                result.append(n)
            bytepairs.append(tuple(result))
        frames.append((mode, bytepairs, (end-start)/1000))
    return frames, periods


def idle_windows(signals):
    rows = []
    marker = signals["IDLE_WINDOW"]
    for i, (start, val) in enumerate(marker):
        if val != 1:
            continue
        end = marker[i+1][0] if i+1 < len(marker) else signals["SCK"][-1][0]
        mode = at(signals["MODE_LSB"], start+1) + 2 * at(signals["MODE_MSB"], start+1)
        transitions = [t for t, _ in signals["SCK"] if start <= t < end]
        rows.append((mode, at(signals["SS"], start+1),
                     at(signals["SCK"], start+1), at(signals["SCK"], end-1),
                     len(transitions)))
    return rows


class TestCpolVcd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.signals = parse()
        cls.frames, cls.periods = decoded(cls.signals)
        cls.windows = idle_windows(cls.signals)

    def test_original_capture_integrity(self):
        self.assertEqual(CAPTURE.stat().st_size, 9755)
        self.assertEqual(sha256(CAPTURE.read_bytes()).hexdigest(), EXPECTED_SHA256)

    def test_clock_and_loopback(self):
        self.assertEqual([mode for mode, *_ in self.frames], [0, 1, 2, 3, 0, 1, 2])
        self.assertEqual(median(self.periods), 1000)
        self.assertTrue(all(999 <= p <= 1001 for p in self.periods))
        self.assertEqual(median(duration for _, _, duration in self.frames), 69.438)
        self.assertEqual(self.signals["MOSI"], self.signals["MISO"])
        for _, pairs, _ in self.frames:
            self.assertEqual(pairs, [(0xA5,0xA5),(0x3C,0x3C),(0x5A,0x5A)])

    def test_idle_cpol_observation(self):
        self.assertEqual(len(self.windows), 14)
        self.assertEqual(Counter(mode for mode, *_ in self.windows),
                         Counter({0:4, 1:4, 2:4, 3:2}))
        # Observation: CPOL=1 expected HIGH, but simulator reports LOW.
        for mode, ss, sck_start, sck_end, transitions in self.windows:
            self.assertEqual(ss,1)
            self.assertEqual((sck_start,sck_end,transitions),(0,0,0))


if __name__=="__main__":
    unittest.main()
