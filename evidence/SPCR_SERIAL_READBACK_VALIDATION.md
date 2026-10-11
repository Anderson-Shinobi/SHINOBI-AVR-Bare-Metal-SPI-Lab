# Diagnostic 03 — Serial Monitor SPCR/PINB readback

**Finding: SPCR readback matches the requested SPI configuration in all 124 logged transactions. The simulated SCK pin is nevertheless LOW during SPI-enabled idle in modes 2 and 3.**

This is a **new source of evidence** completing the separately published [VCD signal investigation](SPCR_GPIO_DIAGNOSTIC_VALIDATION.md). It strengthens the diagnosis but **does not establish that Wokwi itself is defective**.

## Source and integrity

- Original text, preserved verbatim: [spcr_gpio_serial_monitor_original.md](spcr_gpio_serial_monitor_original.md).
- Source: user-supplied Wokwi Serial Monitor output from Diagnostic 03.
- Original file SHA-256: `b289cc3a44714afc44cb90b291a9da4697a7b03cc2fe8ddad8f392496d229bc3`.
- Original Git blob SHA-1: `d6bf3d20a6a41a27bfbe9ba58e342ebaa320c28b`.
- Original size: **26,106 bytes**; 500 lines including Markdown code fences and header.
- Decoded: **124 complete mode records**; **372 TX/RX records**; **31 repetitions of modes 0,1,2,3**.
- The Serial Monitor text contains **no timestamps**, and spans substantially more repetitions than the 12.42-second VCD. Thus its individual transactions cannot be time-aligned one-for-one with the VCD's nine transactions.

## Register readback and pin sample

| Mode | Requested SPCR | Readback SPCR | Readback CPOL | Readback CPHA | Repeats | Matches |
|---:|---|---|---:|---:|---:|---|
| 0 | `0x51` | `0x51` | 0 | 0 | 31 | 31 |
| 1 | `0x55` | `0x55` | 0 | 1 | 31 | 31 |
| 2 | `0x59` | `0x59` | 1 | 0 | 31 | 31 |
| 3 | `0x5D` | `0x5D` | 1 | 1 | 31 | 31 |

In **all 124 records**:

- `REQUESTED_SPCR == READBACK_SPCR`, with correct CPOL/CPHA bits.
- `GPIO_SCK=1` with the SPI peripheral disabled.
- `SPI_IDLE_PRE=0` and `SPI_IDLE_POST=0` from `PINB5`, **even for CPOL=1**.
- The **three bytes `A5 3C 5A`** each return the same value with `LOOPBACK_PASS`: 372/372.
- No `TIMEOUT`, `FAIL_OR_TIMEOUT` or `LOOPBACK_MISMATCH` appears.

## Triangulation with the VCD

The [separate logic analyzer capture](shinobi-spi-spcr-gpio-probe-2026-10-11.vcd) independently recorded:

- SCK HIGH in all **nine GPIO-positive-control** windows (SPI disabled).
- SCK LOW in all **18 SPI-enabled idle** windows, eight of which were in nominal modes 2/3.
- **Nine complete SPI transfers**, 27 matching loopback bytes and median SCK frequency of **1 MHz**.

The Serial Monitor additionally establishes that **the simulated CPU reads back CPOL=1 in SPCR** for modes 2 and 3, even while the CPU's own pin sample and the analyzer both indicate LOW idle SCK.

This rules out a *simple failure of the SPCR register write* in the observed simulated run and makes a **peripheral-to-pin behavior issue within the simulation** a primary hypothesis. It does not independently prove the SPI output driver or pin multiplexer is incorrect: further scrutiny of implementation and comparison against physical ATmega328P or another trusted model would be required.

## Diagnostic decision status

- **PASS:** SPCR requested/readback equality, all four mode-bit combinations, 372/372 loopback bytes.
- **PASS:** GPIO-controlled D13/PB5 HIGH; corroborated by the VCD.
- **REPRODUCED DISCREPANCY:** SPI-controlled idle clock remains LOW while CPOL=1.
- **OPEN:** physical silicon comparison, true SPI-slave CPOL/CPHA setup/hold behavior, exact origin of the Wokwi discrepancy.
- **DO NOT CLAIM:** a fully validated four-mode SPI protocol, physical measurement, or a confirmed simulator bug.

## Reproducibility

```bash
python3 -m unittest discover -s tests -v
```

The [serial log regression test](../tests/test_spcr_serial_log.py) checks SHA-256 integrity, exact register/bit readback, GPIO/PINB states, 31 cycles of four modes, and 372 matching byte transfers. The original firmware, original Wokwi project, and all previous captures remain unchanged.

**SHINOBI Engineering — From Physics to Firmware. Don't just write drivers. Measure the bus.**
