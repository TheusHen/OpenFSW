/**
 * @file beacon.h
 * @brief Beacon System
 * 
 * OpenFSW-LEO-3U Beacon Transmission
 * - Periodic health beacon
 * - Emergency beacon
 * - Configurable intervals
 */

#ifndef BEACON_H
#define BEACON_H

#include "../../core/openfsw.h"

/*===========================================================================*/
/* Beacon Configuration                                                      */
/*===========================================================================*/
#define BEACON_NORMAL_INTERVAL_MS   30000   /* 30 seconds */
#define BEACON_SAFE_INTERVAL_MS     10000   /* 10 seconds */
#define BEACON_EMERGENCY_INTERVAL_MS 5000   /* 5 seconds */

#define BEACON_MAX_SIZE             64      /* bytes */
#define BEACON_CALLSIGN_SIZE        8

/*===========================================================================*/
/* Beacon Types                                                              */
/*===========================================================================*/
typedef enum {
    BEACON_TYPE_HEALTH = 0,
    BEACON_TYPE_STATUS,
    BEACON_TYPE_EMERGENCY,
    BEACON_TYPE_CUSTOM
} beacon_type_t;

/*===========================================================================*/
/* Standard Beacon Frame                                                     */
/*===========================================================================*/
typedef struct __attribute__((packed)) {
    /* Header - 12 bytes */
    char callsign[BEACON_CALLSIGN_SIZE];    /* Amateur radio callsign */
    uint8_t frame_type;
    uint8_t frame_version;
    uint16_t sequence;
    
    /* System Status - 8 bytes */
    uint32_t uptime_s;
    uint8_t mode;
    uint8_t health_flags;
    uint8_t reset_count;
    uint8_t fault_flags;
    
    /* Power Status - 8 bytes */
    uint16_t battery_voltage_mv;
    int16_t battery_current_ma;
    uint8_t battery_soc;
    int8_t battery_temp_c;
    uint16_t solar_power_mw;
    
    /* ADCS Status - 8 bytes */
    int16_t quaternion_w;       /* Q15 format */
    int16_t quaternion_x;
    int16_t quaternion_y;
    int16_t quaternion_z;
    
    /* Thermal - 4 bytes */
    int8_t temp_obc_c;
    int8_t temp_battery_c;
    int8_t temp_comms_c;
    int8_t temp_payload_c;
    
    /* Comms - 4 bytes */
    int8_t rssi_last;
    uint8_t packets_rx_24h;
    uint8_t packets_tx_24h;
    uint8_t link_margin_db;
    
    /* Checksum - 2 bytes */
    uint16_t crc16;
    
} beacon_frame_t;  /* Total: 46 bytes */

/*===========================================================================*/
/* Emergency Beacon                                                          */
/*===========================================================================*/
typedef struct __attribute__((packed)) {
    char callsign[BEACON_CALLSIGN_SIZE];
    uint8_t emergency_code;
    uint8_t sequence;
    uint32_t timestamp;
    uint16_t crc16;
} beacon_emergency_t;

/* Emergency Codes */
#define BEACON_EMERGENCY_POWER      0x01
#define BEACON_EMERGENCY_ATTITUDE   0x02
#define BEACON_EMERGENCY_THERMAL    0x04
#define BEACON_EMERGENCY_COMMS      0x08
#define BEACON_EMERGENCY_FDIR       0x10

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void beacon_init(void);
void beacon_periodic(void);

/* Configuration */
void beacon_set_callsign(const char *callsign);
void beacon_set_interval(uint32_t interval_ms);
void beacon_enable(void);
void beacon_disable(void);

/* Transmission */
openfsw_status_t beacon_transmit_now(void);
openfsw_status_t beacon_transmit_emergency(uint8_t code);

/* Status */
bool beacon_is_enabled(void);
uint32_t beacon_get_last_tx_time(void);
uint32_t beacon_get_tx_count(void);

/* Frame building */
void beacon_build_frame(beacon_frame_t *frame);

#endif /* BEACON_H */
