# Next improvements review — checkpoint-2026-09-30

## Checkpoint and scope

The tag resolves to `c248f4cb33c568032495747cd5185ca4a26db8aa`, which includes
the release-readiness review. The working tree was clean before this new file.
That earlier review's “no tags” statement describes its inspection time, not the
current tag state. This document is outside the existing checkpoint.

Only this review was created. No scripts were run or imported, no hardware was
accessed, and no existing code, data, documentation, tags, or history was changed.
Recommendations below describe future work, not completed measurements.
**Documentation gap** means missing explanation or provenance; **evidence gap**
means missing supporting observations or artifacts in the checkpoint. Evidence
absent from the repository may exist elsewhere; it must not be invented.

## High value

### 1. Publish a small, traceable evidence set

**Evidence gap.** The [timing note](2026-09-29-oracle-glitch-prep.md) reports the
40 MHz / 8000-sample baseline and ~159 µs landmark, while [.gitignore](../.gitignore)
excludes timestamped Husky baseline runs. The [rail CSV](rail_droop_results.csv)
contains one manually entered 3.20 V idle / 3.12 V minimum result, 80 mV calculated
droop, oracle PASS. Neither is a demonstrated fault or causal rail-effect result.

The highest-value additions would be selected original exports with run IDs,
checksums, acquisition metadata, and captions linking each claim to its source:

- A Saleae capture showing PA0 trigger, PA5 workload marker, and PA1 verdict over
  completed normal iterations, including the verdict interval and continued activity.
- A Husky baseline trace and timing plot with the analysis window, sample rate,
  units, landmark definition, and warnings visible. Label the analog estimator
  separately from any directly observed digital edge.
- A Siglent MCU-side rail waveform export and matching screenshot showing the
  transient and measurement settings. This would add information that a scalar
  minimum alone cannot provide.

If the original evidence is unavailable, label any later recording as a new run;
do not present it as verification of an earlier session. Keep HP/LP state and
timing-only HS2 observations associated with their actual session records.

### 2. Add an as-built measurement diagram and per-run setup record

**Documentation and evidence gaps.** Pin roles are documented in the
[oracle note](2026-09-28-fi-fault-oracle.md), and the
[differential note](2026-09-17-differential-shunt.md) records reported breadboard
connections. There is no tracked as-built wiring diagram or bench photograph
in the checkpoint inventory.

Add a labeled signal/power-path diagram identifying PA0/PA5/PA1, instrument
channels, measurement points, grounds, shunt, and MCU-side rail. An annotated
bench photo should corroborate the actual arrangement rather than substitute
for the diagram. Distinguish historical differential-shunt and current rail
setups; do not silently combine them into one verified configuration.

Record the Siglent model, probe and attenuation, ground arrangement, coupling,
bandwidth limit, vertical/time scales, trigger reference, sample rate/record
length, and measurement window for each rail run. Include instrument accuracy
and repeatability limits where known. The rail note's scale/ground troubleshooting
makes this more useful than another unqualified droop number.

### 3. Supply a portable reproduction guide and data manifest

**Documentation gap.** The oracle note already includes build flags, and the
differential note includes analysis commands and assumptions. What is missing
is a single path from the tagged checkout to identified outputs, with a tested
environment record. No dependency manifest or test suite is tracked at this tag.

Document compiler/Python/library versions, relevant instrument/firmware versions,
firmware source revision and binary hash per run, and the actual clock/gain
metadata where available. Replace assumptions with recorded values only when
evidence supports them. Separate offline reproduction from hardware acquisition
instructions and explain which commands write files. A data manifest should map
each CSV/plot to its run, firmware, units, analysis command, and provenance.
Explicitly list evidence omitted from the tag; do not imply ignored runs ship
with a fresh checkout. Preserve the historical use of normalized ADC units.

### 4. Establish a measurement-quality matrix before stronger conclusions

**Evidence gap.** The rail note reports repeat values 1, 2, 4, and 8, but does not
contain paired results for each. Do not backfill those combinations from the
single CSV row. The following is an eventual recording plan, not a completed
test matrix or an automated glitch sweep:

| Measurement class | Question | Evidence to retain |
| --- | --- | --- |
| Clean digital baseline | Are trigger, workload, and valid verdict intervals repeatable? | Multi-iteration logic export, pulse timing, completion/liveness observations |
| Clean analog baseline | How repeatable is the reported timing landmark? | Raw traces, run settings, landmark distribution, warnings and exclusions |
| Rail baseline and repeat recordings | Is the observed minimum resolved above measurement variability? | Paired idle/minimum readings, transient exports, setup identity, repeat count and spread |
| Independent session repeat | Does the baseline survive a documented setup/session change? | Separate run IDs, setup differences, comparable measurements |
| Recorded anomaly or transport failure, if encountered | Is the result usable, incomplete, or unknown? | Error log, missing fields, completion/reset evidence, explicit uncertainty |

The eventual table should include run/time, firmware identity, setup ID,
instrument settings, reported HP/LP state, existing test metadata, idle/minimum
and calculated droop, oracle observation, capture return, artifact links, and
notes. Distinguish the logger's test `repeat` setting from the number of independent
measurement repetitions. Record unsuccessful acquisitions and exclusions as well
as usable results. The first logged row is not automatically an unperturbed control.

### 5. Define the minimum polished portfolio package

The [README](../README.md) and [portfolio summary](2026-09-30-portfolio-summary.md)
already provide a credible narrative. Before calling the presentation polished,
add the evidence index, as-built diagram, two or three well-captioned original
figures, and portable offline reproduction instructions above. Keep the current
limits prominent: one rail row, no causal attribution, no demonstrated successful
fault injection, and no complete independently supported oracle-validation record.
Improving Siglent transient capture remains the documented next experiment.

## Medium value

### 6. Add offline regression evidence

**Software-validation gap.** Add future tests of CSV validation, rejection before
append, tolerance boundaries, reordered/extra columns, empty/one-row reports,
and note escaping using temporary synthetic fixtures clearly labeled as such.
Check the arithmetic reference result independently of the target firmware.
Record test commands and outcomes only when actually run. These tests should
not import hardware-control modules or operate on experiment CSVs.

### 7. Consolidate navigation and overlapping analysis tools later

**Maintainability opportunity, not proven redundancy.** README, portfolio,
project-status, quality-review, and release-readiness files repeat some context,
but serve different audiences or preserve dated findings. Keep README as the entry
point, link to one current status/evidence index, and retain historical reviews
as snapshots rather than repeatedly updating them to sound current.

`compare_trace_csv.py` and `compare_trace_csv_astra.py` overlap, as do
`analyze_trace_jitter_sol.py` and `analyze_trace_jitter_astra.py`. Their dependencies
and numerical/boundary implementations differ. Document the supported entry
point and compare behavior before considering consolidation. Do not assume
interchangeability from filenames. The hardware-helper duplication noted in the
[quality review](2026-09-30-repo-quality-review.md#c4-pure-analysis-helpers-are-duplicated-hardware-checks-are-not-equivalent)
is a later maintenance topic, not a reason to merge distinct safety checks.

Preserved firmware variants and original CSVs are provenance, not disposable
duplicates. A later data/figures directory layout and manifest could reduce root
clutter while preserving links, hashes, and reproducibility.

### 8. Prepare answers to an experienced reviewer's next questions

- Which firmware binary ran for each dataset, and where is its build identity?
- Where can I inspect the original PA0/PA5/PA1 recording and valid verdict interval?
- What ties the analog landmark to the reported workload end rather than another transition?
- Was 3.12 V a time-localized MCU-side rail transient, and what was the measurement uncertainty?
- How many independent repetitions exist, including failed or excluded recordings?
- What does PASS establish, and what evidence distinguishes completion, reset, and hang?
- Can the published plots be regenerated from the tag without private files or hardware?
- Which statements are operator reports, source-code properties, or independently reproduced analyses?

These questions identify missing evidence or provenance; they do not imply that
the undocumented checks have already failed or succeeded.

## Nice to have

- A compact firmware state/timing diagram explaining invalid versus valid PA1
  intervals. Label it schematic; it must not masquerade as a measured waveform.
- A small gallery comparing existing differential-shunt plots with links to the
  source datasets, units, and the September 17 analysis limitations. Inspect the
  plots before choosing them; filenames alone do not establish their suitability.
- A short glossary for normalized ADC amplitude, rail volts, timing landmark,
  capture return, oracle verdict, and first-row reference.
- Explicit source/data licensing if public reuse is intended; no license file
  is tracked in the checkpoint. A brief software dependency table would also help.
- A concise checkpoint index linking this tag's source, evidence, and known gaps.
  This can be part of existing navigation rather than another overlapping summary.

## Not worth adding

- More promotional summaries, badges, or dashboards before improving the evidence set.
- Statistical trend plots, success rates, or causal claims based on the single
  80 mV row; successful fault-injection claims remain unsupported.
- Fabricated oscilloscope/logic screenshots, reconstructed “raw” measurements,
  or invented per-offset results to fill gaps in the manual sweep record.
- Automatic crowbar sweeps or stronger glitch settings as a portfolio-completeness
  task; neither resolves the documented measurement-quality gap.
- Every cache, compiled binary, or generated run indiscriminately committed to Git.
  Curated evidence with provenance is more useful than an unexplained artifact dump.
- Deleting dated reviews, original traces, or firmware variants merely to make
  the repository smaller, or moving the existing tag to make old claims look current.
