/**
 * @file fdir.c
 * @brief Fault Detection, Isolation & Recovery Implementation
 */

#include "fdir.h"
#include "../osal/osal.h"
#include "../core/mode/mode_manager.h"
#include "../core/logging/event_log.h"
#include "../drivers/bsp.h"

/*===========================================================================*/
/* Configuration                                                             */
/*===========================================================================*/
#define FDIR_RESET_LOOP_THRESHOLD   3
#define FDIR_RESET_LOOP_WINDOW_S    60

/*===========================================================================*/
/* Recovery Rules                                                            */
/*===========================================================================*/
static const fdir_rule_t fdir_rules[] = {
    { FAULT_WATCHDOG_TIMEOUT, 1, 0, RECOVERY_SYSTEM_RESET },
    { FAULT_BROWNOUT, 2, 60000, RECOVERY_LOAD_SHED },
    { FAULT_RESET_LOOP, 3, 60000, RECOVERY_SAFE_MODE },
    { FAULT_SENSOR_INVALID, 3, 10000, RECOVERY_ISOLATE },
    { FAULT_ACTUATOR_FAIL, 2, 5000, RECOVERY_ISOLATE },
    { FAULT_BUS_ERROR, 5, 1000, RECOVERY_RESET_SUBSYS },
    { FAULT_MEMORY_ERROR, 1, 0, RECOVERY_SAFE_MODE },
    { FAULT_COMM_LOSS, 10, 60000, RECOVERY_RETRY },
    { FAULT_POWER_CRITICAL, 1, 0, RECOVERY_LOAD_SHED },
    { FAULT_THERMAL_LIMIT, 1, 0, RECOVERY_PAYLOAD_OFF },
    { FAULT_ATTITUDE_LOST, 1, 0, RECOVERY_SAFE_MODE },
};

#define NUM_RULES (sizeof(fdir_rules) / sizeof(fdir_rules[0]))

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    fault_record_t records[FAULT_COUNT];
    uint8_t isolated_subsys[SUBSYS_COUNT];
    osal_mutex_t mutex;
    bool initialized;
} g_fdir;

/*===========================================================================*/
/* Helper Functions                                                          */
/*===========================================================================*/

static const fdir_rule_t* find_rule(fault_type_t fault)
{
    for (size_t i = 0; i < NUM_RULES; i++) {
        if (fdir_rules[i].fault == fault) {
            return &fdir_rules[i];
        }
    }
    return NULL;
}

static void execute_action(recovery_action_t action, subsystem_id_t subsys)
{
    switch (action) {
        case RECOVERY_NONE:
            break;
            
        case RECOVERY_RETRY:
            /* Just log, let subsystem retry */
            break;
            
        case RECOVERY_ISOLATE:
            fdir_isolate_subsystem(subsys);
            break;
            
        case RECOVERY_RESET_SUBSYS:
            bsp_reset_subsystem(subsys);
            break;
            
        case RECOVERY_SAFE_MODE:
            mode_manager_force(MODE_SAFE);
            break;
            
        case RECOVERY_SYSTEM_RESET:
            bsp_reset_software();
            break;
            
        case RECOVERY_PAYLOAD_OFF:
            /* Disable payload power rail */
            bsp_power_disable_rail(4); /* Payload rail */
            break;
            
        case RECOVERY_LOAD_SHED:
            /* Disable non-essential loads */
            bsp_power_disable_rail(3); /* Non-essential */
            bsp_power_disable_rail(4); /* Payload */
            break;
    }
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void fdir_init(void)
{
    osal_mutex_create(&g_fdir.mutex);
    
    for (int i = 0; i < FAULT_COUNT; i++) {
        g_fdir.records[i].type = (fault_type_t)i;
        g_fdir.records[i].subsystem = SUBSYS_CORE;
        g_fdir.records[i].timestamp_ms = 0;
        g_fdir.records[i].occurrence_count = 0;
        g_fdir.records[i].active = false;
        g_fdir.records[i].last_action = RECOVERY_NONE;
    }
    
    for (int i = 0; i < SUBSYS_COUNT; i++) {
        g_fdir.isolated_subsys[i] = 0;
    }
    
    g_fdir.initialized = true;
}

void fdir_periodic(void)
{
    if (!g_fdir.initialized) {
        return;
    }
    
    osal_mutex_lock(g_fdir.mutex, OSAL_WAIT_FOREVER);
    
    /* Check for reset loop */
    if (fdir_detect_reset_loop()) {
        fdir_report_fault(FAULT_RESET_LOOP, SUBSYS_BOOT);
    }
    
    /* Process active faults */
    for (int i = 0; i < FAULT_COUNT; i++) {
        if (g_fdir.records[i].active) {
            const fdir_rule_t *rule = find_rule((fault_type_t)i);
            if (rule && g_fdir.records[i].occurrence_count >= rule->threshold_count) {
                execute_action(rule->action, g_fdir.records[i].subsystem);
                g_fdir.records[i].last_action = rule->action;
            }
        }
    }
    
    osal_mutex_unlock(g_fdir.mutex);
}

void fdir_report_fault(fault_type_t fault, subsystem_id_t subsys)
{
    if (fault >= FAULT_COUNT) {
        return;
    }
    
    osal_mutex_lock(g_fdir.mutex, OSAL_WAIT_FOREVER);
    
    g_fdir.records[fault].type = fault;
    g_fdir.records[fault].subsystem = subsys;
    g_fdir.records[fault].timestamp_ms = osal_get_time_ms();
    g_fdir.records[fault].occurrence_count++;
    g_fdir.records[fault].active = true;
    
    event_log_write(EVENT_ERROR, subsys, fault, "Fault reported");
    
    osal_mutex_unlock(g_fdir.mutex);
}

void fdir_clear_fault(fault_type_t fault)
{
    if (fault >= FAULT_COUNT) {
        return;
    }
    
    osal_mutex_lock(g_fdir.mutex, OSAL_WAIT_FOREVER);
    g_fdir.records[fault].active = false;
    osal_mutex_unlock(g_fdir.mutex);
}

bool fdir_is_fault_active(fault_type_t fault)
{
    if (fault >= FAULT_COUNT) {
        return false;
    }
    return g_fdir.records[fault].active;
}

uint32_t fdir_get_fault_count(fault_type_t fault)
{
    if (fault >= FAULT_COUNT) {
        return 0;
    }
    return g_fdir.records[fault].occurrence_count;
}

const fault_record_t* fdir_get_fault_record(fault_type_t fault)
{
    if (fault >= FAULT_COUNT) {
        return NULL;
    }
    return &g_fdir.records[fault];
}

void fdir_execute_recovery(fault_type_t fault)
{
    if (fault >= FAULT_COUNT) {
        return;
    }
    
    const fdir_rule_t *rule = find_rule(fault);
    if (rule) {
        execute_action(rule->action, g_fdir.records[fault].subsystem);
    }
}

void fdir_isolate_subsystem(subsystem_id_t subsys)
{
    if (subsys >= SUBSYS_COUNT) {
        return;
    }
    
    osal_mutex_lock(g_fdir.mutex, OSAL_WAIT_FOREVER);
    g_fdir.isolated_subsys[subsys] = 1;
    event_log_write(EVENT_WARNING, subsys, 0, "Subsystem isolated");
    osal_mutex_unlock(g_fdir.mutex);
}

void fdir_restore_subsystem(subsystem_id_t subsys)
{
    if (subsys >= SUBSYS_COUNT) {
        return;
    }
    
    osal_mutex_lock(g_fdir.mutex, OSAL_WAIT_FOREVER);
    g_fdir.isolated_subsys[subsys] = 0;
    event_log_write(EVENT_INFO, subsys, 0, "Subsystem restored");
    osal_mutex_unlock(g_fdir.mutex);
}

bool fdir_detect_reset_loop(void)
{
    /* Check boot counter from boot module */
    extern uint32_t boot_get_count(void);
    extern reset_cause_t boot_get_reset_cause(void);
    
    if (boot_get_reset_cause() == RESET_CAUSE_WATCHDOG) {
        if (boot_get_count() >= FDIR_RESET_LOOP_THRESHOLD) {
            return true;
        }
    }
    
    return false;
}

void fdir_reset_loop_handled(void)
{
    extern void boot_clear_counters(void);
    boot_clear_counters();
}

void fdir_force_safe_mode(const char *reason)
{
    event_log_write(EVENT_CRITICAL, SUBSYS_FDIR, 0, reason);
    mode_manager_force(MODE_SAFE);
}
