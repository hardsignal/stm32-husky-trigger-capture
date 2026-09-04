.syntax unified
.cpu cortex-m4
.thumb

.global _start
.global Reset_Handler

.section .isr_vector,"a",%progbits
.type g_pfnVectors, %object
g_pfnVectors:
    .word _estack
    .word Reset_Handler

.section .text.Reset_Handler
.type Reset_Handler, %function
Reset_Handler:
    bl main
1:
    b 1b
