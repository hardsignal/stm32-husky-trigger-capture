# STM32 Husky Trigger Capture

A minimal hardware-security lab project using:

- STM32 NUCLEO-F446RE
- ChipWhisperer Husky
- Saleae Logic 8

## Goal

Create a repeatable STM32 workload, generate a clean trigger on PA0, verify timing with Saleae, and capture a synchronized acquisition window with ChipWhisperer Husky.

## Current wiring

### NUCLEO → Husky

- PA0 / A0 → Husky TIO4
- GND → Husky GND

### NUCLEO → Saleae

- PA0 / A0 → Saleae D4
- PA5 / D13 → Saleae D0
- GND → Saleae GND

The NUCLEO is powered from its own USB connection.

Husky target power is not used. At this stage Husky is being used for trigger synchronization and ADC acquisition only; its analog power-measurement path is not yet connected to the STM32.

## Firmware

`main.c` drives:

- PA0 HIGH as the capture trigger
- PA5 HIGH as a workload marker
- a short repeatable arithmetic workload
- PA5 LOW
- PA0 LOW

The workload was reduced to 5 loop iterations so the active region fits inside the Husky capture window.

## Build

The project is built with the ARM GNU toolchain.

Build command:

    arm-none-eabi-gcc       -mcpu=cortex-m4 -mthumb       -ffreestanding -nostdlib       -T linker.ld       startup.s main.c       -o trigger.elf

## Flash

The firmware is flashed through the NUCLEO onboard ST-LINK using OpenOCD.

Flash command:

    openocd       -f interface/stlink.cfg       -f target/stm32f4x.cfg       -c "program trigger.elf verify reset exit"

## Husky capture settings

- ADC samples: 1000
- ADC clock: 40 MHz
- Capture window: 25 µs
- Trigger source: TIO4

The 25 µs window was deliberately chosen to sit just above the measured workload duration of ~18–19 µs, leaving several microseconds of timing margin while keeping the acquisition compact.

## Verified results

- Saleae confirms PA0 and PA5 timing
- Short workload duration is ~18–19 µs
- Husky captures 1000 samples successfully
- 10 repeated acquisitions complete consistently
- Trigger and acquisition timing are repeatable

## Next step

Connect the Husky analog measurement input to the STM32 power-measurement path and capture the real power signature of the workload.

The current ADC traces validate synchronized acquisition only; they are not yet meaningful STM32 power traces.
