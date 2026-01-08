#pragma once

#include <stdbool.h>
#include <stdint.h>
#include "openfsw/boot.h"

/* Board Support Package hooks.
 * Keep Boot independent of vendor drivers: BSP is the only hardware-facing layer.
 */

void bsp_clock_basic_init(void);

/* Watchdog: avoid skipping it, but keep implementation BSP-specific. */
void bsp_watchdog_init(void);
void bsp_watchdog_kick(void);

openfsw_reset_cause_t bsp_reset_get_cause(void);

/* Optional safe-mode pin (e.g., jumper, deployment inhibit, etc). */
bool bsp_safe_mode_pin_asserted(void);
