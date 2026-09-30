# Rail droop report

Source: `experiments/rail_droop_results.csv`.

Number of tests: 1

All values and operator notes below come from the CSV. Droop is calculated as (rail_idle_v - rail_min_v) * 1000. Comparisons are descriptive and do not establish causality. Oracle results are reproduced as entered; no fault-success classification is inferred.

| Test | timestamp | ext_offset | repeat | output_mode | hp_state | lp_state_after_test | rail_idle_v | rail_min_v | rail_mean_v | rail_rms_v | droop_mv | oracle_result | capture_return | notes | Calculated droop (mV) | Droop delta vs test #1 (mV) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-09-30T04:36:50+00:00 | 200 | 8 | enable_only | false | false | 3.20 | 3.12 | 3.20 | 3.20 | 80.00 | PASS | false | Siglent CH1 rail measurement; no oracle anomaly observed | 80.00 | +0.00 |

Minimum calculated droop: 80.00 mV.

Maximum calculated droop: 80.00 mV.

Mean calculated droop: 80.000 mV.

Largest measured droop: 80.00 mV, test(s) #1.

Baseline: first logged test (#1), calculated droop 80.00 mV. Each table delta is the test's calculated droop minus this baseline; a positive delta means a larger measured droop.

Only one row is logged; trend conclusions are not possible yet.

---
Hardsignal Labs  
Independent cyber-physical security research  
Researcher: Maciej Duranczyk
