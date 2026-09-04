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

int main(void)
{
    RCC_AHB1ENR |= (1U << 0);

    GPIOA_MODER &= ~(3U << 0);
    GPIOA_MODER |=  (1U << 0);

    while (1) {
        GPIOA_ODR |=  (1U << 0);
        delay(200000);

        GPIOA_ODR &= ~(1U << 0);
        delay(800000);
    }
}
