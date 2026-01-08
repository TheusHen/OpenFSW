/**
 * @file mode_manager.c
 * @brief System Mode Manager Implementation
 */

#include "mode_manager.h"
#include "../../osal/osal.h"

/*===========================================================================*/
/* Mode Names                                                                */
/*===========================================================================*/
static const char *mode_names[MODE_COUNT] = {
    "BOOT",
    "SAFE",
    "DETUMBLE",
    "NOMINAL",
    "LOW_POWER",
    "RECOVERY"
};

/*===========================================================================*/
/* Transition Rules                                                          */
/*===========================================================================*/
static const mode_transition_t transition_rules[] = {
    /* BOOT -> any except NOMINAL (must pass through DETUMBLE or SAFE) */
    { MODE_BOOT, MODE_SAFE, true, "always" },
    { MODE_BOOT, MODE_DETUMBLE, true, "power_on" },
    { MODE_BOOT, MODE_RECOVERY, true, "watchdog_reset" },
    { MODE_BOOT, MODE_LOW_POWER, true, "brownout" },
    
    /* SAFE -> limited transitions */
    { MODE_SAFE, MODE_DETUMBLE, true, "ground_cmd" },
    { MODE_SAFE, MODE_NOMINAL, true, "ground_cmd" },
    { MODE_SAFE, MODE_LOW_POWER, true, "low_power" },
    
    /* DETUMBLE -> SAFE or NOMINAL */
    { MODE_DETUMBLE, MODE_SAFE, true, "fdir" },
    { MODE_DETUMBLE, MODE_NOMINAL, true, "detumble_complete" },
    { MODE_DETUMBLE, MODE_LOW_POWER, true, "low_power" },
    
    /* NOMINAL -> any */
    { MODE_NOMINAL, MODE_SAFE, true, "fdir" },
    { MODE_NOMINAL, MODE_DETUMBLE, true, "attitude_lost" },
    { MODE_NOMINAL, MODE_LOW_POWER, true, "low_power" },
    { MODE_NOMINAL, MODE_RECOVERY, true, "fdir" },
    
    /* LOW_POWER -> limited */
    { MODE_LOW_POWER, MODE_SAFE, true, "fdir" },
    { MODE_LOW_POWER, MODE_NOMINAL, true, "power_restored" },
    { MODE_LOW_POWER, MODE_DETUMBLE, true, "power_restored" },
    
    /* RECOVERY -> SAFE or NOMINAL */
    { MODE_RECOVERY, MODE_SAFE, true, "recovery_failed" },
    { MODE_RECOVERY, MODE_NOMINAL, true, "recovery_success" },
    { MODE_RECOVERY, MODE_DETUMBLE, true, "attitude_lost" },
};

#define NUM_TRANSITIONS (sizeof(transition_rules) / sizeof(transition_rules[0]))

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static mode_state_t g_mode;
static mode_entry_fn_t g_entry_cb;
static mode_exit_fn_t g_exit_cb;
static osal_mutex_t g_mode_mutex;

/*===========================================================================*/
/* Helper Functions                                                          */
/*===========================================================================*/

static uint32_t get_mode_timeout(system_mode_t mode)
{
    switch (mode) {
        case MODE_DETUMBLE:
            return MODE_DETUMBLE_TIMEOUT_S;
        case MODE_RECOVERY:
            return MODE_RECOVERY_TIMEOUT_S;
        default:
            return 0; /* No timeout */
    }
}

static uint32_t get_system_time_s(void)
{
    return osal_get_time_ms() / 1000;
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void mode_manager_init(system_mode_t initial)
{
    osal_mutex_create(&g_mode_mutex);
    
    g_mode.current = initial;
    g_mode.previous = MODE_BOOT;
    g_mode.requested = initial;
    g_mode.entry_time_s = get_system_time_s();
    g_mode.timeout_s = get_mode_timeout(initial);
    g_mode.transition_pending = false;
    g_mode.forced_override = false;
    
    g_entry_cb = NULL;
    g_exit_cb = NULL;
    
    if (g_entry_cb) {
        g_entry_cb(initial);
    }
}

system_mode_t mode_manager_get_current(void)
{
    return g_mode.current;
}

system_mode_t mode_manager_get_previous(void)
{
    return g_mode.previous;
}

bool mode_manager_can_transition(system_mode_t from, system_mode_t to)
{
    if (from == to) {
        return false;
    }
    
    for (size_t i = 0; i < NUM_TRANSITIONS; i++) {
        if (transition_rules[i].from == from && transition_rules[i].to == to) {
            return transition_rules[i].allowed;
        }
    }
    
    return false;
}

openfsw_status_t mode_manager_request(system_mode_t mode)
{
    if (mode >= MODE_COUNT) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    osal_mutex_lock(g_mode_mutex, OSAL_WAIT_FOREVER);
    
    if (!mode_manager_can_transition(g_mode.current, mode)) {
        osal_mutex_unlock(g_mode_mutex);
        return OPENFSW_ERROR_PERMISSION;
    }
    
    g_mode.requested = mode;
    g_mode.transition_pending = true;
    g_mode.forced_override = false;
    
    osal_mutex_unlock(g_mode_mutex);
    return OPENFSW_OK;
}

void mode_manager_force(system_mode_t mode)
{
    if (mode >= MODE_COUNT) {
        return;
    }
    
    osal_mutex_lock(g_mode_mutex, OSAL_WAIT_FOREVER);
    
    g_mode.requested = mode;
    g_mode.transition_pending = true;
    g_mode.forced_override = true;
    
    osal_mutex_unlock(g_mode_mutex);
}

void mode_manager_process(void)
{
    osal_mutex_lock(g_mode_mutex, OSAL_WAIT_FOREVER);
    
    /* Check for timeout */
    if (g_mode.timeout_s > 0) {
        uint32_t elapsed = get_system_time_s() - g_mode.entry_time_s;
        if (elapsed >= g_mode.timeout_s) {
            /* Timeout: force to SAFE */
            g_mode.requested = MODE_SAFE;
            g_mode.transition_pending = true;
            g_mode.forced_override = true;
        }
    }
    
    /* Process pending transition */
    if (g_mode.transition_pending) {
        /* Call exit callback */
        if (g_exit_cb) {
            g_exit_cb(g_mode.current);
        }
        
        /* Update state */
        g_mode.previous = g_mode.current;
        g_mode.current = g_mode.requested;
        g_mode.entry_time_s = get_system_time_s();
        g_mode.timeout_s = get_mode_timeout(g_mode.current);
        g_mode.transition_pending = false;
        g_mode.forced_override = false;
        
        /* Call entry callback */
        if (g_entry_cb) {
            g_entry_cb(g_mode.current);
        }
    }
    
    osal_mutex_unlock(g_mode_mutex);
}

uint32_t mode_manager_time_in_mode(void)
{
    return get_system_time_s() - g_mode.entry_time_s;
}

bool mode_manager_is_timeout(void)
{
    if (g_mode.timeout_s == 0) {
        return false;
    }
    return mode_manager_time_in_mode() >= g_mode.timeout_s;
}

const char* mode_manager_get_name(system_mode_t mode)
{
    if (mode >= MODE_COUNT) {
        return "UNKNOWN";
    }
    return mode_names[mode];
}

void mode_manager_set_entry_callback(mode_entry_fn_t fn)
{
    g_entry_cb = fn;
}

void mode_manager_set_exit_callback(mode_exit_fn_t fn)
{
    g_exit_cb = fn;
}
