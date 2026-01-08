/**
 * @file telecommand.h
 * @brief Telecommand System
 */

#ifndef TELECOMMAND_H
#define TELECOMMAND_H

#include "../core/openfsw.h"
#include "../comms/ccsds/ccsds.h"

/*===========================================================================*/
/* Command Authorization Levels                                              */
/*===========================================================================*/
typedef enum {
    TC_AUTH_NONE = 0,      /* Always allowed */
    TC_AUTH_BASIC,         /* Basic operations */
    TC_AUTH_ELEVATED,      /* System configuration */
    TC_AUTH_CRITICAL       /* Safety-critical commands */
} tc_auth_level_t;

/*===========================================================================*/
/* Command Status                                                            */
/*===========================================================================*/
typedef enum {
    TC_STATUS_ACCEPTED = 0,
    TC_STATUS_REJECTED_AUTH,
    TC_STATUS_REJECTED_INVALID,
    TC_STATUS_REJECTED_BUSY,
    TC_STATUS_EXECUTED,
    TC_STATUS_FAILED,
    TC_STATUS_TIMEOUT
} tc_status_t;

/*===========================================================================*/
/* Command Handler                                                           */
/*===========================================================================*/
typedef tc_status_t (*tc_handler_t)(const uint8_t *data, uint16_t len, uint8_t *response, uint16_t *resp_len);

typedef struct {
    uint8_t service_type;
    uint8_t service_subtype;
    tc_auth_level_t auth_level;
    tc_handler_t handler;
    const char *name;
    uint32_t timeout_ms;
} tc_definition_t;

/*===========================================================================*/
/* Command Record                                                            */
/*===========================================================================*/
typedef struct {
    uint16_t sequence;
    uint8_t service_type;
    uint8_t service_subtype;
    uint32_t timestamp_ms;
    tc_status_t status;
} tc_record_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void telecommand_init(void);
void telecommand_periodic(void);

/* Command registration */
openfsw_status_t telecommand_register(const tc_definition_t *def);

/* Command processing */
tc_status_t telecommand_process(const ccsds_tc_packet_t *pkt);
bool telecommand_validate(const ccsds_tc_packet_t *pkt);
bool telecommand_authorize(const ccsds_tc_packet_t *pkt, tc_auth_level_t required);

/* Security */
void telecommand_set_auth_key(const uint8_t *key, uint8_t len);
bool telecommand_verify_auth(const ccsds_tc_packet_t *pkt);
void telecommand_add_to_safe_list(uint8_t service_type, uint8_t service_subtype);
bool telecommand_is_safe(uint8_t service_type, uint8_t service_subtype);

/* Statistics */
uint32_t telecommand_get_accepted_count(void);
uint32_t telecommand_get_rejected_count(void);
uint32_t telecommand_get_executed_count(void);
const tc_record_t* telecommand_get_last_record(void);

/* Acknowledgment */
void telecommand_send_ack(uint16_t sequence, tc_status_t status);

/*===========================================================================*/
/* Standard Command Handlers                                                 */
/*===========================================================================*/

/* Service 17: Test */
tc_status_t tc_handler_ping(const uint8_t *data, uint16_t len, uint8_t *resp, uint16_t *resp_len);
tc_status_t tc_handler_connection_test(const uint8_t *data, uint16_t len, uint8_t *resp, uint16_t *resp_len);

/* Service 8: Function Management */
tc_status_t tc_handler_mode_change(const uint8_t *data, uint16_t len, uint8_t *resp, uint16_t *resp_len);
tc_status_t tc_handler_reset(const uint8_t *data, uint16_t len, uint8_t *resp, uint16_t *resp_len);

/* Service 3: Housekeeping */
tc_status_t tc_handler_enable_hk(const uint8_t *data, uint16_t len, uint8_t *resp, uint16_t *resp_len);
tc_status_t tc_handler_disable_hk(const uint8_t *data, uint16_t len, uint8_t *resp, uint16_t *resp_len);

/* Service 9: Time Management */
tc_status_t tc_handler_time_sync(const uint8_t *data, uint16_t len, uint8_t *resp, uint16_t *resp_len);

#endif /* TELECOMMAND_H */
