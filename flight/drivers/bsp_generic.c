#include "bsp.h"

/*
 * Generic BSP implementation.
 *
 * This is meant for early bring-up, CI builds, or as a template.
 * For real flight hardware you should provide a board-specific BSP.
 */

void bsp_clock_basic_init(void)
{
    /* No-op by default. */
}

uint32_t bsp_clock_get_sysclk(void)
{
    /* Unknown for generic target; assume a conservative 16 MHz. */
    return 16000000u;
}

uint32_t bsp_clock_get_hclk(void)
{
    return bsp_clock_get_sysclk();
}

void bsp_watchdog_init(void)
{
    /* Generic target has no hardware watchdog.
     * Intentionally do nothing here so you can still run in emulation.
     * For flight: implement a real watchdog in a board BSP.
     */
}

void bsp_watchdog_kick(void)
{
    /* No-op by default. */
}

void bsp_watchdog_set_timeout(uint32_t ms)
{
    (void)ms;
    /* No-op by default. */
}

reset_cause_t bsp_reset_get_cause(void)
{
    return RESET_CAUSE_UNKNOWN;
}

void bsp_reset_software(void)
{
    /* Generic target: no reset mechanism. Trap. */
    for (;;) {
        __asm volatile("wfi");
    }
}

void bsp_reset_subsystem(subsystem_id_t subsys)
{
    (void)subsys;
    /* No-op by default. */
}

bool bsp_safe_mode_pin_asserted(void)
{
    return false;
}

void bsp_power_enter_low_power(void)
{
    /* No-op by default. */
}

void bsp_power_enable_rail(uint8_t rail)
{
    (void)rail;
}

void bsp_power_disable_rail(uint8_t rail)
{
    (void)rail;
}

void bsp_debug_putchar(char c)
{
    (void)c;
    /* No-op by default. */
}

void bsp_debug_puts(const char *str)
{
    if (!str) return;
    while (*str) {
        bsp_debug_putchar(*str++);
    }
}
