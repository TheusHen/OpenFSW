/**
 * @file beacon.c
 * @brief Beacon System Implementation
 * 
 * OpenFSW-LEO-3U Beacon Transmission
 */

#include "beacon.h"
#include "../../osal/osal.h"
#include "../../core/time/time_manager.h"
#include "../../core/mode/mode_manager.h"
#include "../../eps/eps.h"
#include "../ccsds/ccsds.h"
#include <string.h>

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    char callsign[BEACON_CALLSIGN_SIZE + 1];
    uint32_t interval_ms;
    uint32_t last_tx_ms;
    uint32_t tx_count;
    uint16_t sequence;
    bool enabled;
    bool initialized;
} g_beacon;

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void beacon_init(void)
{
    memset(&g_beacon, 0, sizeof(g_beacon));
    
    /* Default callsign */
    strncpy(g_beacon.callsign, "OFSW-3U", BEACON_CALLSIGN_SIZE);
    
    g_beacon.interval_ms = BEACON_NORMAL_INTERVAL_MS;
    g_beacon.enabled = true;
    g_beacon.initialized = true;
}

void beacon_periodic(void)
{
    if (!g_beacon.initialized || !g_beacon.enabled) return;
    
    uint32_t now = time_get_uptime_ms();
    uint32_t interval = g_beacon.interval_ms;
    
    /* Use faster beacon rate in safe mode */
    system_mode_t mode = mode_get_current();
    if (mode == MODE_SAFE) {
        interval = BEACON_SAFE_INTERVAL_MS;
    } else if (mode == MODE_RECOVERY) {
        interval = BEACON_EMERGENCY_INTERVAL_MS;
    }
    
    if ((now - g_beacon.last_tx_ms) >= interval) {
        beacon_transmit_now();
        g_beacon.last_tx_ms = now;
    }
}

void beacon_set_callsign(const char *callsign)
{
    if (!callsign) return;
    
    memset(g_beacon.callsign, 0, sizeof(g_beacon.callsign));
    strncpy(g_beacon.callsign, callsign, BEACON_CALLSIGN_SIZE);
}

void beacon_set_interval(uint32_t interval_ms)
{
    if (interval_ms < 1000) interval_ms = 1000;  /* Min 1 second */
    if (interval_ms > 300000) interval_ms = 300000;  /* Max 5 minutes */
    
    g_beacon.interval_ms = interval_ms;
}

void beacon_enable(void)
{
    g_beacon.enabled = true;
}

void beacon_disable(void)
{
    g_beacon.enabled = false;
}

bool beacon_is_enabled(void)
{
    return g_beacon.enabled;
}

uint32_t beacon_get_last_tx_time(void)
{
    return g_beacon.last_tx_ms;
}

uint32_t beacon_get_tx_count(void)
{
    return g_beacon.tx_count;
}

void beacon_build_frame(beacon_frame_t *frame)
{
    if (!frame) return;
    
    memset(frame, 0, sizeof(beacon_frame_t));
    
    /* Header */
    memcpy(frame->callsign, g_beacon.callsign, BEACON_CALLSIGN_SIZE);
    frame->frame_type = BEACON_TYPE_HEALTH;
    frame->frame_version = 1;
    frame->sequence = g_beacon.sequence++;
    
    /* System Status */
    frame->uptime_s = time_get_uptime_ms() / 1000;
    frame->mode = (uint8_t)mode_get_current();
    frame->health_flags = 0;  /* TODO: Get from health monitor */
    frame->reset_count = 0;   /* TODO: Get from persistent storage */
    frame->fault_flags = 0;   /* TODO: Get from FDIR */
    
    /* Power Status */
    eps_status_t eps;
    eps_get_status(&eps);
    
    frame->battery_voltage_mv = eps.battery_voltage_mv;
    frame->battery_current_ma = eps.battery_current_ma;
    frame->battery_soc = eps.battery_soc;
    frame->battery_temp_c = eps.battery_temp_c;
    frame->solar_power_mw = eps.solar_power_mw;
    
    /* ADCS Status - TODO: Get from ADCS module */
    frame->quaternion_w = 32767;  /* 1.0 in Q15 */
    frame->quaternion_x = 0;
    frame->quaternion_y = 0;
    frame->quaternion_z = 0;
    
    /* Thermal - TODO: Get from thermal sensors */
    frame->temp_obc_c = 25;
    frame->temp_battery_c = eps.battery_temp_c;
    frame->temp_comms_c = 25;
    frame->temp_payload_c = 25;
    
    /* Comms - TODO: Get from comms statistics */
    frame->rssi_last = -80;
    frame->packets_rx_24h = 0;
    frame->packets_tx_24h = 0;
    frame->link_margin_db = 10;
    
    /* Calculate CRC */
    frame->crc16 = ccsds_calc_crc((const uint8_t*)frame, 
                                   sizeof(beacon_frame_t) - 2);
}

openfsw_status_t beacon_transmit_now(void)
{
    beacon_frame_t frame;
    beacon_build_frame(&frame);
    
    /* TODO: Send via radio driver */
    /* For now, just increment counter */
    
    g_beacon.tx_count++;
    
    return OPENFSW_OK;
}

openfsw_status_t beacon_transmit_emergency(uint8_t code)
{
    beacon_emergency_t emergency;
    
    memcpy(emergency.callsign, g_beacon.callsign, BEACON_CALLSIGN_SIZE);
    emergency.emergency_code = code;
    emergency.sequence = (uint8_t)(g_beacon.sequence++ & 0xFF);
    emergency.timestamp = time_get_uptime_ms() / 1000;
    emergency.crc16 = ccsds_calc_crc((const uint8_t*)&emergency, 
                                      sizeof(beacon_emergency_t) - 2);
    
    /* TODO: Send via radio driver with high priority */
    
    g_beacon.tx_count++;
    
    return OPENFSW_OK;
}
