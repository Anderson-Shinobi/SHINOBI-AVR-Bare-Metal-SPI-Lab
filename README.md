# SHINOBI AVR Bare-Metal SPI Lab

**From Physics to Firmware | Arduino Uno R3 / ATmega328P | MIT License**

> **Status:** AVR-GCC build and two Wokwi VCD investigations completed. **PARTIAL PASS:** 1 MHz clock and loopback data validated in simulation. **OPEN:** CPOL=1 idle clock remains LOW in both captures, contrary to expected HIGH. Physical Arduino Uno has not been tested.

This is an **independent repository** linked from the [SHINOBI Engineering portfolio](https://anderson-shinobi.github.io/). The firmware uses AVR peripheral registers directly; `setup()` and `loop()` are invoked by Wokwi's standard Arduino start-up scaffold. No `SPI.h`, `Wire.h`, `Serial`, or Arduino high-level pin APIs are used.

## Experiment

Hardware SPI master; SPCR/SPSR/SPDR; 1 MHz at 16 MHz MCU; modes 0–3; D11 MOSI→D12 MISO loopback; SS D10; SCK D13; UART 9600 bps.

## Run in Wokwi

**[▶ Open the saved SPI Bare-Metal lab in Wokwi](https://wokwi.com/projects/477544744412189697)**

1. Open the saved project in Wokwi, then start the simulation.
2. Inspect the UART messages and analyzer channels.
3. After allowing the four modes to run, press **Stop** to download the **VCD** capture.
4. Analyze SCK frequency, CPOL/CPHA, MOSI, MISO and SS from the captured transitions.
5. Compare measurement with nominal values; do not treat UART `LOOPBACK_PASS` alone as evidence of verified timing.

Alternatively, open a [new Arduino Uno editor](https://wokwi.com/projects/new/arduino-uno) and import the versioned `sketch.ino` and `diagram.json` from this repository. A saved Wokwi project is independently editable, so use GitHub as the reference source for controlled revisions.

Expected UART: SPI mode 0/1/2/3 and three LOOPBACK_PASS reports per mode for A5, 3C and 5A. Loopback is NOT a slave compatibility test. Logic analyzer D0=SCK, D1=MOSI, D2=MISO, D3=SS; attach GND.

## First Wokwi measurement — original VCD

- [Experimental report: SPI clock, loopback and CPOL observation](evidence/VCD_VALIDATION.md)
- [Original 12.30-second VCD capture](evidence/shinobi-spi-loopback.vcd) — SHA-256 recorded in report.
- [Captured data table](evidence/measurements.csv)
- [Automated VCD regression test](tests/test_spi_capture.py) executed in GitHub Actions.
- **Measured:** SCK 1 MHz, HIGH/LOW 500 ns, 11 SS-low transactions, 33 matching MOSI/MISO bytes (`A5 3C 5A`).
- **Open anomaly:** mode-2/3 CPOL expects SCK idle HIGH, but the capture shows SCK LOW immediately before SS assertion. Do not claim full phase/polarity validation yet.

## CPOL diagnostic (follow-up experiment)

The original VCD identified an **open CPOL=1 idle-level anomaly** in modes 2 and 3. The baseline firmware remains unchanged.

- [Diagnostic overview and Wokwi instructions](diagnostics/cpol_probe/README.md)
- [Alternate diagnostic firmware](diagnostics/cpol_probe/sketch.ino)
- [Wokwi analyzer circuit with mode and idle markers](diagnostics/cpol_probe/diagram.json)

Use a **new Wokwi project**, not the saved baseline simulation. It adds separate analyzer channels for two mode bits and an idle-window marker, and sends three SPI bytes without interleaved UART output while chip select is asserted. Its own AVR compilation is checked in CI. **Do not mark the anomaly resolved until a new VCD demonstrates it.**

## CPOL idle-window diagnostic — second VCD recorded

The [isolated CPOL diagnostic](diagnostics/cpol_probe/README.md) was executed in Wokwi and a **9.40-second VCD capture** was decoded.

- [Second CPOL diagnostic report](evidence/CPOL_IDLE_PROBE_VALIDATION.md)
- [Original CPOL diagnostic VCD](evidence/shinobi-spi-cpol-probe-2026-10-11.vcd)
- **PASS:** 1 MHz median SCK, 7 complete transactions, 21 matching MOSI/MISO bytes.
- **REPRODUCED ANOMALY:** in **6 idle windows with nominal CPOL=1**, SCK remained **LOW**, not the expected HIGH. The mode marker and idle marker lines confirm which mode and window were observed.
- **OPEN:** full CPOL/CPHA electrical/protocol qualification; origin of the Wokwi behavior is not established. Physical hardware has not been tested.

The original firmware and original Wokwi simulation remain unchanged.

## Measurement acceptance criteria

Check fSCK≈1 MHz, all CPOL/CPHA modes, SS LOW during burst, sampled MOSI and MISO matching. Save VCD only after simulator Stop.

The waveform and physical board still require independent validation. The AVR-GCC workflow compiles only an object (`.o`) and does not itself prove that the firmware works in the simulator or silicon.

## Build on Linux Mint

```bash
sudo apt-get install -y gcc-avr avr-libc
avr-g++ -std=gnu++11 -Os -Wall -Wextra -Werror -mmcu=atmega328p -DF_CPU=16000000UL -x c++ -c sketch.ino -o /tmp/shinobi-lab.o
python3 -m unittest discover -s tests -v
```

## Repository files

- [sketch.ino](sketch.ino) — firmware implemented through peripheral registers
- [diagram.json](diagram.json) — Wokwi circuit and analyzer connections
- [.github/workflows/ci.yml](.github/workflows/ci.yml) — AVR compile and static tests
- [tests/test_lab.py](tests/test_lab.py) — static structure and wiring assertions
- [LICENSE](LICENSE) — MIT © 2026 Anderson Nogueira

## Roadmap

**Next:** pass GitHub CI → run Wokwi → collect VCD → inspect timing, protocol and error cases → repeat on an actual Arduino Uno → compare traces.

**SHINOBI Engineering — Don't just write drivers. Measure the bus.**
