/**
 * @file mode_manager.h
 * @brief System Mode Manager
 * 
 * Handles mode transitions, timeouts, and mode-specific behavior.
 */

#ifndef MODE_MANAGER_H
#define MODE_MANAGER_H

#include "../openfsw.h"

/*===========================================================================*/
/* Mode Configuration                                                        */
/*===========================================================================*/
#define MODE_DETUMBLE_TIMEOUT_S     1800    /* 30 minutes max */
#define MODE_RECOVERY_TIMEOUT_S     3600    /* 1 hour max */
#define MODE_LOW_POWER_MIN_SOC      20      /* Minimum battery SOC % */

/*===========================================================================*/
/* Mode Transition Rules                                                     */
/*===========================================================================*/
typedef struct {
    system_mode_t from;
    system_mode_t to;
    bool allowed;
    const char *condition;
} mode_transition_t;

/*===========================================================================*/
/* Mode State                                                                */
/*===========================================================================*/
typedef struct {
    system_mode_t current;
    system_mode_t previous;
    system_mode_t requested;
    uint32_t entry_time_s;
    uint32_t timeout_s;
    bool transition_pending;
    bool forced_override;
} mode_state_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

/**
 * @brief Initialize mode manager with starting mode
 */
void mode_manager_init(system_mode_t initial);

/**
 * @brief Get current system mode
 */
system_mode_t mode_manager_get_current(void);

/**
 * @brief Get previous system mode
 */
system_mode_t mode_manager_get_previous(void);

/**
 * @brief Request mode transition
 * @return OPENFSW_OK if transition allowed and scheduled
 */
openfsw_status_t mode_manager_request(system_mode_t mode);

/**
 * @brief Force mode transition (bypass rules)
 */
void mode_manager_force(system_mode_t mode);

/**
 * @brief Execute pending transition
 */
void mode_manager_process(void);

/**
 * @brief Check if transition is allowed
 */
bool mode_manager_can_transition(system_mode_t from, system_mode_t to);

/**
 * @brief Get time in current mode (seconds)
 */
uint32_t mode_manager_time_in_mode(void);

/**
 * @brief Mode timeout check
 */
bool mode_manager_is_timeout(void);

/**
 * @brief Get mode name string
 */
const char* mode_manager_get_name(system_mode_t mode);

/**
 * @brief Register mode entry callback
 */
typedef void (*mode_entry_fn_t)(system_mode_t mode);
void mode_manager_set_entry_callback(mode_entry_fn_t fn);

/**
 * @brief Register mode exit callback
 */
typedef void (*mode_exit_fn_t)(system_mode_t mode);
void mode_manager_set_exit_callback(mode_exit_fn_t fn);

/* Compatibility aliases used by older comms/handlers. */
static inline system_mode_t mode_get_current(void)
{
    return mode_manager_get_current();
}

static inline openfsw_status_t mode_request_transition(system_mode_t mode)
{
    return mode_manager_request(mode);
}

#endif /* MODE_MANAGER_H */
