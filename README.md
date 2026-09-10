# STM32 + ChipWhisperer Husky Trigger and Power Capture

Hardsignal Labs experiment using an STM32 NUCLEO-F446RE and ChipWhisperer Husky to build and validate a synchronized power-analysis measurement path.

The project progressed from digital trigger validation to real shunt-based analog power capture and controlled A/B experiments.

## Hardware

- STM32 NUCLEO-F446RE
- ChipWhisperer Husky
- Saleae Logic 8
- 10 ohm shunt resistor
- BB830 breadboard
- SMA-to-crocodile measurement lead
- ST-LINK/V2.1 onboard debugger

The NUCLEO is powered from its own USB connection.

Husky target power is not used.

## Digital synchronization

### NUCLEO -> Husky

- PA0 / A0 -> Husky TIO4
- GND -> Husky GND

### NUCLEO -> Saleae

- PA0 / A0 -> Saleae D4
- PA5 / D13 -> Saleae D0
- GND -> Saleae GND

PA0 defines the Husky acquisition trigger.

PA5 marks the firmware region being compared.

## Power measurement

The NUCLEO JP6 / IDD jumper is removed and a 10 ohm shunt is inserted into the MCU supply path.

The Husky MEASURE input observes the voltage developed across the measurement path.

This produces synchronized analog traces of STM32 activity rather than trigger-only captures.

## Firmware

Two principal firmware variants are preserved:

- `main_workload50.c` - 50-iteration arithmetic workload
- `main_control_delay277.c` - timing-matched control workload

The arithmetic workload repeatedly performs addition, XOR and rotation operations.

The control firmware uses a delay selected to approximately match the execution duration of the arithmetic workload.

PA0 surrounds the capture region and PA5 marks the workload/control region.

## Build

```bash
arm-none-eabi-gcc \
-mcpu=cortex-m4 -mthumb \
-ffreestanding -nostdlib \
-T linker.ld \
startup.s main.c \
-o trigger.elf
