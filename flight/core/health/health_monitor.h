/**
 * @file health_monitor.h
 * @brief System Health Monitoring
 */

#ifndef HEALTH_MONITOR_H
#define HEALTH_MONITOR_H

#include "../openfsw.h"

/*===========================================================================*/
/* Thresholds                                                                */
/*===========================================================================*/
#define HEALTH_STACK_WARNING_BYTES  128
#define HEALTH_CPU_WARNING_PERCENT  80
#define HEALTH_TEMP_MIN_C           -40
#define HEALTH_TEMP_MAX_C           85
#define HEALTH_VOLTAGE_MIN_MV       3000
#define HEALTH_VOLTAGE_MAX_MV       4200

/*===========================================================================*/
/* Health Status                                                             */
/*===========================================================================*/
typedef enum {
    HEALTH_OK = 0,
    HEALTH_WARNING,
    HEALTH_CRITICAL
} health_status_t;

typedef struct {
    uint32_t cpu_load_percent;
    uint32_t min_stack_bytes;
    int16_t temperature_c;
    uint16_t voltage_mv;
    health_status_t overall;
    uint32_t error_count;
    uint32_t warning_count;
} health_data_t;

typedef struct {
    uint32_t heartbeat;
    uint32_t last_update_ms;
    bool alive;
} task_health_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void health_monitor_init(void);
void health_monitor_periodic(void);
void health_monitor_update_task(uint8_t task_id);
health_status_t health_monitor_get_status(void);
const health_data_t* health_monitor_get_data(void);
void health_monitor_register_task(uint8_t task_id, const char *name, uint32_t timeout_ms);
bool health_monitor_is_task_alive(uint8_t task_id);
void health_monitor_increment_error(subsystem_id_t subsys);
void health_monitor_increment_warning(subsystem_id_t subsys);
uint32_t health_monitor_get_error_count(subsystem_id_t subsys);

#endif /* HEALTH_MONITOR_H */
