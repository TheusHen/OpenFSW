#include "bsp.h"

/* Minimal STM32F4 register-level BSP (no HAL).
 * Adjust addresses/clock assumptions for your exact STM32F4 part.
 */

#define PERIPH_BASE        0x40000000u
#define AHB1PERIPH_BASE    (PERIPH_BASE + 0x00020000u)
#define RCC_BASE           (AHB1PERIPH_BASE + 0x3800u)
#define IWDG_BASE          (PERIPH_BASE + 0x3000u)

typedef struct {
    volatile uint32_t CR;
    volatile uint32_t PLLCFGR;
    volatile uint32_t CFGR;
    volatile uint32_t CIR;
    volatile uint32_t AHB1RSTR;
    volatile uint32_t AHB2RSTR;
    volatile uint32_t AHB3RSTR;
    uint32_t RESERVED0;
    volatile uint32_t APB1RSTR;
    volatile uint32_t APB2RSTR;
    uint32_t RESERVED1[2];
    volatile uint32_t AHB1ENR;
    volatile uint32_t AHB2ENR;
    volatile uint32_t AHB3ENR;
    uint32_t RESERVED2;
    volatile uint32_t APB1ENR;
    volatile uint32_t APB2ENR;
    uint32_t RESERVED3[2];
    volatile uint32_t AHB1LPENR;
    volatile uint32_t AHB2LPENR;
    volatile uint32_t AHB3LPENR;
    uint32_t RESERVED4;
    volatile uint32_t APB1LPENR;
    volatile uint32_t APB2LPENR;
    uint32_t RESERVED5[2];
    volatile uint32_t BDCR;
    volatile uint32_t CSR;
    uint32_t RESERVED6[2];
    volatile uint32_t SSCGR;
    volatile uint32_t PLLI2SCFGR;
    volatile uint32_t PLLSAICFGR;
    volatile uint32_t DCKCFGR;
} rcc_t;

typedef struct {
    volatile uint32_t KR;
    volatile uint32_t PR;
    volatile uint32_t RLR;
    volatile uint32_t SR;
} iwdg_t;

#define RCC   ((rcc_t *)RCC_BASE)
#define IWDG  ((iwdg_t *)IWDG_BASE)

#define SCB_AIRCR          (*((volatile uint32_t *)0xE000ED0Cu))
#define SCB_AIRCR_VECTKEY  (0x5FAu << 16)
#define SCB_AIRCR_SYSRESETREQ (1u << 2)

/* RCC->CSR bits */
#define RCC_CSR_LSION_Pos      0u
#define RCC_CSR_LSION          (1u << RCC_CSR_LSION_Pos)
#define RCC_CSR_LSIRDY_Pos     1u
#define RCC_CSR_LSIRDY         (1u << RCC_CSR_LSIRDY_Pos)
#define RCC_CSR_RMVF_Pos       24u
#define RCC_CSR_RMVF           (1u << RCC_CSR_RMVF_Pos)
#define RCC_CSR_BORRSTF        (1u << 25u)
#define RCC_CSR_PINRSTF        (1u << 26u)
#define RCC_CSR_PORRSTF        (1u << 27u)
#define RCC_CSR_SFTRSTF        (1u << 28u)
#define RCC_CSR_IWDGRSTF       (1u << 29u)
#define RCC_CSR_WWDGRSTF       (1u << 30u)
#define RCC_CSR_LPWRRSTF       (1u << 31u)

static void busy_wait(volatile uint32_t loops)
{
    while (loops--) {
        __asm volatile("nop");
    }
}

void bsp_clock_basic_init(void)
{
    /* Minimal: keep default clock (HSI) but ensure LSI is on for IWDG. */
    RCC->CSR |= RCC_CSR_LSION;
    while ((RCC->CSR & RCC_CSR_LSIRDY) == 0u) {
        /* wait */
    }
}

uint32_t bsp_clock_get_sysclk(void)
{
    /* Minimal BSP keeps default HSI. */
    return 16000000u;
}

uint32_t bsp_clock_get_hclk(void)
{
    return bsp_clock_get_sysclk();
}

void bsp_watchdog_init(void)
{
    /* Start Independent Watchdog.
     * Prescaler/reload chosen for a coarse ~1s timeout (depends on LSI).
     */

    /* Enable write access */
    IWDG->KR = 0x5555u;

    /* Prescaler: 64 */
    IWDG->PR = 0x04u;

    /* Reload value */
    IWDG->RLR = 1000u;

    /* Wait for registers update */
    while ((IWDG->SR & 0x07u) != 0u) {
        /* wait */
    }

    /* Reload counter */
    IWDG->KR = 0xAAAAu;

    /* Start watchdog */
    IWDG->KR = 0xCCCCu;

    busy_wait(1000u);
}

void bsp_watchdog_kick(void)
{
    IWDG->KR = 0xAAAAu;
}

void bsp_watchdog_set_timeout(uint32_t ms)
{
    (void)ms;
    /* TODO: Convert ms to prescaler/reload based on measured LSI.
     * Keep a fixed configuration for now.
     */
}

reset_cause_t bsp_reset_get_cause(void)
{
    const uint32_t csr = RCC->CSR;
    reset_cause_t cause = RESET_CAUSE_UNKNOWN;

    /* Priority is somewhat subjective; choose the most specific first. */
    if ((csr & RCC_CSR_BORRSTF) != 0u) {
        cause = RESET_CAUSE_BROWN_OUT;
    } else if ((csr & RCC_CSR_PORRSTF) != 0u) {
        cause = RESET_CAUSE_POWER_ON;
    } else if ((csr & RCC_CSR_PINRSTF) != 0u) {
        cause = RESET_CAUSE_PIN;
    } else if (((csr & RCC_CSR_IWDGRSTF) != 0u) || ((csr & RCC_CSR_WWDGRSTF) != 0u)) {
        cause = RESET_CAUSE_WATCHDOG;
    } else if ((csr & RCC_CSR_SFTRSTF) != 0u) {
        cause = RESET_CAUSE_SOFTWARE;
    } else if ((csr & RCC_CSR_LPWRRSTF) != 0u) {
        cause = RESET_CAUSE_LOW_POWER;
    }

    /* Clear reset flags */
    RCC->CSR |= RCC_CSR_RMVF;

    return cause;
}

void bsp_reset_software(void)
{
    /* Request a system reset via AIRCR. */
    SCB_AIRCR = SCB_AIRCR_VECTKEY | SCB_AIRCR_SYSRESETREQ;
    for (;;) {
        __asm volatile("nop");
    }
}

void bsp_reset_subsystem(subsystem_id_t subsys)
{
    (void)subsys;
    /* TODO: Board-specific peripheral reset (RCC resets).
     * Keep stub to avoid hardcoding peripherals.
     */
}

bool bsp_safe_mode_pin_asserted(void)
{
    /* Board-specific: implement via GPIO strap.
     * Keeping default false here to avoid hardcoding a random pin.
     */
    return false;
}

void bsp_power_enter_low_power(void)
{
    /* TODO: Enter STOP/STANDBY depending on mission policy. */
}

void bsp_power_enable_rail(uint8_t rail)
{
    (void)rail;
    /* TODO: implement load-switch control via GPIO. */
}

void bsp_power_disable_rail(uint8_t rail)
{
    (void)rail;
}

void bsp_debug_putchar(char c)
{
    (void)c;
    /* TODO: Wire to SWO/ITM or UART.
     * Keeping silent in the bare-metal ELF build.
     */
}

void bsp_debug_puts(const char *str)
{
    if (!str) return;
    while (*str) {
        bsp_debug_putchar(*str++);
    }
}
