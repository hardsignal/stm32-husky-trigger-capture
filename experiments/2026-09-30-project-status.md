# STM32/Husky project status — 2026-09-30

Hardsignal Labs — Researcher: Maciej Duranczyk.

Repository-only status snapshot. No hardware was accessed, no lab scripts were
executed, and no experiment data was modified. Source-code behavior is distinct
from bench verification; bench observations below are operator-reported.

## Current objective

Characterize the STM32 fault oracle, timing, and MCU rail measurements in a
repeatable workflow on owned lab hardware. The immediate measurement priority
is resolving the rail transient before further changes to glitch strength.
Project context: [rail characterization](2026-09-30-rail-droop-characterization.md).

## Oracle behavior and verification limits

[Firmware](../main_fault_oracle.c) and the [oracle note](2026-09-28-fi-fault-oracle.md)
define PA0/A0 as the Husky TIO4 trigger, PA5/D13 as the arithmetic-region marker,
and PA1/A1 as the result oracle. PA1 is cleared before each iteration; PA5 falls
after the workload; the comparison sets PA1 HIGH on equality with `0x8FAEE67B`,
LOW otherwise, before PA0 falls. The verdict is held until the next iteration.
PA1 LOW during boot or computation is not a fault verdict. HIGH reports equality,
not proof of fault-free execution; the oracle alone cannot distinguish reset
from hang.

The September 28 note leaves hardware verification as future work. The later
timing note reports a manually validated workload-end/oracle landmark, and the
rail note reports no oracle anomaly. These support operator-reported timing and
normal-result observations, not a complete independently verified PA0/PA5/PA1
validation record or a demonstrated fault.

## Clean capture and timing status

The [September 29 note](2026-09-29-oracle-glitch-prep.md) reports a clean baseline:
40 MHz ADC, 8,000 samples / 200 µs, with the landmark near 159.0–159.2 µs after
PA0. This timing validation is operator-reported.

[Baseline source](../husky_oracle_baseline.py) configures a 10 MHz system-derived
clock with ADC multiplier 4, basic rising-edge TIO4 triggering, TIO4 high
impedance, zero ADC offset and presamples, decimation 1, one segment, streaming
and test mode off, normal ADC mode, and a 3-second timeout. Gain is retained,
not assigned a documented fixed value. HP/LP are kept off and HS2 disabled.
The timing estimator selects the strongest absolute adjacent-sample transition
within 158.5–159.5 µs, timestamped at the later sample. Low-gain warnings remain
visible; other ADC errors reject the capture. Source settings are not a current
hardware readback.

The same note records HS2 timing-only validation: an event about 159 µs after
PA0 and an approximately 1.1 µs observable pulse. The physical crowbar remained
disconnected throughout those checks. This establishes reported timing behavior,
not measured rail injection or a successful fault. The preparation script was
documented as AST-checked only.

## Manual sweep and rail measurements

The rail note reports a completed manual timing sweep, repeat values 1, 2, 4,
and 8, idle voltage roughly 3.20–3.22 V, minima around 3.12–3.16 V, and no oracle
anomaly. It does not supply a per-offset LP sweep table or explicitly document
LP state during each test. Detailed manual LP offset sweep results therefore
cannot be reconstructed from the repository.

The [CSV](rail_droop_results.csv) now contains one manually entered result:

| Timestamp (UTC) | ext_offset | repeat | Output mode | Idle (V) | Minimum (V) | Mean / RMS (V) | Droop (mV) | Oracle | Capture return |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-09-30T04:36:50+00:00 | 200 | 8 | enable_only | 3.20 | 3.12 | 3.20 / 3.20 | 80.00 | PASS | false |

Recorded HP state and LP state after the test are both `false`. Exact notes:
“Siglent CH1 rail measurement; no oracle anomaly observed”. These are operator
entries, not independently verified instrument readings. The [existing report](rail_droop_report.md)
shows minimum, maximum, and mean droop of 80 mV; this sole row is also the
largest and first baseline, with zero baseline difference. One row cannot
support trend conclusions or causality. The earlier rail note's statement that
individual measurements were not supplied predates the now-present CSV row.

## Tooling and repository hygiene

[rail_droop_log.py](../rail_droop_log.py) provides standard-library-only offline
`init`, `add`, `summary`, `validate`, and `report` commands. Validation checks
required columns, finite voltages and stored droop, minimum no greater than idle,
droop agreement within 0.01 mV, and nonnegative integer repeat/offset. Reports
preserve operator text, include every row, calculated statistics and first-row
comparisons, and end with the Hardsignal Labs footer. No commands were run for
this status snapshot.

Before this file was added, `git status --short` was empty on branch `main` at
`61a784a` (Ignore generated trace and build artifacts). Firmware, helpers, notes,
rail CSV, and report are tracked. Recent commits include `9a91562` (fault oracle
and rail characterization) and `e4cd16b` (ignore Husky capture artifacts).
[.gitignore](../.gitignore) excludes Python caches, generated Husky baseline
directories, selected trace CSVs, and `trigger.elf`; a clean Git status does not
mean ignored artifacts are absent. This status document is the only new change.

## Known issues and safe state

- Intermittent Husky USB disconnects: occurrence and frequency are not established
  by the repository notes reviewed. Baseline code anticipates USB cleanup failures;
  that handling alone does not prove an observed intermittent-disconnect issue.
  The [FI-0 note](2026-09-28-fi-0-recovery-baseline.md) separately documents
  operator-reported OpenOCD/capture recovery dependent on connected-device power state.
- Siglent setup sensitivity: vertical-scale and probe-ground troubleshooting are
  explicitly operator-reported in the rail note.
- Rail droop is not yet well resolved electrically: the available evidence is
  aggregate operator observations and one manual scalar measurement, without a
  rail transient waveform establishing its shape or cause. This is an evidence
  limitation, not a claim that the recorded 80 mV difference is a proven glitch effect.
- Latest documented safe state: **HP=False, LP=False**, operator-reported, not
  freshly read back. There is no automatic crowbar sweep in the documented
  preparation workflow; the rail logger is offline only.

## Next lab step

Improve Siglent transient capture of the MCU-side rail before changing glitch
strength further. This is the next-session plan, not a completed measurement.

## Resume checklist

1. Read this snapshot and the linked rail and timing notes.
2. Review Git status and preserve the existing experiment data.
3. Manually confirm the reported HP=False / LP=False state before bench work.
4. Keep automatic crowbar sweeping out of the workflow.
5. Review the documented power-state recovery issue and any new USB observations.
6. Revisit Siglent vertical scale and probe-ground setup.
7. Improve MCU-side rail transient capture before further strength changes.
8. Record paired readings, actual settings, oracle result, and operator notes.
9. Use the offline validation/report tooling when new measurements are logged.
10. Keep operator reports distinct from independently supported conclusions.
