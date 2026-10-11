"""Static checks are not simulator measurements."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class TestSPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = (ROOT / "sketch.ino").read_text()
        cls.diagram = json.loads((ROOT / "diagram.json").read_text())

    def test_registers_modes(self):
        for name in ("SPCR", "SPDR", "SPSR", "CPOL", "CPHA", "SPIF", "DDB3", "DDB4"):
            self.assertIn(name, self.code)
        self.assertIn("mode < 4", self.code)
        self.assertIn("0xA5, 0x3C, 0x5A", self.code)

    def test_wiring(self):
        pairs = {(x[0], x[1]) for x in self.diagram["connections"]}
        for pair in (("uno:11", "uno:12"), ("uno:13", "logic1:D0"),
                     ("uno:11", "logic1:D1"), ("uno:12", "logic1:D2"),
                     ("uno:10", "logic1:D3"), ("uno:GND.2", "logic1:GND")):
            self.assertIn(pair, pairs)

    def test_license(self):
        self.assertIn("MIT License", (ROOT / "LICENSE").read_text())
        self.assertIn("SPDX-License-Identifier: MIT", self.code)
