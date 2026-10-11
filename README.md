# SHINOBI AVR Bare-Metal SPI Lab

**From Physics to Firmware | Arduino Uno R3 / ATmega328P | MIT License**

> **Status:** implementation prepared and local structural checks performed. AVR-GCC build on GitHub Actions and execution/measurement in Wokwi must be checked before claiming the protocol was validated.

This is an **independent repository** linked from the [SHINOBI Engineering portfolio](https://anderson-shinobi.github.io/). The firmware uses AVR peripheral registers directly; `setup()` and `loop()` are invoked by Wokwi's standard Arduino start-up scaffold. No `SPI.h`, `Wire.h`, `Serial`, or Arduino high-level pin APIs are used.

## Experiment

Hardware SPI master; SPCR/SPSR/SPDR; 1 MHz at 16 MHz MCU; modes 0–3; D11 MOSI→D12 MISO loopback; SS D10; SCK D13; UART 9600 bps.

## Run in Wokwi

1. Open [Wokwi Arduino Uno](https://wokwi.com/projects/new/arduino-uno).
2. Replace **sketch.ino** and **diagram.json** in that project with the same files from this repository.
3. Start the simulation; inspect the serial monitor and the logic analyzer.
4. Stop and download the **VCD** capture. Send the VCD for quantitative timing and protocol decoding.
5. Keep captured, measured and calculated results separate in the report.

Expected UART: SPI mode 0/1/2/3 and three LOOPBACK_PASS reports per mode for A5, 3C and 5A. Loopback is NOT a slave compatibility test. Logic analyzer D0=SCK, D1=MOSI, D2=MISO, D3=SS; attach GND.

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
