/**
 * @file health_monitor.c
 * @brief System Health Monitoring Implementation
 */

#include "health_monitor.h"
#include "../../osal/osal.h"
#include "../../drivers/bsp.h"

/*===========================================================================*/
/* Configuration                                                             */
/*===========================================================================*/
#define MAX_MONITORED_TASKS 16

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
typedef struct {
    const char *name;
    uint32_t timeout_ms;
    uint32_t last_heartbeat_ms;
    bool registered;
    bool alive;
} monitored_task_t;

static struct {
    health_data_t data;
    monitored_task_t tasks[MAX_MONITORED_TASKS];
    uint32_t error_counts[SUBSYS_COUNT];
    uint32_t warning_counts[SUBSYS_COUNT];
    osal_mutex_t mutex;
} g_health;

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void health_monitor_init(void)
{
    osal_mutex_create(&g_health.mutex);
    
    g_health.data.cpu_load_percent = 0;
    g_health.data.min_stack_bytes = 0xFFFFFFFF;
    g_health.data.temperature_c = 25;
    g_health.data.voltage_mv = 3700;
    g_health.data.overall = HEALTH_OK;
    g_health.data.error_count = 0;
    g_health.data.warning_count = 0;
    
    for (int i = 0; i < MAX_MONITORED_TASKS; i++) {
        g_health.tasks[i].registered = false;
        g_health.tasks[i].alive = false;
    }
    
    for (int i = 0; i < SUBSYS_COUNT; i++) {
        g_health.error_counts[i] = 0;
        g_health.warning_counts[i] = 0;
    }
}

void health_monitor_register_task(uint8_t task_id, const char *name, uint32_t timeout_ms)
{
    if (task_id >= MAX_MONITORED_TASKS) {
        return;
    }
    
    osal_mutex_lock(g_health.mutex, OSAL_WAIT_FOREVER);
    
    g_health.tasks[task_id].name = name;
    g_health.tasks[task_id].timeout_ms = timeout_ms;
    g_health.tasks[task_id].last_heartbeat_ms = osal_get_time_ms();
    g_health.tasks[task_id].registered = true;
    g_health.tasks[task_id].alive = true;
    
    osal_mutex_unlock(g_health.mutex);
}

void health_monitor_update_task(uint8_t task_id)
{
    if (task_id >= MAX_MONITORED_TASKS) {
        return;
    }
    
    osal_mutex_lock(g_health.mutex, OSAL_WAIT_FOREVER);
    
    if (g_health.tasks[task_id].registered) {
        g_health.tasks[task_id].last_heartbeat_ms = osal_get_time_ms();
        g_health.tasks[task_id].alive = true;
    }
    
    osal_mutex_unlock(g_health.mutex);
}

void health_monitor_periodic(void)
{
    osal_mutex_lock(g_health.mutex, OSAL_WAIT_FOREVER);
    
    uint32_t now = osal_get_time_ms();
    health_status_t status = HEALTH_OK;
    
    /* Check task heartbeats */
    for (int i = 0; i < MAX_MONITORED_TASKS; i++) {
        if (!g_health.tasks[i].registered) {
            continue;
        }
        
        uint32_t elapsed = now - g_health.tasks[i].last_heartbeat_ms;
        if (elapsed > g_health.tasks[i].timeout_ms) {
            g_health.tasks[i].alive = false;
            status = HEALTH_CRITICAL;
        }
    }
    
    /* Check thresholds */
    if (g_health.data.temperature_c < HEALTH_TEMP_MIN_C ||
        g_health.data.temperature_c > HEALTH_TEMP_MAX_C) {
        status = (status == HEALTH_OK) ? HEALTH_WARNING : status;
    }
    
    if (g_health.data.voltage_mv < HEALTH_VOLTAGE_MIN_MV ||
        g_health.data.voltage_mv > HEALTH_VOLTAGE_MAX_MV) {
        status = HEALTH_CRITICAL;
    }
    
    if (g_health.data.cpu_load_percent > HEALTH_CPU_WARNING_PERCENT) {
        status = (status == HEALTH_OK) ? HEALTH_WARNING : status;
    }
    
    if (g_health.data.min_stack_bytes < HEALTH_STACK_WARNING_BYTES) {
        status = (status == HEALTH_OK) ? HEALTH_WARNING : status;
    }
    
    g_health.data.overall = status;
    
    /* Kick watchdog */
    bsp_watchdog_kick();
    
    osal_mutex_unlock(g_health.mutex);
}

health_status_t health_monitor_get_status(void)
{
    return g_health.data.overall;
}

const health_data_t* health_monitor_get_data(void)
{
    return &g_health.data;
}

bool health_monitor_is_task_alive(uint8_t task_id)
{
    if (task_id >= MAX_MONITORED_TASKS) {
        return false;
    }
    return g_health.tasks[task_id].alive;
}

void health_monitor_increment_error(subsystem_id_t subsys)
{
    if (subsys >= SUBSYS_COUNT) {
        return;
    }
    
    osal_mutex_lock(g_health.mutex, OSAL_WAIT_FOREVER);
    g_health.error_counts[subsys]++;
    g_health.data.error_count++;
    osal_mutex_unlock(g_health.mutex);
}

void health_monitor_increment_warning(subsystem_id_t subsys)
{
    if (subsys >= SUBSYS_COUNT) {
        return;
    }
    
    osal_mutex_lock(g_health.mutex, OSAL_WAIT_FOREVER);
    g_health.warning_counts[subsys]++;
    g_health.data.warning_count++;
    osal_mutex_unlock(g_health.mutex);
}

uint32_t health_monitor_get_error_count(subsystem_id_t subsys)
{
    if (subsys >= SUBSYS_COUNT) {
        return 0;
    }
    return g_health.error_counts[subsys];
}
