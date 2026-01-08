/**
 * @file telemetry.c
 * @brief Telemetry System Implementation
 * 
 * OpenFSW-LEO-3U Telemetry Management
 * - Housekeeping collection and packetization
 * - Event telemetry
 * - Priority-based queuing
 * - CCSDS packet generation
 */

#include "telemetry.h"
#include "../osal/osal.h"
#include "../core/time/time_manager.h"
#include "../core/mode/mode_manager.h"
#include "../core/health/health_monitor.h"
#include "../eps/eps.h"
#include <string.h>

/*===========================================================================*/
/* Configuration                                                             */
/*===========================================================================*/
#define TM_MAX_DEFINITIONS      32
#define TM_QUEUE_SIZE           16
#define TM_HK_DEFAULT_PERIOD    1000    /* 1 Hz default HK */

/*===========================================================================*/
/* Queue Entry                                                               */
/*===========================================================================*/
typedef struct {
    ccsds_tm_packet_t packet;
    tm_priority_t priority;
    bool valid;
} tm_queue_entry_t;

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    tm_definition_t definitions[TM_MAX_DEFINITIONS];
    uint8_t def_count;
    
    tm_queue_entry_t queue[TM_QUEUE_SIZE];
    uint8_t queue_head;
    uint8_t queue_tail;
    uint8_t queue_count;
    
    osal_mutex_t mutex;
    bool initialized;
    
    /* Statistics */
    uint32_t packets_generated;
    uint32_t packets_queued;
    uint32_t packets_sent;
    uint32_t queue_overflows;
} g_telemetry;

/*===========================================================================*/
/* Private Functions                                                         */
/*===========================================================================*/

static int find_definition(uint16_t packet_id)
{
    for (uint8_t i = 0; i < g_telemetry.def_count; i++) {
        if (g_telemetry.definitions[i].packet_id == packet_id) {
            return (int)i;
        }
    }
    return -1;
}

static void generate_hk_packet(tm_definition_t *def)
{
    if (!def || !def->generator) return;
    
    uint8_t data[256];
    uint16_t len = 0;
    
    /* Call generator function */
    def->generator(data, &len);
    
    if (len > 0) {
        ccsds_tm_packet_t pkt;
        ccsds_build_tm_header(&pkt, def->apid, PUS_SVC_HOUSEKEEPING, 25);
        ccsds_tm_set_data(&pkt, data, len);
        ccsds_finalize_tm(&pkt);
        
        telemetry_queue_packet(&pkt, def->priority);
        g_telemetry.packets_generated++;
    }
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void telemetry_init(void)
{
    memset(&g_telemetry, 0, sizeof(g_telemetry));
    osal_mutex_create(&g_telemetry.mutex);
    
    /* Register standard housekeeping */
    tm_definition_t sys_hk = {
        .packet_id = 1,
        .apid = APID_SYSTEM,
        .type = TM_TYPE_HOUSEKEEPING,
        .priority = TM_PRIORITY_NORMAL,
        .period_ms = TM_HK_DEFAULT_PERIOD,
        .enabled = true,
        .generator = telemetry_gen_system_hk
    };
    telemetry_register(&sys_hk);
    
    tm_definition_t pwr_hk = {
        .packet_id = 2,
        .apid = APID_POWER,
        .type = TM_TYPE_HOUSEKEEPING,
        .priority = TM_PRIORITY_NORMAL,
        .period_ms = TM_HK_DEFAULT_PERIOD,
        .enabled = true,
        .generator = telemetry_gen_power_hk
    };
    telemetry_register(&pwr_hk);
    
    tm_definition_t adcs_hk = {
        .packet_id = 3,
        .apid = APID_ADCS,
        .type = TM_TYPE_HOUSEKEEPING,
        .priority = TM_PRIORITY_NORMAL,
        .period_ms = TM_HK_DEFAULT_PERIOD,
        .enabled = true,
        .generator = telemetry_gen_adcs_hk
    };
    telemetry_register(&adcs_hk);
    
    tm_definition_t comms_hk = {
        .packet_id = 4,
        .apid = APID_COMMS,
        .type = TM_TYPE_HOUSEKEEPING,
        .priority = TM_PRIORITY_NORMAL,
        .period_ms = 5000,  /* 0.2 Hz for comms */
        .enabled = true,
        .generator = telemetry_gen_comms_hk
    };
    telemetry_register(&comms_hk);
    
    g_telemetry.initialized = true;
}

void telemetry_periodic(void)
{
    if (!g_telemetry.initialized) return;
    
    uint32_t now = time_get_uptime_ms();
    
    osal_mutex_lock(g_telemetry.mutex, OSAL_WAIT_FOREVER);
    
    for (uint8_t i = 0; i < g_telemetry.def_count; i++) {
        tm_definition_t *def = &g_telemetry.definitions[i];
        
        if (!def->enabled) continue;
        if (def->type != TM_TYPE_HOUSEKEEPING) continue;
        
        if ((now - def->last_sent_ms) >= def->period_ms) {
            generate_hk_packet(def);
            def->last_sent_ms = now;
        }
    }
    
    osal_mutex_unlock(g_telemetry.mutex);
}

openfsw_status_t telemetry_register(const tm_definition_t *def)
{
    if (!def) return OPENFSW_ERROR_INVALID_PARAM;
    if (g_telemetry.def_count >= TM_MAX_DEFINITIONS) return OPENFSW_ERROR_NO_MEMORY;
    
    osal_mutex_lock(g_telemetry.mutex, OSAL_WAIT_FOREVER);
    
    /* Check for duplicate */
    if (find_definition(def->packet_id) >= 0) {
        osal_mutex_unlock(g_telemetry.mutex);
        return OPENFSW_ERROR_BUSY;
    }
    
    memcpy(&g_telemetry.definitions[g_telemetry.def_count], def, sizeof(tm_definition_t));
    g_telemetry.def_count++;
    
    osal_mutex_unlock(g_telemetry.mutex);
    
    return OPENFSW_OK;
}

openfsw_status_t telemetry_enable(uint16_t packet_id)
{
    osal_mutex_lock(g_telemetry.mutex, OSAL_WAIT_FOREVER);
    
    int idx = find_definition(packet_id);
    if (idx < 0) {
        osal_mutex_unlock(g_telemetry.mutex);
        return OPENFSW_ERROR_NOT_FOUND;
    }
    
    g_telemetry.definitions[idx].enabled = true;
    
    osal_mutex_unlock(g_telemetry.mutex);
    return OPENFSW_OK;
}

openfsw_status_t telemetry_disable(uint16_t packet_id)
{
    osal_mutex_lock(g_telemetry.mutex, OSAL_WAIT_FOREVER);
    
    int idx = find_definition(packet_id);
    if (idx < 0) {
        osal_mutex_unlock(g_telemetry.mutex);
        return OPENFSW_ERROR_NOT_FOUND;
    }
    
    g_telemetry.definitions[idx].enabled = false;
    
    osal_mutex_unlock(g_telemetry.mutex);
    return OPENFSW_OK;
}

openfsw_status_t telemetry_set_period(uint16_t packet_id, uint32_t period_ms)
{
    if (period_ms < 100) return OPENFSW_ERROR_INVALID_PARAM;  /* Min 100ms */
    
    osal_mutex_lock(g_telemetry.mutex, OSAL_WAIT_FOREVER);
    
    int idx = find_definition(packet_id);
    if (idx < 0) {
        osal_mutex_unlock(g_telemetry.mutex);
        return OPENFSW_ERROR_NOT_FOUND;
    }
    
    g_telemetry.definitions[idx].period_ms = period_ms;
    
    osal_mutex_unlock(g_telemetry.mutex);
    return OPENFSW_OK;
}

uint32_t telemetry_queue_count(void)
{
    return g_telemetry.queue_count;
}

openfsw_status_t telemetry_queue_packet(const ccsds_tm_packet_t *pkt, tm_priority_t priority)
{
    if (!pkt) return OPENFSW_ERROR_INVALID_PARAM;
    
    osal_mutex_lock(g_telemetry.mutex, OSAL_WAIT_FOREVER);
    
    if (g_telemetry.queue_count >= TM_QUEUE_SIZE) {
        /* Queue full - try to drop low priority packet if this is higher priority */
        if (priority >= TM_PRIORITY_HIGH) {
            /* Find and drop lowest priority packet */
            for (uint8_t i = 0; i < TM_QUEUE_SIZE; i++) {
                if (g_telemetry.queue[i].valid && 
                    g_telemetry.queue[i].priority < priority) {
                    g_telemetry.queue[i].valid = false;
                    g_telemetry.queue_count--;
                    break;
                }
            }
        }
        
        if (g_telemetry.queue_count >= TM_QUEUE_SIZE) {
            g_telemetry.queue_overflows++;
            osal_mutex_unlock(g_telemetry.mutex);
            return OPENFSW_ERROR_OVERFLOW;
        }
    }
    
    /* Find empty slot */
    uint8_t slot = g_telemetry.queue_tail;
    g_telemetry.queue[slot].packet = *pkt;
    g_telemetry.queue[slot].priority = priority;
    g_telemetry.queue[slot].valid = true;
    
    g_telemetry.queue_tail = (g_telemetry.queue_tail + 1) % TM_QUEUE_SIZE;
    g_telemetry.queue_count++;
    g_telemetry.packets_queued++;
    
    osal_mutex_unlock(g_telemetry.mutex);
    return OPENFSW_OK;
}

openfsw_status_t telemetry_dequeue_packet(ccsds_tm_packet_t *pkt)
{
    if (!pkt) return OPENFSW_ERROR_INVALID_PARAM;
    
    osal_mutex_lock(g_telemetry.mutex, OSAL_WAIT_FOREVER);
    
    if (g_telemetry.queue_count == 0) {
        osal_mutex_unlock(g_telemetry.mutex);
        return OPENFSW_ERROR_NOT_FOUND;
    }
    
    /* Find highest priority packet */
    int best_idx = -1;
    tm_priority_t best_priority = TM_PRIORITY_LOW;
    
    for (uint8_t i = 0; i < TM_QUEUE_SIZE; i++) {
        if (g_telemetry.queue[i].valid && 
            g_telemetry.queue[i].priority >= best_priority) {
            best_priority = g_telemetry.queue[i].priority;
            best_idx = i;
        }
    }
    
    if (best_idx < 0) {
        osal_mutex_unlock(g_telemetry.mutex);
        return OPENFSW_ERROR_NOT_FOUND;
    }
    
    *pkt = g_telemetry.queue[best_idx].packet;
    g_telemetry.queue[best_idx].valid = false;
    g_telemetry.queue_count--;
    g_telemetry.packets_sent++;
    
    osal_mutex_unlock(g_telemetry.mutex);
    return OPENFSW_OK;
}

void telemetry_send_event(uint16_t event_id, const uint8_t *data, uint16_t len)
{
    ccsds_tm_packet_t pkt;
    uint8_t event_data[256];
    uint16_t total_len = 0;
    
    /* Event header: event_id (2) + timestamp (4) */
    event_data[0] = (event_id >> 8) & 0xFF;
    event_data[1] = event_id & 0xFF;
    
    uint32_t ts = time_get_uptime_ms();
    event_data[2] = (ts >> 24) & 0xFF;
    event_data[3] = (ts >> 16) & 0xFF;
    event_data[4] = (ts >> 8) & 0xFF;
    event_data[5] = ts & 0xFF;
    total_len = 6;
    
    /* Append event data */
    if (data && len > 0 && len <= (256 - 6)) {
        memcpy(&event_data[6], data, len);
        total_len += len;
    }
    
    ccsds_build_tm_header(&pkt, APID_SYSTEM, PUS_SVC_EVENT_REPORTING, 5);
    ccsds_tm_set_data(&pkt, event_data, total_len);
    ccsds_finalize_tm(&pkt);
    
    telemetry_queue_packet(&pkt, TM_PRIORITY_HIGH);
}

/*===========================================================================*/
/* Standard Housekeeping Generators                                          */
/*===========================================================================*/

void telemetry_gen_system_hk(uint8_t *data, uint16_t *len)
{
    tm_system_hk_t hk;
    
    hk.uptime_s = time_get_uptime_ms() / 1000;
    hk.mode = (uint8_t)mode_get_current();
    hk.health_status = 0;  /* TODO: Get from health monitor */
    hk.boot_count = 0;     /* TODO: Get from persistent storage */
    hk.reset_cause = 0;    /* TODO: Get from boot */
    hk.error_count = 0;
    hk.warning_count = 0;
    hk.reserved = 0;
    
    memcpy(data, &hk, sizeof(hk));
    *len = sizeof(hk);
}

void telemetry_gen_power_hk(uint8_t *data, uint16_t *len)
{
    tm_power_hk_t hk;
    
    eps_status_t eps;
    eps_get_status(&eps);
    
    hk.battery_voltage_mv = eps.battery_voltage_mv;
    hk.battery_current_ma = eps.battery_current_ma;
    hk.battery_soc = eps.battery_soc;
    hk.battery_temp_c = eps.battery_temp_c;
    hk.solar_power_mw = eps.solar_power_mw;
    hk.rail_status = eps.rail_status;
    hk.low_power_flag = eps.low_power_flag;
    
    memcpy(data, &hk, sizeof(hk));
    *len = sizeof(hk);
}

void telemetry_gen_adcs_hk(uint8_t *data, uint16_t *len)
{
    tm_adcs_hk_t hk;
    
    /* TODO: Get actual ADCS data from Ada module */
    hk.quaternion_w = 32767;  /* 1.0 in Q15 */
    hk.quaternion_x = 0;
    hk.quaternion_y = 0;
    hk.quaternion_z = 0;
    hk.rate_x = 0;
    hk.rate_y = 0;
    hk.rate_z = 0;
    hk.mode = 0;
    hk.status = 0;
    hk.error_angle = 0;
    
    memcpy(data, &hk, sizeof(hk));
    *len = sizeof(hk);
}

void telemetry_gen_comms_hk(uint8_t *data, uint16_t *len)
{
    tm_comms_hk_t hk;
    
    /* TODO: Get actual comms statistics */
    hk.rx_packets = 0;
    hk.tx_packets = 0;
    hk.rssi = -80;
    hk.snr = 10;
    hk.crc_errors = 0;
    hk.status = 0;
    
    memcpy(data, &hk, sizeof(hk));
    *len = sizeof(hk);
}
