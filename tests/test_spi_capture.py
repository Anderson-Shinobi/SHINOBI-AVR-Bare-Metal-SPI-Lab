"""Reproduce basic Wokwi SPI VCD observations from original capture.

This test verifies timing and bytes. It does NOT certify all CPOL/CPHA states.
"""
import bisect
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "evidence" / "shinobi-spi-loopback.vcd"
SHA256 = "245140bb24a83f3fa3515d875ae6757e1e2ce9eac057b9f39ea4776bfcbf7d52"
EXPECTED = [0xA5, 0x3C, 0x5A]


def decode_capture():
    events = {"SCK": [], "MOSI": [], "MISO": [], "SS": []}
    identifiers = {}
    in_data = False
    time = 0
    for row in CAPTURE.read_text().splitlines():
        line = row.strip()
        if line.startswith("$var"):
            parts = line.split()
            identifiers[parts[3]] = parts[4]
        if line.startswith("$enddefinitions"):
            in_data = True
            continue
        if not in_data:
            continue
        if line.startswith("#"):
            time = int(line[1:])
        elif len(line) >= 2 and line[0] in "01":
            chan = identifiers.get(line[1:])
            if chan in events:
                events[chan].append((time, int(line[0])))

    clock = events["SCK"]
    mosit = [t for t, _ in events["MOSI"]]
    misot = [t for t, _ in events["MISO"]]
    assert events["MOSI"] == events["MISO"], "Loopback waveforms differ"

    def sampled(times, data, tick):
        index = bisect.bisect_right(times, tick) - 1
        assert index >= 0
        return data[index][1]

    ss = events["SS"]
    frames = []
    periods = []
    for i, (start, level) in enumerate(ss[:-1]):
        if level != 0:
            continue
        end, following = ss[i + 1]
        assert following == 1
        edges = [(t, v) for t, v in clock if start <= t < end]
        if not edges:  # First initial SS-low region has no SCK.
            continue
        bursts = []
        for t, v in edges:
            if not bursts or t - bursts[-1][-1][0] > 10_000:
                bursts.append([(t, v)])
            else:
                bursts[-1].append((t, v))
        assert len(bursts) == 3

        tx_bytes, rx_bytes = [], []
        for burst in bursts:
            rises = [t for t, v in burst if v == 1]
            if len(rises) == 9:  # Extra boundary rise in mode-odd traces
                rises = rises[1:]
            assert len(rises) == 8
            periods.extend([b - a for a, b in zip(rises, rises[1:])])
            tx = 0
            rx = 0
            for t in rises:
                tx = (tx << 1) | sampled(mosit, events["MOSI"], t + 250)
                rx = (rx << 1) | sampled(misot, events["MISO"], t + 250)
            tx_bytes.append(tx)
            rx_bytes.append(rx)

        previous = [v for t, v in clock if t < start]
        idle = previous[-1] if previous else 0
        frames.append((len(frames) % 4, tuple(tx_bytes), tuple(rx_bytes), idle))
    return frames, periods, events


class TestSpiVcd(unittest.TestCase):
    def test_original_hash(self):
        self.assertEqual(len(CAPTURE.read_bytes()), 14355)
        self.assertEqual(hashlib.sha256(CAPTURE.read_bytes()).hexdigest(), SHA256)

    def test_clock_and_bytes(self):
        frames, periods, events = decode_capture()
        self.assertEqual(len(frames), 11)
        self.assertEqual(len(periods), 231)
        self.assertEqual(sorted(set(periods)), [999, 1000, 1001])
        for mode, tx, rx, idle in frames:
            self.assertEqual(tx, tuple(EXPECTED))
            self.assertEqual(rx, tuple(EXPECTED))
        self.assertEqual(events["MOSI"], events["MISO"])

    def test_observed_idle_not_full_cpol_proof(self):
        frames, _, _ = decode_capture()
        # This characterizes *observed* VCD, not the expected CPOL=1 waveform.
        self.assertEqual([idle for mode, tx, rx, idle in frames], [0] * 11)
        self.assertEqual([mode for mode, *_ in frames],
                         [0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2])


if __name__ == "__main__":
    unittest.main()
