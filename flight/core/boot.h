#pragma once

#include <stdint.h>
#include <stdbool.h>

typedef enum {
    OPENFSW_RESET_UNKNOWN = 0,
    OPENFSW_RESET_POWER_ON,
    OPENFSW_RESET_PIN,
    OPENFSW_RESET_WATCHDOG,
    OPENFSW_RESET_SOFTWARE,
    OPENFSW_RESET_BROWN_OUT,
} openfsw_reset_cause_t;

typedef enum {
    OPENFSW_BOOT_MODE_NOMINAL = 0,
    OPENFSW_BOOT_MODE_SAFE,
} openfsw_boot_mode_t;

void boot_main(void);

/* Called after .data/.bss are initialized. */
void boot_platform_init(void);

/* Decide safe vs nominal mode (reset cause, pins, etc). */
openfsw_boot_mode_t boot_select_mode(openfsw_reset_cause_t cause);
