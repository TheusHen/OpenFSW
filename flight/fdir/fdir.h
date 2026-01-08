/**
 * @file fdir.h
 * @brief Fault Detection, Isolation & Recovery
 */

#ifndef FDIR_H
#define FDIR_H

#include "../core/openfsw.h"

/*===========================================================================*/
/* Fault Types                                                               */
/*===========================================================================*/
typedef enum {
    FAULT_NONE = 0,
    FAULT_WATCHDOG_TIMEOUT,
    FAULT_BROWNOUT,
    FAULT_RESET_LOOP,
    FAULT_SENSOR_INVALID,
    FAULT_ACTUATOR_FAIL,
    FAULT_BUS_ERROR,
    FAULT_MEMORY_ERROR,
    FAULT_COMM_LOSS,
    FAULT_POWER_CRITICAL,
    FAULT_THERMAL_LIMIT,
    FAULT_ATTITUDE_LOST,
    FAULT_COUNT
} fault_type_t;

/*===========================================================================*/
/* Recovery Actions                                                          */
/*===========================================================================*/
typedef enum {
    RECOVERY_NONE = 0,
    RECOVERY_RETRY,
    RECOVERY_ISOLATE,
    RECOVERY_RESET_SUBSYS,
    RECOVERY_SAFE_MODE,
    RECOVERY_SYSTEM_RESET,
    RECOVERY_PAYLOAD_OFF,
    RECOVERY_LOAD_SHED
} recovery_action_t;

/*===========================================================================*/
/* Fault State                                                               */
/*===========================================================================*/
typedef struct {
    fault_type_t type;
    subsystem_id_t subsystem;
    uint32_t timestamp_ms;
    uint32_t occurrence_count;
    bool active;
    recovery_action_t last_action;
} fault_record_t;

/*===========================================================================*/
/* FDIR Configuration                                                        */
/*===========================================================================*/
typedef struct {
    fault_type_t fault;
    uint32_t threshold_count;
    uint32_t window_ms;
    recovery_action_t action;
} fdir_rule_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void fdir_init(void);
void fdir_periodic(void);

/* Fault reporting */
void fdir_report_fault(fault_type_t fault, subsystem_id_t subsys);
void fdir_clear_fault(fault_type_t fault);

/* Query */
bool fdir_is_fault_active(fault_type_t fault);
uint32_t fdir_get_fault_count(fault_type_t fault);
const fault_record_t* fdir_get_fault_record(fault_type_t fault);

/* Recovery */
void fdir_execute_recovery(fault_type_t fault);
void fdir_isolate_subsystem(subsystem_id_t subsys);
void fdir_restore_subsystem(subsystem_id_t subsys);

/* Reset loop detection */
bool fdir_detect_reset_loop(void);
void fdir_reset_loop_handled(void);

/* Forced safe mode */
void fdir_force_safe_mode(const char *reason);

#endif /* FDIR_H */
