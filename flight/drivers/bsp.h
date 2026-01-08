/**
 * @file bsp.h
 * @brief Board Support Package Interface
 */

#ifndef BSP_H
#define BSP_H

#include "../core/openfsw.h"

/*===========================================================================*/
/* Clock                                                                     */
/*===========================================================================*/
void bsp_clock_basic_init(void);
uint32_t bsp_clock_get_sysclk(void);
uint32_t bsp_clock_get_hclk(void);

/*===========================================================================*/
/* Watchdog                                                                  */
/*===========================================================================*/
void bsp_watchdog_init(void);
void bsp_watchdog_kick(void);
void bsp_watchdog_set_timeout(uint32_t ms);

/*===========================================================================*/
/* Reset                                                                     */
/*===========================================================================*/
reset_cause_t bsp_reset_get_cause(void);
void bsp_reset_software(void);
void bsp_reset_subsystem(subsystem_id_t subsys);

/*===========================================================================*/
/* Safe Mode                                                                 */
/*===========================================================================*/
bool bsp_safe_mode_pin_asserted(void);

/*===========================================================================*/
/* Power                                                                     */
/*===========================================================================*/
void bsp_power_enter_low_power(void);
void bsp_power_enable_rail(uint8_t rail);
void bsp_power_disable_rail(uint8_t rail);

/*===========================================================================*/
/* Debug                                                                     */
/*===========================================================================*/
void bsp_debug_putchar(char c);
void bsp_debug_puts(const char *str);

#endif /* BSP_H */
