/**
 * @file rtos.h
 * @brief RTOS Interface
 */

#ifndef RTOS_H
#define RTOS_H

#include "../core/openfsw.h"

/**
 * @brief Start the RTOS scheduler (must not return)
 */
__attribute__((noreturn)) void rtos_start(system_mode_t initial_mode);

/**
 * @brief Get current system mode
 */
system_mode_t rtos_get_mode(void);

/**
 * @brief Request mode transition
 */
openfsw_status_t rtos_request_mode(system_mode_t mode);

#endif /* RTOS_H */
