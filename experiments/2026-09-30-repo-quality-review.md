# Repository quality review — 2026-09-30

Static, repository-only review at `d8e12b5`. Scope: README, the two Husky oracle
helpers, the rail logger, and all existing Markdown experiment notes/report.
Supporting source, CSV text, file inventory, and Git metadata were read only.
No scripts were executed or imported; no hardware, settings, or experiment data
were changed. Only this review file was added. Line references below are relative
to the repository root and refer to the reviewed snapshot. Recommendations are
proposals, not applied changes. External links and runtime behavior were not tested.

## Critical

None identified by static inspection. This is not a hardware-safety certification
or a claim that all runtime failure paths have been verified.

## Important

### I1. Rail note mixes historical implementation status with current results

**Locations:** `experiments/2026-09-30-rail-droop-characterization.md:29–31,60–61`;
`experiments/rail_droop_results.csv:2`; `experiments/rail_droop_report.md:5–23`.
The note says paired measurements were not supplied and no measurements have
been collected, while the CSV/report contain one operator-entered result. The
example also shares the row's numeric values, without establishing its provenance.
Clarify that the earlier statements concern the documentation/implementation
session, and link the subsequent logged result. Do not infer that the row was
fabricated or that the script was executed merely because these files exist.

### I2. Preparation cleanup description omits an explicit failure-path exception

**Locations:** `experiments/2026-09-29-oracle-glitch-prep.md:20–25`;
`husky_oracle_glitch_prep.py:58–62,108–127`.
The note describes disabling the engine and disconnecting without qualifying
the failure path. A `USBErrorIO` from `scope.capture()` instead marks the hardware
state unknown, skips FPGA-register cleanup, and attempts disconnect only.
Document this existing exception and the limits of cleanup guarantees. No change
to the control flow or register writes is proposed in this review.

### I3. Logger add can persist values that its validator rejects

**Locations:** `rail_droop_log.py:73–78,158–169,196–202`.
CLI voltage parsing checks finiteness, but `add_result()` does not enforce
`rail_min_v <= rail_idle_v` before appending. A minimum above idle therefore
produces a negative stored droop and a row that `validate`/`report` reject.
Consider a separate, explicitly approved offline validation change before writes;
this would change accepted input behavior and is not a behavior-preserving cleanup.

### I4. Summary and report have different data-acceptance and droop semantics

**Locations:** `rail_droop_log.py:39–57,73–79,93–94,172–188`.
`summary` requires the exact column order and uses stored droop without validating
the voltage relationship or stored/calculated agreement. `report` permits reordered
and additional columns, validates measurements, and uses recalculated droop.
Consequently, summary can display data that report rejects, and even accepted data
can differ by the allowed 0.01 mV tolerance. Document these distinctions before
considering harmonization; simply replacing summary's reader would change behavior.

## Cosmetic

### C1. Logger usage documentation omits newer commands

**Locations:** `experiments/2026-09-30-rail-droop-characterization.md:33–58`;
`rail_droop_log.py:211–224`; `README.md:56–59`.
The detailed usage section covers init/add/summary but not validate/report, while
the README lists all five. Add concise descriptions or a link to a canonical
command reference in a future documentation patch.

### C2. Repeated snapshots need explicit historical framing

**Locations:** `README.md:34–77`; `experiments/2026-09-30-project-status.md:33–110`;
`experiments/2026-09-30-rail-droop-characterization.md:15–31`;
`experiments/2026-09-17-differential-shunt.md:123`;
`experiments/2026-09-28-fi-fault-oracle.md:88–94`.
Timing, safe state, and rail results are repeated across overview and dated notes.
The differential note's untracked-data statement is explicitly historical; those
datasets are tracked now. The oracle note's future-bench-work wording predates
later operator reports. Preserve dated evidence, add onward links where useful,
and keep current totals in the CSV/report rather than treating every note as live.
The status note's Git snapshot at lines 87–93 is likewise historical, not today's HEAD.

### C3. Markdown helper docstring overstates literal rendering

**Location:** `rail_droop_log.py:85–90`.
The docstring says cell content is not interpreted, but underscores deliberately
remain unescaped: text such as `_note_` can render as emphasis. Newlines become
`<br>`, so rendered notes are not a byte-for-byte text representation either.
Clarify the docstring while preserving the explicitly requested underscore policy.
The source CSV is unchanged by rendering.

### C4. Pure analysis helpers are duplicated; hardware checks are not equivalent

**Locations:** `husky_oracle_baseline.py:144–148,165–188`;
`husky_oracle_glitch_prep.py:68–93`; existing shared imports at preparation lines 14–16.
ADC error-flag parsing, timing-window selection, and adjacent-sample landmark
calculation could be shared as pure functions. Preserve boundary inclusion,
later-sample timestamps, tie selection, warning threshold, and caller-specific
logging/error handling. A pure module could also avoid importing baseline plotting
setup (`husky_oracle_baseline.py:18–20`) just to obtain helpers, but removing that
import side effect needs separate review and is not strictly behavior-neutral.
Do not merge baseline `preflight` (lines 44–51) with preparation `check_safe`
(lines 19–24): the latter additionally requires HS2 readback to be `None`.

### C5. A few terms need more precise definitions

**Locations:** `rail_droop_log.py:130–132,196,204–205`;
`husky_oracle_baseline.py:159–160`; `README.md:43–46`;
`experiments/2026-09-29-oracle-glitch-prep.md:7–12`.
Define `capture_return=false` as a reported API return, distinct from oracle PASS
or a fault classification; the capture helper treats a truthy return as timeout.
Distinguish `ext_offset` metadata from ADC sample offset and avoid implying units
without the clock context. Retain “first logged baseline” for rail comparisons:
it is not necessarily an unperturbed control. Keep the automated analog timing
landmark distinct from a directly observed PA1 edge; the algorithm does not read PA1.

## No issue

### N1. Current evidence claims and pin terminology are appropriately qualified

**Locations:** `README.md:26–46,63–77`;
`experiments/2026-09-30-project-status.md:18–31,97–110`;
`experiments/2026-09-28-fi-fault-oracle.md:34–42,66–75`.
PA0/A0 trigger, PA5/D13 workload marker, and PA1/A1 oracle roles agree. HP/LP
safe state is labeled operator-reported, HS2 validation is timing-only, and no
successful fault is claimed. USB error-handling code is not presented as proof
of observed intermittent disconnects. Earlier normalized ADC/shunt statistics
are distinguished from rail-voltage measurements in the differential note, lines 20–24.

### N2. Reviewed local links and named source/data files exist

**Locations:** README's links at lines 20,24,32,37,46,50,56,58,84–85;
project-status links in sections “Current objective” through “Known issues and
safe state”; oracle-note links at lines 3,93; recovery-note link at line 46;
differential-note dataset references at lines 32–33,50,60–62,87–104.
No missing local targets were found in these references. The ST PDF URL in the
oracle note, line 13, was not fetched; generated `/tmp/fault_oracle.elf` is an
example build output, not a missing repository source file.

### N3. No obvious unused imports or unreachable helpers in the three scripts

**Locations:** `husky_oracle_baseline.py:11–26,252–253`;
`husky_oracle_glitch_prep.py:8–16,131–132`; `rail_droop_log.py:4–10,191–235`.
Manual reference inspection found uses for all imports and command/helper paths.
The existing preparation script already shares setup and cleanup helpers.
This is static inspection, not linting, dependency verification, or execution.

### N4. Offline report and current row agree within the stated evidence limits

**Locations:** `rail_droop_log.py:56–82,93–143`;
`experiments/rail_droop_results.csv:2`; `experiments/rail_droop_report.md:5–28`.
The recorded 3.20 V idle and 3.12 V minimum imply 80 mV; the one-row report
matches, retains PASS and the operator's note, and disclaims trend/causal inference.
The logger imports only standard-library modules and contains no hardware-control
calls. Report generation validates before writing, handles empty/one-row input,
identifies tied largest droops, and appends the lab footer by source inspection.
