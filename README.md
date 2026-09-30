# Hardsignal Labs — STM32/Husky Characterization

Independent hardware-security research by Maciej Duranczyk on owned lab hardware.
This project combines synchronized acquisition, a firmware result oracle, and
manual rail measurements. Bench observations below are operator-reported.

## Project goal

Build a repeatable workflow for STM32 fault-oracle, timing, and voltage-glitch
characterization, with recorded measurements and explicit evidence limits.

## Hardware used

- STM32 NUCLEO-F446RE and ChipWhisperer Husky
- Saleae Logic 8 and Siglent oscilloscope
- ST-LINK/V2.1 onboard debugger
- 10 ohm shunt, BB830 breadboard, and analog measurement leads

The documented setup powers the NUCLEO through its own USB connection; Husky
target power is not used. Earlier work includes [differential-shunt measurements](experiments/2026-09-17-differential-shunt.md).

## Oracle design

[main_fault_oracle.c](main_fault_oracle.c) implements a 50-iteration arithmetic workload:

- **PA0/A0:** acquisition trigger connected to Husky TIO4.
- **PA5/D13:** workload marker.
- **PA1/A1:** oracle, cleared before each iteration and set HIGH when the result
  matches `0x8FAEE67B`, before PA0 falls.

The valid verdict follows completion; LOW during boot or computation is not a
fault verdict. See the [oracle design notes](experiments/2026-09-28-fi-fault-oracle.md).

## Clean capture baseline

The operator reports a clean **40 MHz ADC, 8000 samples / 200 µs** baseline.
[Baseline code](husky_oracle_baseline.py) uses basic rising-edge TIO4 triggering,
zero offset/presamples, one segment, and non-streaming acquisition, with HP/LP
off and HS2 disabled. Source settings are not a live hardware-state check.

## Timing validation

The operator reports a **~159 µs workload-end/oracle landmark** after PA0,
manually observed near 159.0–159.2 µs. **HS2 timing-only validation** showed an
event near 159 µs and an approximately 1.1 µs pulse while the physical crowbar
remained disconnected. See the [timing record](experiments/2026-09-29-oracle-glitch-prep.md).

## Rail-droop characterization

The [CSV](experiments/rail_droop_results.csv) contains **one operator-entered result**:

| Idle rail | Minimum rail | Calculated droop | Oracle result |
| --- | --- | --- | --- |
| 3.20 V | 3.12 V | 80 mV | PASS |

The [offline logger](rail_droop_log.py) supports `init`, `add`, `summary`,
`validate`, and `report` using only the Python standard library. The
[report](experiments/rail_droop_report.md) preserves notes and compares logged
measurements against the first row.

## Current findings

- Operator-reported timing validation and rail observations provide a baseline
  for further measurement; no oracle anomaly was reported.
- Latest operator-reported safe state: **HP=False, LP=False**. The documented
  preparation workflow contains no automatic crowbar sweep.
- **No successful fault injection has been demonstrated.**

## Known limitations

- One rail result cannot establish trends or causality; the rail transient is
  not yet well resolved electrically.
- Siglent vertical-scale and probe-ground troubleshooting is operator-reported.
- Detailed per-offset LP sweep results and a complete independent oracle
  validation record are not available in the repository.
- The oracle alone cannot distinguish reset from hang; HIGH reports equality,
  not proof of fault-free execution.

## Next step

Improve Siglent transient capture of the MCU-side rail before changing glitch
strength further.

See the [project status and resume checklist](experiments/2026-09-30-project-status.md)
and [rail-characterization notes](experiments/2026-09-30-rail-droop-characterization.md).
