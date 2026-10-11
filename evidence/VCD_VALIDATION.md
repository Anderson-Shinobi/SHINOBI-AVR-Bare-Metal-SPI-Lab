# SPI logic-analyzer validation — Wokwi capture 2026-10-11

> **Status: partial PASS (clock + loopback), OPEN observation for CPOL/CPHA waveform qualification.** Compiled firmware and repeatable loopback results are not a substitute for a fully compliant SPI slave or real oscilloscope measurements.

## Evidence provenance

- Simulator: [saved Wokwi project](https://wokwi.com/projects/477544744412189697)
- Source: [shinobi-spi-loopback.vcd](shinobi-spi-loopback.vcd), uploaded by the author
- Wokwi header timestamp: `Sun, 11 Oct 2026 01:14:44 GMT`
- Original bytes: **14,355**; capture span: **12.299548437 s**; timescale: **1 ns**
- Original SHA-256: `245140bb24a83f3fa3515d875ae6757e1e2ce9eac057b9f39ea4776bfcbf7d52`
- Signals: `SCK` (Uno D13), `MOSI` (D11), `MISO` (D12), `SS` (D10). MOSI wired directly to MISO.

## Method

Parse VCD scalar events and nanosecond timestamps. Exclude the initial ~0.104 ms SS-low state, which contains no clock pulses. Each subsequent SS-low region contains three distinct bursts of eight SCK pulses separated by UART logging delays. Decode MOSI and MISO MSB-first at 250 ns after the appropriate rising-edge markers, excluding a zero-width initial edge where the simulator emitted one. Measure 1 MHz from rising-edge separations **within** byte bursts; do not compute over interbyte or intertransaction pauses. Determine idle SCK from the latest recorded clock state just before each falling SS edge.

Sampling 250 ns into a high clock phase is a convenient loopback-data reconstruction here; it is **not** equivalent to independently proving phase-specific setup/hold timing for all four modes.

## Measurements

| Quantity | VCD result |
|---|---:|
| Clock frequency within transfers (median) | **1,000,000 Hz** |
| Clock period (median) | **1,000 ns** |
| Clock pulse HIGH / LOW (median) | **500 ns / 500 ns** |
| Per-transfer byte bursts | **3** |
| Completed SS-low transactions (excluding startup) | **11** |
| Decoded bytes | **33** |
| MOSI/MISO bitstream comparison | **Identical transitions** |
| Reconstructed MOSI and MISO bytes | **11 × A5 3C 5A** |
| SS asserted per transaction (median) | **~96.756 ms** |

Mode labels reflect the firmware's intended `SPCR` sequence; they have **not** been independently proved from complete CPOL/CPHA waveforms:

| Nominal mode | CPOL | CPHA | Transactions captured | Each decoded byte sequence | SCK idle immediately before SS LOW |
|---:|---:|---:|---:|---|---:|
| 0 | 0 | 0 | 3 | A5 3C 5A | LOW |
| 1 | 0 | 1 | 3 | A5 3C 5A | LOW |
| 2 | 1 | 0 | 3 | A5 3C 5A | **LOW — unexpected** |
| 3 | 1 | 1 | 2 | A5 3C 5A | **LOW — unexpected** |

The capture ends in the third repeated sequence, before its Mode 3 transaction.

## Observations requiring follow-up

1. **CPOL idle anomaly:** Expected SCK idle HIGH when CPOL=1 (modes 2/3). Immediately before each SS assertion, the VCD last records SCK LOW instead. CPOL-level compliance is therefore **not verified**. Possible causes must be investigated, including how Wokwi models and exports SPI-pin changes; do not assume simulator error or firmware correctness without another experiment.
2. **Clock-transition artifacts:** The first burst of some odd-mode transactions includes an extra SCK edge, sometimes with zero time separation. Review phase boundaries before making claims about CPHA timing.
3. **Long chip-select assertion:** Each SS-low interval lasts about 96.756 ms because the test firmware prints UART diagnostics between the three 8-clock bursts. A real slave might impose frame timing, CS deassertion or transaction-timeout requirements.
4. **Loopback scope:** Identical MOSI/MISO traces prove the electrical loopback data path in simulation, not compatibility with a real SPI peripheral, electrical integrity, or full-duplex slave response.
5. **Not a physical measurement:** Clock tolerance, voltages, rise/fall times, physical EMC and board-level timing remain untested.

## Next acceptance gates

- Repeat capture with a clearly identified CPOL=1 idle window while SS is HIGH and verify the actual SCK level.
- Capture MOSI relative to phase-selected leading and trailing edges; explicitly check CPHA/setup/hold in all four modes.
- Consider changing test harness to report UART results **after** SS deassertion for contiguous SPI bursts, while preserving the driver and its test version as a baseline.
- Add a real SPI slave (or a slave with known timing behavior) and check application-level replies.
- Later compare with Arduino Uno R3 physical board and instrumented clock/data lines.

**SHINOBI Engineering — From Physics to Firmware. Don't just write drivers. Measure the bus.**
