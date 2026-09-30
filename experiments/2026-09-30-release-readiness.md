# Release-readiness review — 2026-09-30

## Assessment and scope

Suitable for a documented research checkpoint, with the evidence and portability
limits below. No blocking missing local files or obvious exposed credentials were
identified in this review. This assessment does not certify hardware operation,
runtime correctness, or a successful fault-injection result.

Reviewed branch `main` at `7890346` (Add portfolio summary for STM32 Husky project).
Inspection used Git metadata, tracked text, file inventories, and local Markdown
references. No lab scripts were executed or imported, no hardware was accessed,
and no code, settings, or experiment data were modified. Only this review was added.
External URLs, binary metadata, and historical Git objects were not audited.

## Working tree and tracked sources

- **Clean before this review:** `git status --short` returned no changes. This
  newly created review is not included in the inspected commit.
- **82 tracked files** were present before this addition. Important sources are
  tracked: `main_fault_oracle.c`, `main.c`, preserved workload/control variants,
  `startup.s`, `linker.ld`, `husky_oracle_baseline.py`,
  `husky_oracle_glitch_prep.py`, `fi0_recovery_check.py`, and `rail_droop_log.py`.
  Trace-analysis helpers are also tracked.
- README, experiment notes, portfolio, project-status and quality-review documents,
  `experiments/rail_droop_results.csv`, and `experiments/rail_droop_report.md` are
  tracked. The single rail row remains part of the checkpoint's evidence.

## Generated artifacts and reproducibility

- **32 ignored local files** were listed. [.gitignore](../.gitignore) covers Python
  caches, `husky_baseline_*/`, selected trace CSV families, and `trigger.elf`.
  The ignored files include four timestamped Husky baseline directories with
  `results.csv`/`overlay.png`, a Python bytecode file, and the compiled ELF.
- `git ls-files -ci --exclude-standard` returned no entries: no currently tracked
  file also matches the current ignore rules.
- Generated artifacts are not universally excluded: root-level trace/mean CSVs,
  plots such as `ab50_mean_overlay.png`, and the rail Markdown report are tracked.
  These are experiment/analysis artifacts, not an unexplained cache or build dump.
- A tag or fresh checkout will include tracked data and plots but **will not
  include the ignored Husky runs**. Timing claims should retain their existing
  operator-reported qualification; a tag alone does not archive every local
  acquisition record. The differential datasets referenced by the September 17
  note are now tracked despite its explicitly historical untracked-data statement.

## Documentation references

- **README local links resolve:** firmware, acquisition helper, logger, CSV,
  report, differential/oracle/timing notes, status, and rail-characterization note
  all point to existing tracked files.
- **Experiment-note links resolve:** the recovery helper, firmware, FI-0 note,
  project overview, rail CSV/report, and other relative Markdown targets exist.
- **Portfolio/status/review references are valid:** portfolio and status links
  resolve, including the portfolio's `#project-context` heading anchor. The
  quality review's file-and-line citations refer to existing files, but its line
  numbers describe the older `d8e12b5` snapshot, not the current source layout.
- The ST UM1724 external PDF link in the oracle note was not fetched. The
  `/tmp/fault_oracle.elf` example is a build output, not a missing source link.

## Secrets, paths, and machine-specific material

A heuristic scan of tracked text found no matches for common private-key headers,
AWS access-key IDs, GitHub/OpenAI token patterns, or password/secret/token/API-key
keywords. The tracked filename inventory contains no obvious credential file,
editor swap/backup file, Python cache, or compiled ELF. This limited scan does
not establish that all secrets are absent; binary contents and Git history were
outside scope.

Publication/portability observations:

- `husky_oracle_baseline.py:4` embeds `~/cw-env/bin/python` and
  `~/cw_nucleo_trigger/...` in its usage example. These assume a local virtual
  environment and checkout name; they are not portable installation instructions.
- `experiments/2026-09-28-fi-0-recovery-baseline.md:60` uses `Path.home()` with a
  fixed `cw_nucleo_trigger` subdirectory. This is another checkout-layout assumption.
- `experiments/2026-09-28-fi-fault-oracle.md:84–85` uses the absolute temporary
  output `/tmp/fault_oracle.elf`; the quality review mentions it too. The file
  itself is not tracked. No literal `/home/...` or `/Users/...` paths were found
  in tracked text.
- Researcher attribution, dated measurements, and bench notes are intentionally
  visible in the documentation; no credentials were identified among them.

## Evidence and documentation currency

The current [README](../README.md) and [portfolio](2026-09-30-portfolio-summary.md)
label bench observations as operator-reported, distinguish analog timing from a
direct PA1 measurement, and state that no successful fault injection has been
demonstrated. The one logged 3.20 V idle / 3.12 V minimum result supports an
80 mV calculated difference and recorded oracle PASS, not causality or a trend.
HP=False / LP=False is a reported state, not a fresh readback. Prior J-Link work
is attributed to project context without claiming a dedicated validation record.

The [quality review](2026-09-30-repo-quality-review.md) is historical: commit
`fd91155` addressed I1–I4, C1, C3, and C5 in documentation and the offline logger.
Source inspection confirms shared validation for add/summary/report and the
documented USBErrorIO cleanup exception; runtime checks were not repeated here.
Remaining duplication observations are not release blockers for this checkpoint.

The existing [rail report](rail_droop_report.md) agrees with the current single
row but lacks the newer generator's explicit “not necessarily an unperturbed
control” sentence. Treat it as a saved report snapshot; it was not regenerated.
The [project status](2026-09-30-project-status.md) likewise contains a historical
Git-state snapshot. Neither document should be read as a live inventory.

## Lightweight tag recommendation

A lightweight tag makes sense as a convenient local research milestone, for
example `checkpoint-2026-09-30`. No tags were listed at review time. Its meaning
should be “documented STM32/Husky characterization checkpoint,” without implying
successful fault injection or validated hardware-control software.

Tag `7890346` only if the intended checkpoint excludes this new review. If the
review should be included, commit it first and use that resulting commit. A
lightweight tag records a commit reference, without an annotated release message
or signature. No tag, commit, or push was performed during this review.
