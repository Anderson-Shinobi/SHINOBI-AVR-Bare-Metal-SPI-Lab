# Controlled CPOL=1 idle-window investigation

This is an **isolated diagnostic**, not a change to the original `sketch.ino`. The first captured SPI VCD confirmed a 1 MHz clock and loopback for 33 bytes, but recorded SCK LOW ahead of SS assertion in nominal SPI modes 2/3. That observation is **not** sufficient to identify the root cause.

## Run with Wokwi

1. Open [New Arduino Uno Project](https://wokwi.com/projects/new/arduino-uno) in a **new Wokwi tab**. Keep the saved [main SPI project](https://wokwi.com/projects/477544744412189697) unchanged.
2. Copy [this diagnostic sketch](sketch.ino) into Wokwi `sketch.ino` and [the diagnostic diagram](diagram.json) into Wokwi `diagram.json`.
3. Start simulation, run for **at least 9 seconds** to capture all modes, then press **Stop**. The analyzer should export `shinobi-spi-cpol-probe.vcd`. If the browser blocks downloads, allow the download for Wokwi.
4. Upload the VCD to ChatGPT for channel-by-channel and mode-by-mode analysis. Save the separate Wokwi project only if you want to keep this specific diagnostic.

## Channel wiring

| Analyzer | Uno signal | Meaning |
|---|---|---|
| D0 | D13/PB5 | SCK: idle LOW when CPOL=0, HIGH when CPOL=1 |
| D1 | D11/PB3 | MOSI |
| D2 | D12/PB4 | MISO (wired directly to MOSI) |
| D3 | D10/PB2 | SS / chip select |
| D4 | D8/PB0 | Mode bit0 (LSB) |
| D5 | D9/PB1 | Mode bit1 (MSB) |
| D6 | D7/PD7 | Idle-window marker: HIGH before and after transfer |
| GND | GND | Shared reference |

**Mode = D4 + 2 × D5** (binary). Unlike the original UART-interleaved experiment, the three bytes are sent **without printing during SS LOW**. Results are printed only after SS HIGH.

## Expected test window for each SPI mode

1. SS HIGH, mode selected and CPOL/CPHA configured.
2. D6=HIGH for **700 ms before** the transfer. SCK should be stable at the CPOL idle level.
3. D6=LOW, SS goes LOW and `A5 3C 5A` are exchanged consecutively.
4. SS goes HIGH again.
5. D6=HIGH for **350 ms after** the transfer. SCK should return to the CPOL idle level.

| Mode | D5 | D4 | CPOL | CPHA | Expected SCK while D6=HIGH / SS=HIGH |
|---:|---:|---:|---:|---:|---|
| 0 | 0 | 0 | 0 | 0 | LOW |
| 1 | 0 | 1 | 0 | 1 | LOW |
| 2 | 1 | 0 | 1 | 0 | HIGH |
| 3 | 1 | 1 | 1 | 1 | HIGH |

### Acceptance criteria

- Verify all four mode codes from the **separate marker channels**, not only the UART labels.
- Verify SCK idle level **throughout** the pre/post windows; not just its most recent edge before SS goes LOW.
- Verify SCK edge polarity and MOSI setup relative to leading/trailing edges during transmission.
- Confirm three contiguous bytes with SS asserted, and compare MOSI/MISO.
- Keep 1 MHz as a **nominal frequency** until verified in the new VCD.
- If SCK remains unexpectedly LOW in CPOL=1 windows, treat that as an experimental result to investigate; neither hardware correctness nor simulator fault should be presumed.

## Notes

The time markers only annotate the waveform; they are not SPI signals. Do not connect D8, D9 or D7 to a real SPI slave. This experiment uses the Wokwi simulator and does not validate signal voltages, analog rise/fall times or a physical Arduino Uno.

**License:** MIT — © 2026 Anderson Nogueira.
