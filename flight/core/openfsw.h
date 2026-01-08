/**
 * @file openfsw.h
 * @brief OpenFSW-LEO-3U Main Header
 * 
 * Mission: OpenFSW-LEO-3U
 * Platform: 3U CubeSat (10x10x34 cm, ~4kg)
 * Orbit: LEO 500km, 97° SSO, ~95min period
 * Life: 6-12 months
 */

#ifndef OPENFSW_H
#define OPENFSW_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

/*===========================================================================*/
/* Version Info                                                              */
/*===========================================================================*/
#define OPENFSW_VERSION_MAJOR   1
#define OPENFSW_VERSION_MINOR   0
#define OPENFSW_VERSION_PATCH   0
#define OPENFSW_MISSION_NAME    "OpenFSW-LEO-3U"

/*===========================================================================*/
/* System Limits                                                             */
/*===========================================================================*/
#define OPENFSW_MAX_TASKS           16
#define OPENFSW_MAX_TIMERS          8
#define OPENFSW_MAX_EVENTS          32
#define OPENFSW_MAX_COMMANDS        64
#define OPENFSW_MAX_TM_PACKETS      32
#define OPENFSW_LOG_BUFFER_SIZE     1024
#define OPENFSW_CMD_QUEUE_SIZE      16
#define OPENFSW_TM_QUEUE_SIZE       32

/*===========================================================================*/
/* Reset Causes                                                              */
/*===========================================================================*/
typedef enum {
    RESET_CAUSE_UNKNOWN = 0,
    RESET_CAUSE_POWER_ON,
    RESET_CAUSE_PIN,
    RESET_CAUSE_WATCHDOG,
    RESET_CAUSE_SOFTWARE,
    RESET_CAUSE_BROWN_OUT,
    RESET_CAUSE_LOW_POWER,
    RESET_CAUSE_COUNT
} reset_cause_t;

/*===========================================================================*/
/* System Modes                                                              */
/*===========================================================================*/
typedef enum {
    MODE_BOOT = 0,
    MODE_SAFE,
    MODE_DETUMBLE,
    MODE_NOMINAL,
    MODE_LOW_POWER,
    MODE_RECOVERY,
    MODE_COUNT
} system_mode_t;

/*===========================================================================*/
/* Error Codes                                                               */
/*===========================================================================*/
typedef enum {
    OPENFSW_OK = 0,
    OPENFSW_ERROR,
    OPENFSW_ERROR_TIMEOUT,
    OPENFSW_ERROR_INVALID_PARAM,
    OPENFSW_ERROR_NO_MEMORY,
    OPENFSW_ERROR_BUSY,
    OPENFSW_ERROR_NOT_READY,
    OPENFSW_ERROR_NOT_FOUND,
    OPENFSW_ERROR_PERMISSION,
    OPENFSW_ERROR_CRC,
    OPENFSW_ERROR_OVERFLOW,
    OPENFSW_ERROR_UNDERFLOW,
    OPENFSW_ERROR_BUS,
    OPENFSW_ERROR_HARDWARE
} openfsw_status_t;

/*===========================================================================*/
/* Event Severity                                                            */
/*===========================================================================*/
typedef enum {
    EVENT_DEBUG = 0,
    EVENT_INFO,
    EVENT_WARNING,
    EVENT_ERROR,
    EVENT_CRITICAL
} event_severity_t;

/*===========================================================================*/
/* Subsystem IDs                                                             */
/*===========================================================================*/
typedef enum {
    SUBSYS_BOOT = 0,
    SUBSYS_RTOS,
    SUBSYS_CORE,
    SUBSYS_MODE,
    SUBSYS_HEALTH,
    SUBSYS_FDIR,
    SUBSYS_EPS,
    SUBSYS_ADCS,
    SUBSYS_COMMS,
    SUBSYS_PAYLOAD,
    SUBSYS_DATA,
    SUBSYS_TIME,
    SUBSYS_DRIVERS,
    SUBSYS_COUNT
} subsystem_id_t;

/*===========================================================================*/
/* Time Types                                                                */
/*===========================================================================*/
typedef uint32_t ofsw_time_ms_t;
typedef uint64_t ofsw_time_us_t;
typedef uint32_t ofsw_met_t;  /* Mission Elapsed Time in seconds */

/*===========================================================================*/
/* Common Structures                                                         */
/*===========================================================================*/

typedef struct {
    uint32_t boot_count;
    uint32_t uptime_seconds;
    reset_cause_t last_reset;
    system_mode_t current_mode;
    uint8_t error_count;
    uint8_t warning_count;
} system_status_t;

typedef struct {
    float x;
    float y;
    float z;
} vec3_t;

typedef struct {
    float w;
    float x;
    float y;
    float z;
} quaternion_t;

/*===========================================================================*/
/* Mission Parameters (LEO 500km SSO)                                        */
/*===========================================================================*/
#define MISSION_ORBIT_ALTITUDE_KM       500.0f
#define MISSION_ORBIT_INCLINATION_DEG   97.0f
#define MISSION_ORBIT_PERIOD_MIN        95.0f
#define MISSION_ECLIPSE_DURATION_MIN    35.0f
#define MISSION_LIFETIME_MONTHS         12

#define EARTH_RADIUS_KM                 6371.0f
#define EARTH_MU_KM3_S2                 398600.4418f
#define EARTH_J2                        1.08263e-3f
#define MAGNETIC_DIPOLE_AM2             7.94e22f

#endif /* OPENFSW_H */
