/**
 * @file boot.c
 * @brief Boot sequence implementation
 * 
 * Responsibilities:
 * - Memory initialization (.data, .bss)
 * - Clock configuration
 * - Watchdog initialization
 * - Reset cause detection
 * - Boot counter management
 * - Safe boot threshold checking
 * - Mode selection
 * - RTOS handoff
 */

#include "boot.h"
#include "../drivers/bsp.h"
#include "../rtos/rtos.h"

/*===========================================================================*/
/* Linker Symbols                                                            */
/*===========================================================================*/
extern uint32_t __data_load__;
extern uint32_t __data_start__;
extern uint32_t __data_end__;
extern uint32_t __bss_start__;
extern uint32_t __bss_end__;

/*===========================================================================*/
/* Persistent Boot Data                                                      */
/*===========================================================================*/
static boot_persistent_t g_boot_data __attribute__((section(".noinit")));

/*===========================================================================*/
/* Static Functions                                                          */
/*===========================================================================*/

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

static uint32_t boot_compute_checksum(const boot_persistent_t *data)
{
    const uint8_t *ptr = (const uint8_t *)data;
    uint32_t sum = 0;
    for (size_t i = 0; i < offsetof(boot_persistent_t, checksum); i++) {
        sum += ptr[i];
    }
    return sum ^ 0xDEADBEEF;
}

static bool boot_validate_persistent(void)
{
    if (g_boot_data.magic != BOOT_COUNTER_MAGIC) {
        return false;
    }
    return (g_boot_data.checksum == boot_compute_checksum(&g_boot_data));
}

static void boot_init_persistent(void)
{
    g_boot_data.magic = BOOT_COUNTER_MAGIC;
    g_boot_data.boot_count = 0;
    g_boot_data.reset_count_watchdog = 0;
    g_boot_data.reset_count_brownout = 0;
    g_boot_data.reset_count_software = 0;
    g_boot_data.last_reset_cause = RESET_CAUSE_UNKNOWN;
    g_boot_data.requested_mode = MODE_BOOT;
    g_boot_data.checksum = boot_compute_checksum(&g_boot_data);
}

static void boot_update_persistent(void)
{
    g_boot_data.checksum = boot_compute_checksum(&g_boot_data);
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void boot_platform_init(void)
{
    bsp_clock_basic_init();
    bsp_watchdog_init();
}

reset_cause_t boot_get_reset_cause(void)
{
    return g_boot_data.last_reset_cause;
}

uint32_t boot_get_count(void)
{
    return g_boot_data.boot_count;
}

bool boot_is_safe_required(void)
{
    if (g_boot_data.reset_count_watchdog >= BOOT_SAFE_THRESHOLD) {
        return true;
    }
    if (g_boot_data.last_reset_cause == RESET_CAUSE_BROWN_OUT) {
        return true;
    }
    return false;
}

void boot_increment_counter(void)
{
    g_boot_data.boot_count++;
    boot_update_persistent();
}

void boot_clear_counters(void)
{
    g_boot_data.reset_count_watchdog = 0;
    g_boot_data.reset_count_brownout = 0;
    boot_update_persistent();
}

system_mode_t boot_select_mode(reset_cause_t cause)
{
    if (bsp_safe_mode_pin_asserted()) {
        return MODE_SAFE;
    }
    
    if (boot_is_safe_required()) {
        return MODE_SAFE;
    }
    
    switch (cause) {
        case RESET_CAUSE_WATCHDOG:
            g_boot_data.reset_count_watchdog++;
            if (g_boot_data.reset_count_watchdog >= BOOT_SAFE_THRESHOLD) {
                return MODE_SAFE;
            }
            return MODE_RECOVERY;
            
        case RESET_CAUSE_BROWN_OUT:
            g_boot_data.reset_count_brownout++;
            return MODE_LOW_POWER;
            
        case RESET_CAUSE_POWER_ON:
            return MODE_DETUMBLE;
            
        case RESET_CAUSE_SOFTWARE:
            if (g_boot_data.requested_mode != MODE_BOOT) {
                return g_boot_data.requested_mode;
            }
            return MODE_NOMINAL;
            
        default:
            return MODE_SAFE;
    }
}

void boot_main(void)
{
    boot_copy_data();
    boot_zero_bss();
    
    if (!boot_validate_persistent()) {
        boot_init_persistent();
    }
    
    boot_platform_init();
    
    reset_cause_t cause = bsp_reset_get_cause();
    g_boot_data.last_reset_cause = cause;
    
    boot_increment_counter();
    
    system_mode_t mode = boot_select_mode(cause);
    
    boot_update_persistent();
    
    rtos_start(mode);
    
    while (1) {
        bsp_watchdog_kick();
    }
}
