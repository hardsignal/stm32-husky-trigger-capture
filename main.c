#include <stdint.h>

#define RCC_AHB1ENR (*(volatile uint32_t *)0x40023830)

#define GPIOA_MODER (*(volatile uint32_t *)0x40020000)
#define GPIOA_ODR   (*(volatile uint32_t *)0x40020014)

static void delay(volatile uint32_t n)
{
    while (n--) {
        __asm volatile ("nop");
    }
}

static volatile uint32_t result;

int main(void)
{
    /* Enable GPIOA */
    RCC_AHB1ENR |= (1U << 0);

    /* PA0 and PA5 as outputs */
    GPIOA_MODER &= ~((3U << 0) | (3U << 10));
    GPIOA_MODER |=  ((1U << 0) | (1U << 10));

    while (1)
    {
        /* Trigger HIGH */
        GPIOA_ODR |= (1U << 0);

        /* Workload marker HIGH */
        GPIOA_ODR |= (1U << 5);

        /* Known repeatable workload */
        result = 0;

        for (volatile uint32_t i = 0; i < 100000; i++)
        {
            result += i;
            result ^= 0x12345678;
            result = (result << 1) | (result >> 31);
        }

        /* Workload marker LOW */
        GPIOA_ODR &= ~(1U << 5);

        /* Trigger LOW */
        GPIOA_ODR &= ~(1U << 0);

        delay(500000);
    }
}
