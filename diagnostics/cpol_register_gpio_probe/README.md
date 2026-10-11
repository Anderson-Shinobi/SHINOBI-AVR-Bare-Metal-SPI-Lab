# Diagnostic 03 — SPCR readback vs GPIO-controlled SCK

**Goal:** discriminate between a failure to configure CPOL/CPHA, a simulator/analyzer signal-capture limitation, and actual SPI pin behavior. This experiment is deliberately separate from the baseline project and from Diagnostic 02. **No diagnosis of the root cause has yet been established.**

The first two Wokwi VCD captures confirmed 1 MHz clock and loopback data but showed **SCK LOW in modes 2 and 3 even in marked idle windows** where CPOL=1 would normally imply HIGH.

## How to run (Linux Mint or browser)

1. Open a **new** [Wokwi Arduino Uno project](https://wokwi.com/projects/new/arduino-uno). Do **not** overwrite the original [LAB 02 project](https://wokwi.com/projects/477544744412189697).
2. Copy [this firmware](sketch.ino) to the new project's `sketch.ino`.
3. Copy [this circuit](diagram.json) to its `diagram.json`. The SPI MOSI(D11)–MISO(D12) loopback and analyzer ground are preconnected.
4. Run for **at least 9 seconds** to capture a cycle of all four modes and their labeled windows. Check the Serial Monitor for `GPIO_SCK=1`, `READBACK_CPOL`, `SPI_IDLE_PRE`, `SPI_IDLE_POST` and `LOOPBACK_PASS`.
5. Press **Stop** to download `shinobi-spi-spcr-gpio-probe.vcd`. Send the VCD to ChatGPT to correlate serial output and measured SCK.

This diagnostic is also compiled in GitHub Actions with AVR-GCC, independently from the baseline sketch.

## Analyzer channels

| Analyzer | Uno | Signal |
|---|---|---|
| D0 | D13/PB5 | **SCK**; forced HIGH as GPIO before SPI takes over |
| D1 | D11/PB3 | MOSI |
| D2 | D12/PB4 | MISO, loopback to MOSI |
| D3 | D10/PB2 | SS (active LOW) |
| D4 | D8/PB0 | Mode bit 0 |
| D5 | D9/PB1 | Mode bit 1 |
| D6 | D7/PD7 | **WINDOW** (HIGH during measurements) |
| D7 | D6/PD6 | **SPI_ENABLED** marker (HIGH when hardware SPI enabled) |
| GND | GND | Analyzer reference ground |

The mode is `D4 + 2 * D5`. **WINDOW HIGH and SPI_ENABLED LOW** denotes the GPIO-positive-control stage. **WINDOW HIGH and SPI_ENABLED HIGH** denotes an SPI-controlled idle stage; before/after transfers are distinguished by SS pulses.

## Execution sequence per mode

1. **GPIO positive control:** `SPCR=0`, SCK/PB5 output latch HIGH, GPIO marker combination `WINDOW=1`, `SPI_ENABLED=0`. Duration **250 ms**. Firmware reads `PINB5` as `GPIO_SCK` and analyzer should show SCK HIGH.
2. **Controlled handover:** return GPIO SCK LOW and wait ~40 ms while peripheral disabled.
3. **SPI pre-window:** write SPCR with SPE/MSTR/SPR0 plus CPOL/CPHA, set `SPI_ENABLED=1`, wait ~40 ms, then `WINDOW=1` for **400 ms**. Firmware captures `SPCR` readback and `PINB5`.
4. **Transmission:** `WINDOW=0`, `SS=0` and transfer `0xA5, 0x3C, 0x5A` contiguously at **1 MHz nominal**.
5. **SPI post-window:** `SS=1`, `WINDOW=1` for **250 ms**. Capture `PINB5` again.
6. Turn SPI off, print the captured register/pin states to UART 9600 bps, and move to next mode.

`SPCR` readback verifies the register image but is **not itself proof** that SCK followed the specification. The PINB sample helps check the digital pin state; the VCD provides an independent time-resolved record **within the simulator**.

## Expected discriminators

| Case | GPIO forced HIGH / analyzer | SPCR CPOL for mode 2/3 | SPI idle on D13/PINB |
|---|---|---|---|
| A | HIGH / HIGH | 1 | HIGH: previous observation may have depended on earlier test setup |
| B | HIGH / HIGH | 1 | LOW: investigate SPI peripheral model, pin override, DDR and port behavior |
| C | HIGH / LOW | any | any: investigate wiring, analyzer channel assignment or model sampling |
| D | HIGH / HIGH | 0 | LOW: configuration or readback did not select CPOL=1 |

This is a **diagnostic decision matrix**, not a claim that any case has occurred.

## Build manually

```bash
sudo apt install -y gcc-avr avr-libc
avr-g++ -std=gnu++11 -Os -Wall -Wextra -Werror -mmcu=atmega328p -DF_CPU=16000000UL \
    -x c++ -c diagnostics/cpol_register_gpio_probe/sketch.ino -o /tmp/shinobi-spi-spcr-gpio-probe.o
```

**Scope:** only simulated digital logic. Real SPI slave compatibility and physical-board voltage/clock tolerances remain untested. **License:** MIT © 2026 Anderson Nogueira.
