# Minimal fault oracle — 28 September 2026

Firmware: [`main_fault_oracle.c`](../main_fault_oracle.c). Separate variant;
the preserved workloads, `main.c`, startup, linker, and capture data are unchanged.
No UART, HAL, interrupts, external clock configuration, or watchdog is added.

## Pins and acquisition

- PA0 / A0 remains connected to Husky TIO4 and Saleae D4.
- PA5 / D13 remains the workload marker, connected to Saleae D0.
- **PA1 / A1 (CN8 pin 2)** is the new oracle, unused by the documented setup.
  Connect it to a free Saleae input, e.g. D1, with the existing common ground.
  This mapping is from [ST UM1724, Table 19](https://www.st.com/resource/en/user_manual/dm00105823.pdf).
  Verify it is physically free on the actual bench. Use a high-impedance input;
  the firmware drives it push-pull at MCU I/O voltage.

The existing Husky basic rising-edge TIO4 trigger, TIO4 input mode, and analog
measurement path remain applicable. The oracle is observed separately on the
logic analyzer; the current capture script does not read or classify it.
No Husky settings or hardware connections were changed during implementation.
An external ~10 kOhm PA1-to-GND pull-down gives a defined LOW while the MCU pin
is high impedance during reset; the firmware's internal pull is disabled.

## Workload and timing

Each iteration sets a volatile 32-bit unsigned result to zero, then for
`i = 0..49` adds `i`, XORs `0x12345678`, and rotates left by one bit. Arithmetic
wraps modulo 2^32. Expected final result: **`0x8FAEE67B` (2410604155)**.
Both the result and loop counter are explicitly initialized; this does not
depend on the existing minimal startup clearing `.bss` or copying `.data`.

Sequence:

1. At boot, configure all three outputs LOW and call `delay(500000)`.
2. Clear PA1 to invalidate the old verdict, then raise PA0 and PA5.
3. Run the arithmetic with PA0 and PA5 HIGH.
4. Lower PA5; compare the result and write PA1 HIGH on equality, LOW otherwise.
5. Lower PA0, then hold the verdict during `delay(500000)` before repeating.

**Sample PA1 just after PA0 falls**, allowing analyzer timing resolution for the
edge, and before the next iteration. LOW during boot or computation is invalid,
not a fault verdict. PA5 marks only the workload; PA0 also encloses the check.
For arithmetic glitches, target the PA5-HIGH portion using PA0's rising edge
as the reference. GPIO writes use BSRR to avoid output-register read/modify/write.

The clock remains at its reset configuration (nominal 16 MHz HSI after a normal
reset). Delays are loop counts, not microseconds. Measure the new PA0/PA5 widths
and repetition period without glitches before choosing offsets or timeouts;
this variant is not timing-matched to the preserved captures. At 40 MS/s,
8000 samples span 200 us: verify the verdict edge fits the actual capture,
and use a longer logic-analyzer recording to observe repetition and resets.

## Classifying future trials

Record PA0, PA5, PA1 and, preferably, NRST on another analyzer input. Establish
normal pulse widths and a timeout longer than several normal iteration periods.
Observe the trial through completion and the next expected iteration.

| Outcome | Evidence |
| --- | --- |
| Correct completion | Normal PA0/PA5 pulse sequence, PA1 HIGH after PA0 falls, continued iterations, no reset evidence. |
| Detected computation fault | Completed pulse sequence, PA1 LOW in the verdict interval, continued iterations, no reset evidence. |
| Reset | NRST assertion or other independent reset evidence, interrupted sequence, then boot settling interval and restarted iterations. GPIO levels during reset alone are not a verdict. |
| Suspected lockup / hang | No completion or no further iterations within the measured timeout, without observed reset. Pins may remain HIGH or LOW; an old HIGH verdict does not prove liveness. Confirm target state with the debugger after recording. |

A single oracle bit cannot unambiguously classify reset versus hang. If reset
was not independently observed, label ambiguous traces **reset/hang/unknown**,
not arithmetic faults. NRST monitoring may not reveal every abnormal execution
path; debugger inspection of reset flags can provide additional evidence.
The existing startup has only stack/reset vector entries, with no valid fault
handlers: CPU exceptions can lead to lockup instead of a LOW completed verdict.
No startup change is needed for normal operation, but exceptions are not decoded.
The comparison, control flow, and GPIO writes can themselves be glitched; HIGH
means the firmware reported equality, not proof of fault-free execution. A
later clean iteration overwrites a fault verdict, so do not rely on a late poll.

## Build and validation

From the repository directory, build without replacing `trigger.elf`:

```bash
arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -O0 -g \
  -ffreestanding -nostdlib -Wall -Wextra -Werror \
  -T linker.ld startup.s main_fault_oracle.c -o /tmp/fault_oracle.elf
arm-none-eabi-objdump -d /tmp/fault_oracle.elf
```

Use this exact optimization level for initial timing baselines. Validation
checks the build, the retained arithmetic loop and verdict branches in the
disassembly, and an independent modulo-2^32 reference calculation. Hardware
flashing, electrical verification, clean captures, and glitch trials remain
future bench work; no hardware compatibility test is claimed here. Follow the
existing [FI-0 recovery note](2026-09-28-fi-0-recovery-baseline.md) for the
measurement setup's power order.
