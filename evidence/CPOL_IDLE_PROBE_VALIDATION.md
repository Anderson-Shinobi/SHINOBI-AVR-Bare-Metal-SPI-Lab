# CPOL idle-window probe — Wokwi SPI diagnostic #2

**Status: clock and loopback PASS; CPOL=1 idle-level observation FAIL / unresolved root cause.**

This experiment isolates the unexpected SCK idle LOW state observed in the [initial SPI VCD](VCD_VALIDATION.md). It uses additional mode and idle-window marker lines from the [separate CPOL probe](../diagnostics/cpol_probe/README.md). The baseline SPI firmware remains unchanged.

## Provenance and capture

- **Source:** [shinobi-spi-cpol-probe-2026-10-11.vcd](shinobi-spi-cpol-probe-2026-10-11.vcd), original user-provided Wokwi analyzer output, not regenerated
- **SHA-256:** `5f1a9958a3ed533ff2b1c5a17d55e817470b650b8ed2139a40b205366d26fb3d`
- **Bytes:** 9,755; **1,289 lines**; **duration:** 9.398922750 seconds
- **Header date:** `Sun, 11 Oct 2026 01:32:13 GMT`; time scale **1 ns**
- **Signals:** D0/SCK, D1/MOSI, D2/MISO, D3/SS, D4/MODE_LSB, D5/MODE_MSB, D6/IDLE_WINDOW
- **Analysis type:** digital simulator timestamps, not physical voltage measurements

## Objective

Determine whether the SPI clock actually remains HIGH outside transmission for CPOL=1 (modes 2 and 3) while SS is HIGH, as required by SPI clock-polarity semantics. The first VCD lacked an explicit idle marker; this second test provides labeled idle windows before and after every transaction.

## Results

| Quantity | Measured / decoded result |
|---|---:|
| Capture duration | 9.398922750 s |
| Complete SS-low transfers | **7** (initial empty SS=0 initialization excluded) |
| Mode sequence from D4/D5 markers | **0, 1, 2, 3, 0, 1, 2** |
| Transmitted bytes | **21** = 7 × (`A5 3C 5A`) |
| MOSI / MISO transitions | **identical** |
| Clock period within bytes (median) | **1,000 ns** |
| SCK frequency derived from period | **1,000,000 Hz** |
| SCK HIGH/LOW half periods (median) | **500 ns / 500 ns** |
| SS LOW duration (median) | **69.438 µs** |
| IDLE_WINDOW=HIGH periods | **14**; 6 correspond to modes 2/3 |
| Before/after nominal 700 ms / 350 ms marker periods | **~704.13 ms / ~352.07 ms** (latest post-window truncated by capture end) |

Decoded bytes for every complete SS-low transaction:

| Transfer | Mode indicated by D5:D4 | Received via MISO | Transmitted via MOSI |
|---:|---:|---|---|
| 1 | 0 (00) | A5 3C 5A | A5 3C 5A |
| 2 | 1 (01) | A5 3C 5A | A5 3C 5A |
| 3 | 2 (10) | A5 3C 5A | A5 3C 5A |
| 4 | 3 (11) | A5 3C 5A | A5 3C 5A |
| 5 | 0 (00) | A5 3C 5A | A5 3C 5A |
| 6 | 1 (01) | A5 3C 5A | A5 3C 5A |
| 7 | 2 (10) | A5 3C 5A | A5 3C 5A |

MOSI and MISO are intentionally physically tied together, so this validates **simulated loopback**, not an independent SPI slave's data interpretation.

## Explicit CPOL qualification

All 14 labeled pre/post windows had **SS HIGH** and no SCK transition in the window. The captured SCK value was **LOW throughout**. In particular, all **six** mode-2/3 windows (combined ~3.15 s) showed LOW.

| Nominal mode | CPOL | CPHA | Expected SCK idle | Observed SCK idle | Finding |
|---:|---:|---:|---|---|---|
| 0 | 0 | 0 | LOW | LOW | Matches |
| 1 | 0 | 1 | LOW | LOW | Matches |
| 2 | 1 | 0 | **HIGH** | **LOW** | **Discrepancy reproduced** |
| 3 | 1 | 1 | **HIGH** | **LOW** | **Discrepancy reproduced** |

The capture's first recorded active SCK edge is a rising transition even in modes 2/3, instead of the falling leading edge expected for CPOL=1. Some CPHA=1 bursts also contain additional/zero-time boundary transitions in the Wokwi VCD. **Do not interpret byte loopback success as proof of CPOL/CPHA compliance.**

## Reconstruction procedure

1. Parse all scalar transitions against nanosecond timestamps; preserve the original order of equal-time transitions.
2. Determine mode from D4/D5 signals at each SS LOW assertion (mode = D4 + 2 × D5).
3. Ignore the initial startup SS=0 snapshot without active clock edges.
4. Segment bursts by SCK edge gaps greater than 1.5 µs, ignoring isolated trailing transitions; each transfer has 3 groups of 8 clocks.
5. Decode each byte MSB-first using the MOSI/MISO logic level 250 ns after the eight selected rising markers, excluding the initial zero-duration artifact present in some CPHA=1 traces. **This byte reconstruction is a diagnostic convenience, not a complete timing-compliance decoder for every CPHA.**
6. Separately enumerate each D6=HIGH interval, verify SS remains HIGH and inspect SCK for any transition. Check idle HIGH/LOW against mode bits.

## Interpretation and limits

- **Confirmed:** SPI register-driven transfers generated ~1 MHz clock and a repeatable MOSI→MISO loopback.
- **Confirmed:** the simulator capture still reports SCK LOW during CPOL=1 idle windows, despite mode markers and separate pre/post measurement windows.
- **Not established:** whether the underlying cause is Wokwi's AVR SPI peripheral model, VCD export behavior, a subtle firmware/hardware state transition, or another factor.
- **Not established:** definitive CPHA edge setup/hold for a true slave; real-world signals, voltage/timing tolerance, or hardware compatibility.

## Next proposed discriminator test

1. **Read back and log SPCR bits** after each mode selection (especially CPOL/CPHA), without changing the baseline experiment.
2. In an *isolated* follow-up, disable SPI temporarily, drive SCK D13 HIGH as GPIO, and verify the analyzer can capture the HIGH idle reference; then restore SPI and compare. This separates analyzer/connection errors from the SPI peripheral state. Take care that changing DDR/PORT on the SPI SCK output is an intervention, not a normal SPI operation.
3. Repeat with a physical ATmega328P/Uno R3 and logic analyzer when available.
4. If discrepancy persists in Wokwi but not silicon, document the simulator limitation as a hypothesis supported by comparative evidence; do **not** call it a simulator bug solely from these two traces.

## Acceptance status

**PARTIAL PASS:** firmware compiles, 21 decoded loopback bytes match, SCK ≈ 1 MHz. **FAIL / OPEN:** CPOL=1 idle HIGH was not observed in the Wokwi VCD. Do not close full SPI-mode validation yet.

**SHINOBI Engineering — From Physics to Firmware. Don't just write drivers. Measure the bus.**
