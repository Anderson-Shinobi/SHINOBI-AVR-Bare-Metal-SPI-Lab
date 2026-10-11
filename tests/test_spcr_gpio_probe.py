"""Static safeguards for Diagnostic 03.

These tests verify implementation structure; Wokwi VCD remains the source
of observed timing and GPIO/SPI state. No live simulation is implied.
"""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "diagnostics" / "cpol_register_gpio_probe"


class TestSpcrGpioProbe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (PROBE / "sketch.ino").read_text(encoding="utf-8")
        cls.diagram = json.loads((PROBE / "diagram.json").read_text(encoding="utf-8"))

    def test_control_stage_and_readback(self):
        for token in (
            "SPCR = 0", "PORTB |= _BV(PORTB5)",
            "PORTB &= static_cast<uint8_t>(~_BV(PORTB5))",
            "const uint8_t spcr_readback = SPCR;",
            "PINB & _BV(PINB5)", "_BV(CPOL)", "_BV(CPHA)",
            "_delay_ms(250)", "_delay_ms(400)",
            'tx_text(" READBACK_SPCR=0x")',
            'tx_text(" GPIO_SCK=")',
            'tx_text(" SPI_IDLE_PRE=")',
            'tx_text(" SPI_IDLE_POST=")',
            "PORTB &= static_cast<uint8_t>(~_BV(PORTB2))",
            "PORTB |= _BV(PORTB2)",
            "mark_window(true)", "mark_spi(true)",
            "mark_spi(false)",
        ):
            self.assertIn(token, self.code)
        self.assertIn("for (uint8_t mode = 0; mode < 4; ++mode)", self.code)
        self.assertNotIn("#include <SPI.h>", self.code)

    def test_mode_and_stage_marker_wiring(self):
        wire_pairs = {(c[0], c[1]) for c in self.diagram["connections"]}
        self.assertTrue({
            ("uno:11", "uno:12"), ("uno:13", "logic1:D0"),
            ("uno:11", "logic1:D1"), ("uno:12", "logic1:D2"),
            ("uno:10", "logic1:D3"), ("uno:8", "logic1:D4"),
            ("uno:9", "logic1:D5"), ("uno:7", "logic1:D6"),
            ("uno:6", "logic1:D7"), ("uno:GND.2", "logic1:GND"),
        }.issubset(wire_pairs))
        names = next(x for x in self.diagram["parts"] if x["id"] == "logic1")["attrs"]["channelNames"]
        self.assertEqual(names.split(","),
                         ["SCK", "MOSI", "MISO", "SS", "MODE_LSB",
                          "MODE_MSB", "WINDOW", "SPI_ENABLED"])

    def test_baseline_unchanged_and_diagnostic_isolated(self):
        original = (ROOT / "sketch.ino").read_text(encoding="utf-8")
        self.assertNotIn("GPIO_SCK", original)
        self.assertNotEqual(self.code, original)
        self.assertIn("SPDX-License-Identifier: MIT", self.code)
