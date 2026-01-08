#include "openfsw/bsp.h"

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

openfsw_reset_cause_t bsp_reset_get_cause(void)
{
    return OPENFSW_RESET_UNKNOWN;
}

bool bsp_safe_mode_pin_asserted(void)
{
    return false;
}
