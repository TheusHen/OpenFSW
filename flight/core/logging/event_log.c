/**
 * @file event_log.c
 * @brief Event Logging Implementation
 */

#include "event_log.h"
#include "../../osal/osal.h"
#include <string.h>

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    event_entry_t entries[EVENT_LOG_SIZE];
    uint32_t write_index;
    uint32_t count;
    osal_mutex_t mutex;
    bool initialized;
} g_log;

/*===========================================================================*/
/* Helper Functions                                                          */
/*===========================================================================*/

static void safe_strcpy(char *dst, const char *src, size_t max_len)
{
    if (!dst || !src || max_len == 0) return;
    
    size_t i;
    for (i = 0; i < max_len - 1 && src[i] != '\0'; i++) {
        dst[i] = src[i];
    }
    dst[i] = '\0';
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void event_log_init(void)
{
    osal_mutex_create(&g_log.mutex);
    
    memset(g_log.entries, 0, sizeof(g_log.entries));
    g_log.write_index = 0;
    g_log.count = 0;
    g_log.initialized = true;
}

void event_log_write(event_severity_t severity, subsystem_id_t subsys,
                     uint16_t event_id, const char *message)
{
    if (!g_log.initialized) return;
    
    osal_mutex_lock(g_log.mutex, OSAL_WAIT_FOREVER);
    
    event_entry_t *entry = &g_log.entries[g_log.write_index];
    
    entry->timestamp_ms = osal_get_time_ms();
    entry->severity = severity;
    entry->subsystem = subsys;
    entry->event_id = event_id;
    
    if (message) {
        safe_strcpy(entry->message, message, EVENT_LOG_MSG_MAX_LEN);
    } else {
        entry->message[0] = '\0';
    }
    
    g_log.write_index = (g_log.write_index + 1) % EVENT_LOG_SIZE;
    if (g_log.count < EVENT_LOG_SIZE) {
        g_log.count++;
    }
    
    osal_mutex_unlock(g_log.mutex);
}

void event_log_debug(subsystem_id_t subsys, const char *message)
{
    event_log_write(EVENT_DEBUG, subsys, 0, message);
}

void event_log_info(subsystem_id_t subsys, const char *message)
{
    event_log_write(EVENT_INFO, subsys, 0, message);
}

void event_log_warning(subsystem_id_t subsys, const char *message)
{
    event_log_write(EVENT_WARNING, subsys, 0, message);
}

void event_log_error(subsystem_id_t subsys, uint16_t event_id, const char *message)
{
    event_log_write(EVENT_ERROR, subsys, event_id, message);
}

void event_log_critical(subsystem_id_t subsys, uint16_t event_id, const char *message)
{
    event_log_write(EVENT_CRITICAL, subsys, event_id, message);
}

uint32_t event_log_get_count(void)
{
    return g_log.count;
}

const event_entry_t* event_log_get_entry(uint32_t index)
{
    if (index >= g_log.count) {
        return NULL;
    }
    
    /* Calculate actual index in circular buffer */
    uint32_t actual_index;
    if (g_log.count < EVENT_LOG_SIZE) {
        actual_index = index;
    } else {
        actual_index = (g_log.write_index + index) % EVENT_LOG_SIZE;
    }
    
    return &g_log.entries[actual_index];
}

const event_entry_t* event_log_get_latest(void)
{
    if (g_log.count == 0) {
        return NULL;
    }
    
    uint32_t latest = (g_log.write_index + EVENT_LOG_SIZE - 1) % EVENT_LOG_SIZE;
    return &g_log.entries[latest];
}

uint32_t event_log_count_by_severity(event_severity_t min_severity)
{
    uint32_t count = 0;
    
    osal_mutex_lock(g_log.mutex, OSAL_WAIT_FOREVER);
    
    for (uint32_t i = 0; i < g_log.count; i++) {
        const event_entry_t *entry = event_log_get_entry(i);
        if (entry && entry->severity >= min_severity) {
            count++;
        }
    }
    
    osal_mutex_unlock(g_log.mutex);
    
    return count;
}

uint32_t event_log_count_by_subsystem(subsystem_id_t subsys)
{
    uint32_t count = 0;
    
    osal_mutex_lock(g_log.mutex, OSAL_WAIT_FOREVER);
    
    for (uint32_t i = 0; i < g_log.count; i++) {
        const event_entry_t *entry = event_log_get_entry(i);
        if (entry && entry->subsystem == subsys) {
            count++;
        }
    }
    
    osal_mutex_unlock(g_log.mutex);
    
    return count;
}

uint32_t event_log_export(event_entry_t *buffer, uint32_t max_entries,
                          event_severity_t min_severity)
{
    if (!buffer || max_entries == 0) {
        return 0;
    }
    
    uint32_t exported = 0;
    
    osal_mutex_lock(g_log.mutex, OSAL_WAIT_FOREVER);
    
    for (uint32_t i = 0; i < g_log.count && exported < max_entries; i++) {
        const event_entry_t *entry = event_log_get_entry(i);
        if (entry && entry->severity >= min_severity) {
            buffer[exported] = *entry;
            exported++;
        }
    }
    
    osal_mutex_unlock(g_log.mutex);
    
    return exported;
}

void event_log_clear(void)
{
    osal_mutex_lock(g_log.mutex, OSAL_WAIT_FOREVER);
    
    memset(g_log.entries, 0, sizeof(g_log.entries));
    g_log.write_index = 0;
    g_log.count = 0;
    
    osal_mutex_unlock(g_log.mutex);
}

openfsw_status_t event_log_save_to_nvm(void)
{
    /* TODO: Implement NVM storage */
    return OPENFSW_OK;
}

openfsw_status_t event_log_load_from_nvm(void)
{
    /* TODO: Implement NVM loading */
    return OPENFSW_OK;
}
