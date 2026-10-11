"""Static checks for the independent CPOL idle-window diagnostic.

No simulation claims: Wokwi runtime and captured VCD require separate review.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "diagnostics" / "cpol_probe"


class TestCpolDiagnostic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (PROBE / "sketch.ino").read_text(encoding="utf-8")
        cls.diagram = json.loads((PROBE / "diagram.json").read_text(encoding="utf-8"))

    def test_register_level_and_phase_windows(self):
        for token in ("SPCR", "SPSR", "SPDR", "CPOL", "CPHA",
                      "PORTD7", "PORTB0", "PORTB1", "PORTB2",
                      "PORTB5", "_delay_ms(700)", "_delay_ms(350)",
                      "exchange(tx_bytes[i], received[i])"):
            self.assertIn(token, self.source)
        self.assertIn('PORTB |= _BV(PORTB2); // SS HIGH before UART output.', self.source)
        self.assertNotIn('#include <SPI.h>', self.source)

    def test_all_analyzer_channels_and_loopback(self):
        pairs = {(wire[0], wire[1]) for wire in self.diagram["connections"]}
        expected = {
            ("uno:11", "uno:12"),
            ("uno:13", "logic1:D0"),
            ("uno:11", "logic1:D1"),
            ("uno:12", "logic1:D2"),
            ("uno:10", "logic1:D3"),
            ("uno:8", "logic1:D4"),
            ("uno:9", "logic1:D5"),
            ("uno:7", "logic1:D6"),
            ("uno:GND.2", "logic1:GND"),
        }
        self.assertTrue(expected.issubset(pairs))
        analyzers = [part for part in self.diagram["parts"] if part["type"] == "wokwi-logic-analyzer"]
        self.assertEqual(len(analyzers), 1)
        names = analyzers[0]["attrs"]["channelNames"].split(",")
        self.assertEqual(names[:7],
                         ["SCK", "MOSI", "MISO", "SS",
                          "MODE_LSB", "MODE_MSB", "IDLE_WINDOW"])

    def test_original_stays_isolated(self):
        baseline = (ROOT / "sketch.ino").read_text(encoding="utf-8")
        self.assertNotIn("IDLE_WINDOW", baseline)
        self.assertNotEqual(baseline, self.source)
