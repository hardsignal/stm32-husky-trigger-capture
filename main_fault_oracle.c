#include <stdint.h>

#define RCC_AHB1ENR  (*(volatile uint32_t *)0x40023830)
#define GPIOA_MODER  (*(volatile uint32_t *)0x40020000)
#define GPIOA_OTYPER (*(volatile uint32_t *)0x40020004)
#define GPIOA_OSPEEDR (*(volatile uint32_t *)0x40020008)
#define GPIOA_PUPDR  (*(volatile uint32_t *)0x4002000C)
#define GPIOA_BSRR   (*(volatile uint32_t *)0x40020018)

#define TRIGGER (1U << 0)  /* PA0 / A0 -> Husky TIO4 */
#define ORACLE  (1U << 1)  /* PA1 / A1: HIGH = correct completed result */
#define MARKER  (1U << 5)  /* PA5 / D13: arithmetic region */
#define PIN_MODES ((3U << 0) | (3U << 2) | (3U << 10))
#define EXPECTED_RESULT UINT32_C(0x8FAEE67B)

static void delay(volatile uint32_t n)
{
    while (n--) {
        __asm volatile ("nop");
    }
}

/* Volatile keeps the arithmetic visible; initialized explicitly each round. */
static volatile uint32_t result;

int main(void)
{
    RCC_AHB1ENR |= 1U;
    (void)RCC_AHB1ENR; /* Allow the GPIO peripheral clock to become active. */

    /* Preload LOW before enabling push-pull outputs; leave other pins alone. */
    GPIOA_BSRR = (TRIGGER | ORACLE | MARKER) << 16;
    GPIOA_OTYPER &= ~(TRIGGER | ORACLE | MARKER);
    GPIOA_OSPEEDR &= ~PIN_MODES;
    GPIOA_PUPDR &= ~PIN_MODES;
    GPIOA_MODER = (GPIOA_MODER & ~PIN_MODES)
                | (1U << 0) | (1U << 2) | (1U << 10);

    delay(500000); /* Startup settling interval, with all three outputs LOW. */

    while (1) {
        GPIOA_BSRR = ORACLE << 16; /* Invalidate the previous result. */
        GPIOA_BSRR = TRIGGER;
        GPIOA_BSRR = MARKER;

        result = 0;
        for (volatile uint32_t i = 0; i < 50; i++) {
            result += i;
            result ^= UINT32_C(0x12345678);
            result = (result << 1) | (result >> 31);
        }

        GPIOA_BSRR = MARKER << 16;

        /* Publish the verdict before ending the trigger window. */
        if (result == EXPECTED_RESULT) {
            GPIOA_BSRR = ORACLE;
        } else {
            GPIOA_BSRR = ORACLE << 16;
        }
        GPIOA_BSRR = TRIGGER << 16;

        delay(500000); /* Hold this verdict until the next iteration. */
    }
}
