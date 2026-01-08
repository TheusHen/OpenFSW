#include "openfsw/boot.h"
#include "openfsw/bsp.h"
#include "openfsw/health.h"
#include "openfsw/scheduler.h"
#include "openfsw/rtos.h"
#include "openfsw/system.h"

/* Linker-provided symbols (see linker/linker.ld). */
extern uint32_t __data_load__;
extern uint32_t __data_start__;
extern uint32_t __data_end__;
extern uint32_t __bss_start__;
extern uint32_t __bss_end__;

static void boot_copy_data(void)
{
    const uint32_t *src = &__data_load__;
    uint32_t *dst = &__data_start__;
    while (dst < &__data_end__) {
        *dst++ = *src++;
    }
}

static void boot_zero_bss(void)
{
    uint32_t *dst = &__bss_start__;
    while (dst < &__bss_end__) {
        *dst++ = 0u;
    }
}

void boot_platform_init(void)
{
    /* Basic clock first (so timebases and peripherals are sane). */
    bsp_clock_basic_init();

    /* Watchdog early (but after clock). */
    bsp_watchdog_init();
}

openfsw_boot_mode_t boot_select_mode(openfsw_reset_cause_t cause)
{
    if (bsp_safe_mode_pin_asserted()) {
        return OPENFSW_BOOT_MODE_SAFE;
    }

    /* Conservative policy: watchdog reset implies safe mode. */
    if (cause == OPENFSW_RESET_WATCHDOG) {
        return OPENFSW_BOOT_MODE_SAFE;
    }

    return OPENFSW_BOOT_MODE_NOMINAL;
}

void boot_main(void)
{
    /* Runtime init normally done by CRT0: we do it here explicitly. */
    boot_copy_data();
    boot_zero_bss();

    boot_platform_init();

    const openfsw_reset_cause_t cause = bsp_reset_get_cause();
    const openfsw_boot_mode_t mode = boot_select_mode(cause);

    openfsw_system_set_context(mode, cause);

    /* Boot chain: Boot -> Health -> Scheduler -> RTOS */
    health_init(mode);
    scheduler_init(mode);

    /* Final handoff: must not return. */
    rtos_start(mode);

    /* If RTOS returns, trap. */
    while (1) {
        bsp_watchdog_kick();
    }
}
