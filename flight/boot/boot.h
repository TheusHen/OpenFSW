/**
 * @file boot.h
 * @brief Boot subsystem interface
 */

#ifndef BOOT_H
#define BOOT_H

#include "../core/openfsw.h"

/*===========================================================================*/
/* Boot Configuration                                                        */
/*===========================================================================*/
#define BOOT_SAFE_THRESHOLD         3   /* Enter safe mode after N resets */
#define BOOT_COUNTER_MAGIC          0xB007C0DE
#define BOOT_WATCHDOG_TIMEOUT_MS    1000

/*===========================================================================*/
/* Boot Data (persistent in backup RAM or NVM)                               */
/*===========================================================================*/
typedef struct {
    uint32_t magic;
    uint32_t boot_count;
    uint32_t reset_count_watchdog;
    uint32_t reset_count_brownout;
    uint32_t reset_count_software;
    reset_cause_t last_reset_cause;
    system_mode_t requested_mode;
    uint32_t checksum;
} boot_persistent_t;

/*===========================================================================*/
/* Boot API                                                                  */
/*===========================================================================*/

/**
 * @brief Main boot entry point (called from Reset_Handler)
 */
void boot_main(void);

/**
 * @brief Platform-specific early init (clock, watchdog)
 */
void boot_platform_init(void);

/**
 * @brief Get the detected reset cause
 */
reset_cause_t boot_get_reset_cause(void);

/**
 * @brief Get current boot count
 */
uint32_t boot_get_count(void);

/**
 * @brief Determine boot mode based on reset history
 */
system_mode_t boot_select_mode(reset_cause_t cause);

/**
 * @brief Check if safe boot threshold exceeded
 */
bool boot_is_safe_required(void);

/**
 * @brief Increment and persist boot counter
 */
void boot_increment_counter(void);

/**
 * @brief Clear reset counters (called after successful nominal operation)
 */
void boot_clear_counters(void);

#endif /* BOOT_H */
