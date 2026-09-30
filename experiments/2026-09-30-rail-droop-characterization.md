# Rail droop characterization — 2026-09-30

## Project context

This experiment is part of **Hardsignal Labs**, an independent hardware-security lab focused on cyber-physical systems, embedded devices, RF/SDR, fault injection, firmware analysis, and automotive security.

Researcher: Maciej Duranczyk  
Lab: Hardsignal Labs  
Project: STM32 fault-oracle and voltage-glitch characterization

The work is being carried out on owned lab hardware in a controlled bench environment. Measurements, timing validation, oracle behaviour, and rail-characterization results are recorded as part of a repeatable experimental workflow rather than as one-off observations.

The current STM32/Husky work builds on prior bring-up and instrumentation work with J-Link, Saleae, ChipWhisperer Husky, oscilloscope measurements, and controlled power-path characterization.

## Operator-reported results

These observations are operator-reported from manual STM32/Husky bench tests
using Siglent rail measurements. They have not been independently verified.

- Current safe state reported by the operator: HP=False, LP=False.
- The timing sweep has already been completed manually.
- Repeat values tested: 1, 2, 4, and 8.
- Observed idle rail voltage: roughly 3.20–3.22 V.
- Observed minimum rail voltage: around 3.12–3.16 V.
- No oracle anomaly was observed.
- Measurement setup troubleshooting included Siglent vertical scale and probe
  ground issues.

At initial documentation time, individual paired measurements were not supplied;
the aggregate observations above were not converted into test rows. The
[CSV](rail_droop_results.csv) now contains one operator-entered row: 3.20 V idle,
3.12 V minimum, 80 mV calculated droop, oracle PASS. See the
[report](rail_droop_report.md). The example below remains usage syntax; matching
values alone do not establish the logged row's provenance.

## Offline logging

`rail_droop_log.py` uses only the Python standard library and local CSV files.
It does not access hardware, import ChipWhisperer, arm or capture, or control
HP/LP. State, output mode, oracle result, and capture return are manually
reported metadata. Omitted output mode and HP/LP states are recorded as
`unknown`; the current safe state is not assumed for historical tests.

`capture_return` records the reported capture API return: `true` means timeout,
`false` means no timeout, and `unknown` means unreported. It is not an oracle
verdict or a fault classification. `ext_offset` is reported timing metadata,
distinct from ADC sample offset; record the clock context in notes rather than
assuming a time conversion.

From the repository directory:

```bash
python3 rail_droop_log.py init
python3 rail_droop_log.py add --offset 200 --repeat 8 --idle 3.20 --min 3.12 --mean 3.20 --rms 3.20 --oracle PASS --capture false
python3 rail_droop_log.py summary
python3 rail_droop_log.py validate
python3 rail_droop_log.py report
```

Optional metadata flags: `--output-mode`, `--hp-state true|false|unknown`,
`--lp-state-after-test true|false|unknown`, and `--notes`.

The CSV location is `experiments/rail_droop_results.csv`, relative to the script,
regardless of the working directory. `init` creates the header and preserves
existing data. `add` requires an initialized CSV, records a UTC timestamp, and
calculates `droop_mv = (rail_idle_v - rail_min_v) * 1000`. Before appending, it
validates the existing rows and candidate row using the same measurement checks
as `validate`. Appending requires the exact standard CSV column order.
`validate` checks required columns, finite voltages and droop, minimum no greater
than idle, stored/calculated droop agreement within 0.01 mV, and nonnegative
integer repeat/offset. `summary` and `report` use these checks, accept reordered
or additional columns, and calculate droop from idle and minimum voltages.
`summary` prints all stored fields plus calculated droop statistics/comparisons;
`report` writes `experiments/rail_droop_report.md` with all rows, statistics,
largest-droop identification, and comparisons against the first logged baseline.
That baseline is a reference row, not necessarily an unperturbed control.
Comparisons describe entered measurements only and do not establish causality;
one row cannot support trend conclusions.

Validation during the logger/documentation edits was AST parsing only; those
editing sessions did not execute the logger or collect measurements. This
describes the editing scope, not the absence of operator-entered CSV data.
