/**
 * @file telecommand.c
 * @brief Telecommand System Implementation
 * 
 * OpenFSW-LEO-3U Telecommand Management
 * - Command registration and dispatch
 * - Authorization and validation
 * - Command history
 * - Acknowledgment generation
 */

#include "telecommand.h"
#include "../osal/osal.h"
#include "../core/time/time_manager.h"
#include "../core/mode/mode_manager.h"
#include "../fdir/fdir.h"
#include "telemetry.h"
#include <string.h>

/*===========================================================================*/
/* Configuration                                                             */
/*===========================================================================*/
#define TC_MAX_HANDLERS         64
#define TC_HISTORY_SIZE         16
#define TC_SAFE_LIST_SIZE       16
#define TC_AUTH_KEY_SIZE        16

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    tc_definition_t handlers[TC_MAX_HANDLERS];
    uint8_t handler_count;
    
    tc_record_t history[TC_HISTORY_SIZE];
    uint8_t history_idx;
    
    uint8_t auth_key[TC_AUTH_KEY_SIZE];
    bool auth_key_set;
    
    struct {
        uint8_t service_type;
        uint8_t service_subtype;
    } safe_list[TC_SAFE_LIST_SIZE];
    uint8_t safe_list_count;
    
    uint32_t accepted_count;
    uint32_t rejected_count;
    uint32_t executed_count;
    
    osal_mutex_t mutex;
    bool initialized;
} g_telecommand;

/*===========================================================================*/
/* Private Functions                                                         */
/*===========================================================================*/

static tc_definition_t* find_handler(uint8_t service_type, uint8_t service_subtype)
{
    for (uint8_t i = 0; i < g_telecommand.handler_count; i++) {
        if (g_telecommand.handlers[i].service_type == service_type &&
            g_telecommand.handlers[i].service_subtype == service_subtype) {
            return &g_telecommand.handlers[i];
        }
    }
    return NULL;
}

static void record_command(const ccsds_tc_packet_t *pkt, tc_status_t status)
{
    tc_record_t *rec = &g_telecommand.history[g_telecommand.history_idx];
    
    rec->sequence = ccsds_get_sequence(&pkt->primary);
    rec->service_type = pkt->secondary.service_type;
    rec->service_subtype = pkt->secondary.service_subtype;
    rec->timestamp_ms = time_get_uptime_ms();
    rec->status = status;
    
    g_telecommand.history_idx = (g_telecommand.history_idx + 1) % TC_HISTORY_SIZE;
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void telecommand_init(void)
{
    memset(&g_telecommand, 0, sizeof(g_telecommand));
    osal_mutex_create(&g_telecommand.mutex);
    
    /* Register standard command handlers */
    
    /* Service 17: Test */
    tc_definition_t ping = {
        .service_type = PUS_SVC_TEST,
        .service_subtype = 1,
        .auth_level = TC_AUTH_NONE,
        .handler = tc_handler_ping,
        .name = "Ping",
        .timeout_ms = 1000
    };
    telecommand_register(&ping);
    
    tc_definition_t conn_test = {
        .service_type = PUS_SVC_TEST,
        .service_subtype = 2,
        .auth_level = TC_AUTH_NONE,
        .handler = tc_handler_connection_test,
        .name = "Connection Test",
        .timeout_ms = 5000
    };
    telecommand_register(&conn_test);
    
    /* Service 8: Function Management */
    tc_definition_t mode_change = {
        .service_type = PUS_SVC_FUNCTION_MGMT,
        .service_subtype = 1,
        .auth_level = TC_AUTH_ELEVATED,
        .handler = tc_handler_mode_change,
        .name = "Mode Change",
        .timeout_ms = 5000
    };
    telecommand_register(&mode_change);
    
    tc_definition_t reset = {
        .service_type = PUS_SVC_FUNCTION_MGMT,
        .service_subtype = 4,
        .auth_level = TC_AUTH_CRITICAL,
        .handler = tc_handler_reset,
        .name = "System Reset",
        .timeout_ms = 10000
    };
    telecommand_register(&reset);
    
    /* Service 3: Housekeeping */
    tc_definition_t enable_hk = {
        .service_type = PUS_SVC_HOUSEKEEPING,
        .service_subtype = 5,
        .auth_level = TC_AUTH_BASIC,
        .handler = tc_handler_enable_hk,
        .name = "Enable HK",
        .timeout_ms = 1000
    };
    telecommand_register(&enable_hk);
    
    tc_definition_t disable_hk = {
        .service_type = PUS_SVC_HOUSEKEEPING,
        .service_subtype = 6,
        .auth_level = TC_AUTH_BASIC,
        .handler = tc_handler_disable_hk,
        .name = "Disable HK",
        .timeout_ms = 1000
    };
    telecommand_register(&disable_hk);
    
    /* Service 9: Time Management */
    tc_definition_t time_sync = {
        .service_type = PUS_SVC_TIME_MGMT,
        .service_subtype = 1,
        .auth_level = TC_AUTH_ELEVATED,
        .handler = tc_handler_time_sync,
        .name = "Time Sync",
        .timeout_ms = 2000
    };
    telecommand_register(&time_sync);
    
    /* Add safe commands (always executable in safe mode) */
    telecommand_add_to_safe_list(PUS_SVC_TEST, 1);           /* Ping */
    telecommand_add_to_safe_list(PUS_SVC_TEST, 2);           /* Connection test */
    telecommand_add_to_safe_list(PUS_SVC_HOUSEKEEPING, 5);   /* Enable HK */
    telecommand_add_to_safe_list(PUS_SVC_HOUSEKEEPING, 6);   /* Disable HK */
    
    g_telecommand.initialized = true;
}

void telecommand_periodic(void)
{
    /* Nothing periodic for now - commands are processed on arrival */
}

openfsw_status_t telecommand_register(const tc_definition_t *def)
{
    if (!def || !def->handler) return OPENFSW_ERROR_INVALID_PARAM;
    if (g_telecommand.handler_count >= TC_MAX_HANDLERS) return OPENFSW_ERROR_NO_MEMORY;
    
    osal_mutex_lock(g_telecommand.mutex, OSAL_WAIT_FOREVER);
    
    /* Check for duplicate */
    if (find_handler(def->service_type, def->service_subtype)) {
        osal_mutex_unlock(g_telecommand.mutex);
        return OPENFSW_ERROR_BUSY;
    }
    
    memcpy(&g_telecommand.handlers[g_telecommand.handler_count], def, sizeof(tc_definition_t));
    g_telecommand.handler_count++;
    
    osal_mutex_unlock(g_telecommand.mutex);
    
    return OPENFSW_OK;
}

bool telecommand_validate(const ccsds_tc_packet_t *pkt)
{
    if (!pkt) return false;
    
    /* Check CRC */
    if (!ccsds_validate_tc(pkt)) return false;
    
    /* Check for valid handler */
    if (!find_handler(pkt->secondary.service_type, pkt->secondary.service_subtype)) {
        return false;
    }
    
    return true;
}

bool telecommand_authorize(const ccsds_tc_packet_t *pkt, tc_auth_level_t required)
{
    if (!pkt) return false;
    
    /* Always allow no-auth commands */
    if (required == TC_AUTH_NONE) return true;
    
    /* In safe mode, only allow safe-listed commands */
    if (mode_get_current() == MODE_SAFE) {
        if (!telecommand_is_safe(pkt->secondary.service_type, 
                                  pkt->secondary.service_subtype)) {
            return false;
        }
    }
    
    /* Check authentication if key is set */
    if (g_telecommand.auth_key_set && required >= TC_AUTH_ELEVATED) {
        return telecommand_verify_auth(pkt);
    }
    
    return true;
}

tc_status_t telecommand_process(const ccsds_tc_packet_t *pkt)
{
    if (!pkt) return TC_STATUS_REJECTED_INVALID;
    
    osal_mutex_lock(g_telecommand.mutex, OSAL_WAIT_FOREVER);
    
    /* Validate packet */
    if (!telecommand_validate(pkt)) {
        g_telecommand.rejected_count++;
        record_command(pkt, TC_STATUS_REJECTED_INVALID);
        osal_mutex_unlock(g_telecommand.mutex);
        return TC_STATUS_REJECTED_INVALID;
    }
    
    /* Find handler */
    tc_definition_t *handler = find_handler(pkt->secondary.service_type,
                                             pkt->secondary.service_subtype);
    
    /* Authorize command */
    if (!telecommand_authorize(pkt, handler->auth_level)) {
        g_telecommand.rejected_count++;
        record_command(pkt, TC_STATUS_REJECTED_AUTH);
        osal_mutex_unlock(g_telecommand.mutex);
        return TC_STATUS_REJECTED_AUTH;
    }
    
    /* Accept command */
    g_telecommand.accepted_count++;
    telecommand_send_ack(ccsds_get_sequence(&pkt->primary), TC_STATUS_ACCEPTED);
    
    osal_mutex_unlock(g_telecommand.mutex);
    
    /* Execute handler */
    uint8_t response[256];
    uint16_t resp_len = 0;
    
    tc_status_t result = handler->handler(pkt->data, pkt->data_length, 
                                           response, &resp_len);
    
    osal_mutex_lock(g_telecommand.mutex, OSAL_WAIT_FOREVER);
    
    if (result == TC_STATUS_EXECUTED) {
        g_telecommand.executed_count++;
    }
    
    record_command(pkt, result);
    telecommand_send_ack(ccsds_get_sequence(&pkt->primary), result);
    
    osal_mutex_unlock(g_telecommand.mutex);
    
    return result;
}

void telecommand_set_auth_key(const uint8_t *key, uint8_t len)
{
    if (!key || len == 0 || len > TC_AUTH_KEY_SIZE) return;
    
    osal_mutex_lock(g_telecommand.mutex, OSAL_WAIT_FOREVER);
    
    memset(g_telecommand.auth_key, 0, TC_AUTH_KEY_SIZE);
    memcpy(g_telecommand.auth_key, key, len);
    g_telecommand.auth_key_set = true;
    
    osal_mutex_unlock(g_telecommand.mutex);
}

bool telecommand_verify_auth(const ccsds_tc_packet_t *pkt)
{
    /* Simple HMAC-like verification using last 16 bytes of data */
    /* In production, use proper cryptographic verification */
    (void)pkt;
    
    if (!g_telecommand.auth_key_set) return true;
    
    /* TODO: Implement proper authentication */
    return true;
}

void telecommand_add_to_safe_list(uint8_t service_type, uint8_t service_subtype)
{
    if (g_telecommand.safe_list_count >= TC_SAFE_LIST_SIZE) return;
    
    g_telecommand.safe_list[g_telecommand.safe_list_count].service_type = service_type;
    g_telecommand.safe_list[g_telecommand.safe_list_count].service_subtype = service_subtype;
    g_telecommand.safe_list_count++;
}

bool telecommand_is_safe(uint8_t service_type, uint8_t service_subtype)
{
    for (uint8_t i = 0; i < g_telecommand.safe_list_count; i++) {
        if (g_telecommand.safe_list[i].service_type == service_type &&
            g_telecommand.safe_list[i].service_subtype == service_subtype) {
            return true;
        }
    }
    return false;
}

uint32_t telecommand_get_accepted_count(void)
{
    return g_telecommand.accepted_count;
}

uint32_t telecommand_get_rejected_count(void)
{
    return g_telecommand.rejected_count;
}

uint32_t telecommand_get_executed_count(void)
{
    return g_telecommand.executed_count;
}

const tc_record_t* telecommand_get_last_record(void)
{
    uint8_t last_idx = (g_telecommand.history_idx == 0) ? 
                        TC_HISTORY_SIZE - 1 : g_telecommand.history_idx - 1;
    return &g_telecommand.history[last_idx];
}

void telecommand_send_ack(uint16_t sequence, tc_status_t status)
{
    ccsds_tm_packet_t pkt;
    uint8_t ack_data[8];
    
    ack_data[0] = (sequence >> 8) & 0xFF;
    ack_data[1] = sequence & 0xFF;
    ack_data[2] = (uint8_t)status;
    ack_data[3] = 0;  /* Reserved */
    
    uint32_t ts = time_get_uptime_ms();
    ack_data[4] = (ts >> 24) & 0xFF;
    ack_data[5] = (ts >> 16) & 0xFF;
    ack_data[6] = (ts >> 8) & 0xFF;
    ack_data[7] = ts & 0xFF;
    
    ccsds_build_tm_header(&pkt, APID_SYSTEM, PUS_SVC_REQUEST_VERIFICATION, 
                           (status == TC_STATUS_ACCEPTED) ? 1 : 
                           (status == TC_STATUS_EXECUTED) ? 7 : 8);
    ccsds_tm_set_data(&pkt, ack_data, sizeof(ack_data));
    ccsds_finalize_tm(&pkt);
    
    telemetry_queue_packet(&pkt, TM_PRIORITY_HIGH);
}

/*===========================================================================*/
/* Standard Command Handlers                                                 */
/*===========================================================================*/

tc_status_t tc_handler_ping(const uint8_t *data, uint16_t len,
                            uint8_t *resp, uint16_t *resp_len)
{
    (void)data;
    (void)len;
    
    /* Echo back "PONG" */
    resp[0] = 'P';
    resp[1] = 'O';
    resp[2] = 'N';
    resp[3] = 'G';
    *resp_len = 4;
    
    return TC_STATUS_EXECUTED;
}

tc_status_t tc_handler_connection_test(const uint8_t *data, uint16_t len,
                                       uint8_t *resp, uint16_t *resp_len)
{
    /* Echo back received data */
    if (data && len > 0 && len <= 200) {
        memcpy(resp, data, len);
        *resp_len = len;
    } else {
        *resp_len = 0;
    }
    
    return TC_STATUS_EXECUTED;
}

tc_status_t tc_handler_mode_change(const uint8_t *data, uint16_t len,
                                   uint8_t *resp, uint16_t *resp_len)
{
    if (!data || len < 1) {
        *resp_len = 0;
        return TC_STATUS_FAILED;
    }
    
    system_mode_t target_mode = (system_mode_t)data[0];
    
    if (target_mode >= MODE_COUNT) {
        *resp_len = 0;
        return TC_STATUS_FAILED;
    }
    
    openfsw_status_t result = mode_request_transition(target_mode);
    
    resp[0] = (result == OPENFSW_OK) ? 1 : 0;
    resp[1] = (uint8_t)mode_get_current();
    *resp_len = 2;
    
    return (result == OPENFSW_OK) ? TC_STATUS_EXECUTED : TC_STATUS_FAILED;
}

tc_status_t tc_handler_reset(const uint8_t *data, uint16_t len,
                             uint8_t *resp, uint16_t *resp_len)
{
    (void)data;
    (void)len;
    
    /* Confirm reset request */
    resp[0] = 1;  /* Acknowledged */
    *resp_len = 1;
    
    /* Schedule reset - actual reset happens after response is sent */
    /* TODO: Implement deferred reset via FDIR */
    
    return TC_STATUS_EXECUTED;
}

tc_status_t tc_handler_enable_hk(const uint8_t *data, uint16_t len,
                                 uint8_t *resp, uint16_t *resp_len)
{
    if (!data || len < 2) {
        *resp_len = 0;
        return TC_STATUS_FAILED;
    }
    
    uint16_t packet_id = ((uint16_t)data[0] << 8) | data[1];
    
    openfsw_status_t result = telemetry_enable(packet_id);
    
    resp[0] = (result == OPENFSW_OK) ? 1 : 0;
    *resp_len = 1;
    
    return (result == OPENFSW_OK) ? TC_STATUS_EXECUTED : TC_STATUS_FAILED;
}

tc_status_t tc_handler_disable_hk(const uint8_t *data, uint16_t len,
                                  uint8_t *resp, uint16_t *resp_len)
{
    if (!data || len < 2) {
        *resp_len = 0;
        return TC_STATUS_FAILED;
    }
    
    uint16_t packet_id = ((uint16_t)data[0] << 8) | data[1];
    
    openfsw_status_t result = telemetry_disable(packet_id);
    
    resp[0] = (result == OPENFSW_OK) ? 1 : 0;
    *resp_len = 1;
    
    return (result == OPENFSW_OK) ? TC_STATUS_EXECUTED : TC_STATUS_FAILED;
}

tc_status_t tc_handler_time_sync(const uint8_t *data, uint16_t len,
                                 uint8_t *resp, uint16_t *resp_len)
{
    if (!data || len < 6) {
        *resp_len = 0;
        return TC_STATUS_FAILED;
    }
    
    /* Parse UTC time from command */
    ofsw_timestamp_t new_time;
    new_time.seconds = ((uint32_t)data[0] << 24) |
                       ((uint32_t)data[1] << 16) |
                       ((uint32_t)data[2] << 8) |
                       (uint32_t)data[3];
    new_time.subseconds = ((uint16_t)data[4] << 8) | data[5];
    
    time_set_utc(&new_time);
    
    /* Return current time in response */
    ofsw_timestamp_t current;
    time_get_timestamp(&current);
    
    resp[0] = (current.seconds >> 24) & 0xFF;
    resp[1] = (current.seconds >> 16) & 0xFF;
    resp[2] = (current.seconds >> 8) & 0xFF;
    resp[3] = current.seconds & 0xFF;
    *resp_len = 4;
    
    return TC_STATUS_EXECUTED;
}
