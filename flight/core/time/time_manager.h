/**
 * @file time_manager.h
 * @brief Time Management System
 */

#ifndef TIME_MANAGER_H
#define TIME_MANAGER_H

#include "../openfsw.h"

/*===========================================================================*/
/* Types                                                                     */
/*===========================================================================*/
typedef struct {
    uint32_t seconds;
    uint32_t subseconds;  /* Microseconds within second */
} ofsw_timestamp_t;

typedef struct {
    uint16_t year;
    uint8_t month;
    uint8_t day;
    uint8_t hour;
    uint8_t minute;
    uint8_t second;
    uint32_t microsecond;
} ofsw_datetime_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void time_manager_init(void);
void time_manager_tick(void);

/* System time (monotonic, from boot) */
ofsw_time_ms_t time_get_ms(void);
ofsw_time_us_t time_get_us(void);
uint32_t time_get_seconds(void);

/* Mission Elapsed Time (MET) */
ofsw_met_t time_get_met(void);
void time_set_met(ofsw_met_t met);

/* Uptime */
uint32_t time_get_uptime_seconds(void);

/* Convenience (ms) for scheduling/telemetry timestamps. */
ofsw_time_ms_t time_get_uptime_ms(void);

/* UTC time (if synchronized) */
bool time_is_synced(void);
void time_sync_utc(const ofsw_timestamp_t *utc);
openfsw_status_t time_get_utc(ofsw_timestamp_t *utc);
openfsw_status_t time_get_datetime(ofsw_datetime_t *dt);

/* Compatibility alias (used by TC handlers). */
static inline void time_set_utc(const ofsw_timestamp_t *utc)
{
    time_sync_utc(utc);
}

/* Time drift correction */
void time_set_drift_correction(int32_t ppm);
int32_t time_get_drift_correction(void);

/* Timestamps */
void time_get_timestamp(ofsw_timestamp_t *ts);
uint32_t time_diff_ms(const ofsw_timestamp_t *a, const ofsw_timestamp_t *b);

#endif /* TIME_MANAGER_H */
