# Diagnostic 03 — SPCR readback versus SCK GPIO positive control

**Result: GPIO positive control PASS; 1 MHz SPI loopback PASS; CPOL=1 idle-HIGH expectation not observed. Root cause still OPEN.**

## Provenance

- Source: user-uploaded `wokwi-logic(4).vcd`, preserved verbatim as [shinobi-spi-spcr-gpio-probe-2026-10-11.vcd](shinobi-spi-spcr-gpio-probe-2026-10-11.vcd)
- SHA-256 of original file: `9ad29fd607e3ae938691ea8814495b10b779f813fcafd291e82fda3fbd997119`
- Git blob SHA-1: `151e09e3ef90d2253b19a6b86d41685c7fb7050a`
- Wokwi timestamp: **Sun, 11 Oct 2026 01:57:28 GMT**
- Capture duration: **12.416560062 s**; timescale **1 ns**
- File length: **13,481 bytes**; **1,760 lines**
- Diagnostic implementation: [readback/GPIO firmware](../diagnostics/cpol_register_gpio_probe/sketch.ino) and [circuit](../diagnostics/cpol_register_gpio_probe/diagram.json)
- Captured signals: SCK, MOSI, MISO, SS, MODE_LSB, MODE_MSB, WINDOW, SPI_ENABLED.

**These are Wokwi digital-simulation measurements, not physical hardware measurements.**

## Key findings

| Observation | Result |
|---|---:|
| Mode sequence from D4/D5 | **0,1,2,3,0,1,2,3,0** |
| Complete transfers, excluding startup | **9** |
| Bytes decoded | **27 = 9 × (A5 3C 5A)** |
| MOSI/MISO waveforms | **Identical timestamps and levels** |
| Median SCK period within byte bursts | **1,000 ns** |
| Derived clock frequency | **1.000 MHz** |
| SCK periods observed | **185 × 1000 ns; 2 × 999 ns; 2 × 1001 ns** |
| GPIO positive-control windows (SPI_ENABLED=0, WINDOW=1) | **9 — SCK HIGH throughout** |
| SPI idle windows (SPI_ENABLED=1, WINDOW=1) | **18 — SCK LOW throughout** |
| SPI idle windows for modes 2/3 (CPOL=1 nominal) | **8 — SCK LOW throughout** |
| Median SS LOW interval for 3 bytes | **69.250 µs** |

The final captured sequence ends during the post-transfer SPI-idle window of the third mode-0 pass. This truncated window is sufficient to observe its idle state but not the complete final 250-ms hold.

### GPIO versus SPI state

The test drove PB5/D13 HIGH as GPIO while SPI was disabled, then drove it LOW before enabling SPI. The logic analyzer recorded the HIGH state in **all nine 251-ms GPIO windows**. Thus, in this test, wiring and analyzer capture of a HIGH level on D13/SCK functioned.

All **18 SPI-controlled pre/post idle windows** showed SCK LOW with no SCK transitions inside the windows. Four nominal mode-2 windows and four nominal mode-3 windows are among those observations.

| Nominal mode | CPOL | CPHA | Captured complete transfers | GPIO D13 / SPI disabled | SCK / SPI enabled, idle |
|---:|---:|---:|---:|---|---|
| 0 | 0 | 0 | 3 | HIGH | LOW (expected) |
| 1 | 0 | 1 | 2 | HIGH | LOW (expected) |
| 2 | 1 | 0 | 2 | HIGH | **LOW (discrepancy)** |
| 3 | 1 | 1 | 2 | HIGH | **LOW (discrepancy)** |

**Interpretation:** a simple failure to connect SCK to the analyzer or capture a HIGH level is unlikely. The discrepancy is associated with the transition from GPIO control to the enabled SPI peripheral **in the simulator**. This evidence alone does not distinguish among a simulator AVR SPI implementation issue, pin-override semantics, or firmware-state interactions.

## SPI transfer integrity

Nine SS LOW transactions contained three byte bursts each, reconstructed using SCK rising-edge sampling 250 ns into HIGH and excluding the extra zero-duration start edge in some CPHA=1 traces.

Each yielded **A5 3C 5A** on both MOSI and MISO. The two lines are explicitly wired together; this demonstrates **simulated loopback**, not independent slave compatibility or conformance to every SPI phase setup/hold requirement.

The first burst of some CPHA=1 transfers includes an extra or zero-time SCK boundary transition in the VCD. Do not claim CPHA timing compliance from this loopback alone.

## Serial Monitor readback — **now received and independently archived**

**Important:** the eight-channel VCD itself does **not** contain any UART messages. Since this original VCD report was prepared, the author provided a separate [full Serial Monitor log](spcr_gpio_serial_monitor_original.md), analyzed in the [companion register-readback report](SPCR_SERIAL_READBACK_VALIDATION.md).

All **124 logged transactions** (31 repetitions of modes 0–3) report `REQUESTED_SPCR == READBACK_SPCR`:

| Mode | Requested SPCR | Readback SPCR | CPOL | CPHA |
|---:|---|---|---:|---:|
| 0 | `0x51` | `0x51` | 0 | 0 |
| 1 | `0x55` | `0x55` | 0 | 1 |
| 2 | `0x59` | `0x59` | 1 | 0 |
| 3 | `0x5D` | `0x5D` | 1 | 1 |

Every mode record has `GPIO_SCK=1`, `SPI_IDLE_PRE=0` and `SPI_IDLE_POST=0`; all **372 loopback bytes** passed. The CPU-side SPCR readback strengthens the hypothesis that **simulated peripheral-to-pin behavior** should be investigated, since the register image contains CPOL=1 but the pin sample and analyzer show LOW.

**Timing limitation:** the serial log contains many more repetitions than this 9-transfer VCD and no timestamps. It cannot be correlated transaction-by-transaction with the VCD. The suspected simulator/peripheral cause remains a **hypothesis**, not a confirmed defect.

## Reproduction

Run [test_spcr_gpio_vcd.py](../tests/test_spcr_gpio_vcd.py) with `python3 -m unittest discover -s tests -v`. Its tests check integrity, mode order, nine GPIO and 18 SPI idle windows, eight CPOL=1 SPI-idle windows, clock period, and 27 matching loopback bytes. The tests record the discrepancy, not a specification-compliance PASS.

## Status

- **PASS:** analyzer can capture D13 HIGH under software GPIO control.
- **PASS:** AVR peripheral emits 1 MHz clock during transactions and the MOSI/MISO loopback bytes match.
- **FAIL against nominal CPOL expectation:** idle SCK remains LOW for modes 2 and 3 even after the new GPIO-positive-control experiment.
- **OPEN:** actual SPCR readback, cause of peripheral pin behavior, CPHA compliance, behavior with a true SPI slave, and physical-board validation.

**SHINOBI Engineering — From Physics to Firmware. Don't just write drivers. Measure the bus.**
