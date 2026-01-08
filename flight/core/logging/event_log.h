/**
 * @file event_log.h
 * @brief Event Logging System
 */

#ifndef EVENT_LOG_H
#define EVENT_LOG_H

#include "../openfsw.h"

/*===========================================================================*/
/* Configuration                                                             */
/*===========================================================================*/
#define EVENT_LOG_SIZE          256
#define EVENT_LOG_MSG_MAX_LEN   32

/*===========================================================================*/
/* Event Entry                                                               */
/*===========================================================================*/
typedef struct {
    uint32_t timestamp_ms;
    event_severity_t severity;
    subsystem_id_t subsystem;
    uint16_t event_id;
    char message[EVENT_LOG_MSG_MAX_LEN];
} event_entry_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void event_log_init(void);

/* Logging */
void event_log_write(event_severity_t severity, subsystem_id_t subsys, 
                     uint16_t event_id, const char *message);

void event_log_debug(subsystem_id_t subsys, const char *message);
void event_log_info(subsystem_id_t subsys, const char *message);
void event_log_warning(subsystem_id_t subsys, const char *message);
void event_log_error(subsystem_id_t subsys, uint16_t event_id, const char *message);
void event_log_critical(subsystem_id_t subsys, uint16_t event_id, const char *message);

/* Query */
uint32_t event_log_get_count(void);
const event_entry_t* event_log_get_entry(uint32_t index);
const event_entry_t* event_log_get_latest(void);

/* Filtering */
uint32_t event_log_count_by_severity(event_severity_t min_severity);
uint32_t event_log_count_by_subsystem(subsystem_id_t subsys);

/* Export */
uint32_t event_log_export(event_entry_t *buffer, uint32_t max_entries, 
                          event_severity_t min_severity);

/* Clear */
void event_log_clear(void);

/* Persistence */
openfsw_status_t event_log_save_to_nvm(void);
openfsw_status_t event_log_load_from_nvm(void);

#endif /* EVENT_LOG_H */
