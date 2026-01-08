/**
 * @file telemetry.h
 * @brief Telemetry System
 */

#ifndef TELEMETRY_H
#define TELEMETRY_H

#include "../core/openfsw.h"
#include "../comms/ccsds/ccsds.h"

/*===========================================================================*/
/* Telemetry Types                                                           */
/*===========================================================================*/

typedef enum {
    TM_TYPE_HOUSEKEEPING = 0,
    TM_TYPE_EVENT,
    TM_TYPE_SCIENCE,
    TM_TYPE_DIAGNOSTIC,
    TM_TYPE_COUNT
} tm_type_t;

typedef enum {
    TM_PRIORITY_LOW = 0,
    TM_PRIORITY_NORMAL,
    TM_PRIORITY_HIGH,
    TM_PRIORITY_CRITICAL
} tm_priority_t;

typedef struct {
    uint16_t packet_id;
    uint16_t apid;
    tm_type_t type;
    tm_priority_t priority;
    uint32_t period_ms;
    uint32_t last_sent_ms;
    bool enabled;
    void (*generator)(uint8_t *data, uint16_t *len);
} tm_definition_t;

/*===========================================================================*/
/* Housekeeping Structures                                                   */
/*===========================================================================*/

typedef struct __attribute__((packed)) {
    uint32_t uptime_s;
    uint8_t mode;
    uint8_t health_status;
    uint16_t boot_count;
    uint8_t reset_cause;
    uint8_t error_count;
    uint8_t warning_count;
    uint8_t reserved;
} tm_system_hk_t;

typedef struct __attribute__((packed)) {
    uint16_t battery_voltage_mv;
    int16_t battery_current_ma;
    uint8_t battery_soc;
    int8_t battery_temp_c;
    uint16_t solar_power_mw;
    uint8_t rail_status;
    uint8_t low_power_flag;
} tm_power_hk_t;

typedef struct __attribute__((packed)) {
    int16_t quaternion_w;  /* Fixed point Q15 */
    int16_t quaternion_x;
    int16_t quaternion_y;
    int16_t quaternion_z;
    int16_t rate_x;        /* mrad/s */
    int16_t rate_y;
    int16_t rate_z;
    uint8_t mode;
    uint8_t status;
    int16_t error_angle;   /* mrad */
} tm_adcs_hk_t;

typedef struct __attribute__((packed)) {
    uint8_t rx_packets;
    uint8_t tx_packets;
    int8_t rssi;
    uint8_t snr;
    uint8_t crc_errors;
    uint8_t status;
} tm_comms_hk_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void telemetry_init(void);
void telemetry_periodic(void);

/* Packet registration */
openfsw_status_t telemetry_register(const tm_definition_t *def);
openfsw_status_t telemetry_enable(uint16_t packet_id);
openfsw_status_t telemetry_disable(uint16_t packet_id);
openfsw_status_t telemetry_set_period(uint16_t packet_id, uint32_t period_ms);

/* Queue management */
uint32_t telemetry_queue_count(void);
openfsw_status_t telemetry_queue_packet(const ccsds_tm_packet_t *pkt, tm_priority_t priority);
openfsw_status_t telemetry_dequeue_packet(ccsds_tm_packet_t *pkt);

/* Event telemetry */
void telemetry_send_event(uint16_t event_id, const uint8_t *data, uint16_t len);

/* Standard housekeeping generators */
void telemetry_gen_system_hk(uint8_t *data, uint16_t *len);
void telemetry_gen_power_hk(uint8_t *data, uint16_t *len);
void telemetry_gen_adcs_hk(uint8_t *data, uint16_t *len);
void telemetry_gen_comms_hk(uint8_t *data, uint16_t *len);

#endif /* TELEMETRY_H */
