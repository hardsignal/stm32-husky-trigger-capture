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
The helper's automated analog landmark estimate does not directly measure a PA1
edge or classify the oracle.

## Rail-droop characterization

The [CSV](experiments/rail_droop_results.csv) contains **one operator-entered result**:

| Idle rail | Minimum rail | Calculated droop | Oracle result |
| --- | --- | --- | --- |
| 3.20 V | 3.12 V | 80 mV | PASS |

The [offline logger](rail_droop_log.py) supports `init`, `add`, `summary`,
`validate`, and `report` using only the Python standard library. The
[report](experiments/rail_droop_report.md) preserves notes and compares logged
measurements against the first row.

## Siglent Ethernet SCPI reader

Connect the SDS1104X-U LAN port to the bench network and configure its network
address on the instrument. Ensure the computer can reach the scope's SCPI TCP
service (bench defaults: `192.168.1.170:5025`). Configure CH1 and the measurement
setup manually before reading. [siglent_read.py](siglent_read.py) uses only Python's
standard library; no PyVISA is needed.

```bash
python3 siglent_read.py
python3 siglent_read.py --host 192.168.1.170 --port 5025 --json
```

The utility sends only `C1:PAVA? MIN`, `C1:PAVA? MEAN`, and `C1:PAVA? RMS`.
It queries current scalar values without configuring or triggering acquisition.
It uses a 3-second connection timeout and 3-second reply deadline per query.
The queries are sequential and need not describe the same acquisition.
PAVA reply syntax follows the [Siglent programming guide](https://siglentna.com/wp-content/uploads/dlm_uploads/2025/11/SDS1000-SeriesSDS2000XSDS2000X-E_ProgrammingGuide_EN02E.pdf).

Example output (illustrative, not a new measurement):

```text
MIN=3.120 V  MEAN=3.190 V  RMS=3.190 V  DROOP=70 mV
```

Here **DROOP = (MEAN - MIN) × 1000 mV**, unlike the rail logger's **idle - MIN**
definition. JSON keys are `min_v`, `mean_v`, `rms_v`, and `droop_mv` (numbers).
Do not copy this droop into the logger as an idle-based result. Errors go to stderr
with a nonzero exit status; no partial result is printed. These scalar readings
alone do not establish a resolved transient waveform or successful fault injection.

Offline checks, with all socket connections mocked:

```bash
python3 -m py_compile siglent_read.py test_siglent_read.py
python3 -m unittest -v test_siglent_read
```

## Log live Siglent scalars

[siglent_log.py](siglent_log.py) reuses the reader and rail logger directly.
It reads CH1 MIN/MEAN/RMS and requires a separately measured `--idle` voltage,
plus operator-reported test metadata. Defaults are `192.168.1.170:5025`; override
with `--host`/`--port`. Initialize the CSV using `rail_droop_log.py init` first.
Both modes validate the existing CSV and proposed row. Existing rows are preserved.

Dry-run example (queries the scope, prints the proposed row, does not write CSV):

```bash
python3 siglent_log.py --offset 200 --repeat 8 --idle 3.20 --oracle PASS --capture false --dry-run --json
```

Real logging example (replace the illustrative metadata with actual observations):

```bash
python3 siglent_log.py --offset 200 --repeat 8 --idle 3.20 --output-mode enable_only --hp-state false --lp-state-after-test false --oracle PASS --capture false --notes "Siglent CH1 scalar readings"
```

Metadata flags do not configure equipment. The helper only issues the reader's
three measurement queries; it does not control ChipWhisperer, change acquisition
settings, or fire a glitch. Each invocation reads fresh values, so a later real
log need not match a dry-run preview. Sequential queries may span acquisitions.

Output distinguishes **Siglent droop = (MEAN - MIN) × 1000 mV** from the stored
**rail logger droop = (IDLE - MIN) × 1000 mV**. JSON contains `row` (the logger
fields, with exact decimal strings), `siglent_droop_mv`, `dry_run`, and `csv_path`.
Notes are preserved as entered; unspecified output/HP/LP states remain `unknown`.
Live scalar readings do not establish a resolved transient waveform or successful
fault injection. No existing experiment data is filled in automatically.

Offline checks (mocked equipment and temporary CSV fixtures):

```bash
python3 -m py_compile siglent_read.py siglent_log.py rail_droop_log.py test_siglent_read.py test_siglent_log.py
python3 -m unittest -v test_siglent_read test_siglent_log
```

## Offline bench evidence index

[evidence_index.py](evidence_index.py) maintains
[experiments/evidence_index.csv](experiments/evidence_index.csv) without importing
instrument code or contacting equipment. The initial index is header-only: no
run or missing artifact has been invented. `init` preserves an existing index;
`add`, `validate`, `summary`, and `hash` operate only on local files.

Preview an association using the reported scalar values (confirm these belong
to the same run before recording it; the example itself is not new evidence):

```bash
python3 evidence_index.py init
python3 evidence_index.py add --run-id scalar-check-20260930-01 --experiment "STM32 CH1 rail scalars" --ext-offset 200 --repeat 8 --oracle-result PASS --capture-return false --siglent-min-v 3.12 --siglent-mean-v 3.19 --siglent-rms-v 3.19 --rail-droop-mv 80.00 --measurement-file experiments/rail_droop_results.csv --notes-file experiments/2026-09-30-rail-droop-characterization.md --notes "Confirm association with measurement timestamp 2026-09-30T04:36:50+00:00; waveform evidence not supplied" --dry-run
```

After checking the association and notes, omit `--dry-run` to append. Supply
`--timestamp` with a known ISO 8601 time including timezone if available;
otherwise the timestamp records indexing time, not acquisition time. Identify
the source CSV row by timestamp/row number in `--notes`; `--measurement-file`
links the source file but does not infer a row match or import its measurements.

Optional `--saleae-file`, `--husky-trace-file`, `--siglent-image-file`, and
`--notes-file` paths must name existing files within the repository. Paths are
stored relative to the repository root, independent of the working directory.
Blank fields mean not supplied, not zero or PASS. No placeholder artifact paths
are created. Measurements must be finite and offset/repeat nonnegative integers.
The index records the supplied **IDLE - MIN rail droop**; it does not substitute
the Siglent reader's **MEAN - MIN** value or infer an idle voltage. These scalar
observations do not prove a resolved transient waveform or successful fault injection.

For an actually added run:

```bash
python3 evidence_index.py hash --run-id scalar-check-20260930-01
python3 evidence_index.py validate
python3 evidence_index.py summary
```

`hash` writes/updates `experiments/evidence_manifests/<run_id>.sha256.json` and
the index's `sha256_manifest` link. It hashes supplied evidence files, including
the entire measurement file when linked, without modifying them. `validate`
checks recorded manifests against current content. Appending to a linked CSV
will therefore make its old file hash stale. Review changes before explicitly
running `hash` again; refreshing replaces the old manifest. Preserve checkpoint
versions in Git if historical hashes matter. Hashes establish file integrity,
not measurement provenance or physical validity. Do not edit evidence while
hashing or run concurrent index writers. A failed index update after a manifest
write can be retried with the same `hash` command.

Offline tests use only synthetic files in temporary repositories:

```bash
python3 -m py_compile evidence_index.py test_evidence_index.py
python3 -m unittest -v test_evidence_index
```

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
