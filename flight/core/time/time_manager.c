/**
 * @file time_manager.c
 * @brief Time Management Implementation
 */

#include "time_manager.h"
#include "../../osal/osal.h"

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    ofsw_met_t mission_time;    /* Mission elapsed time (seconds) */
    ofsw_timestamp_t utc_base;  /* UTC base when synced */
    uint32_t utc_sync_uptime_s; /* Uptime when UTC was synced (seconds) */
    int32_t drift_ppm;          /* Drift correction in PPM */
    bool utc_synced;
    osal_mutex_t mutex;
} g_time;

/*===========================================================================*/
/* Constants                                                                 */
/*===========================================================================*/
static const uint8_t days_in_month[12] = {
    31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31
};

/*===========================================================================*/
/* Helper Functions                                                          */
/*===========================================================================*/

static bool is_leap_year(uint16_t year)
{
    return ((year % 4 == 0) && (year % 100 != 0)) || (year % 400 == 0);
}

static void seconds_to_datetime(uint32_t total_seconds, ofsw_datetime_t *dt)
{
    /* Epoch: 2000-01-01 00:00:00 */
    uint32_t days = total_seconds / 86400;
    uint32_t remaining = total_seconds % 86400;
    
    dt->hour = remaining / 3600;
    remaining %= 3600;
    dt->minute = remaining / 60;
    dt->second = remaining % 60;
    
    /* Calculate year */
    dt->year = 2000;
    while (days >= (is_leap_year(dt->year) ? 366 : 365)) {
        days -= is_leap_year(dt->year) ? 366 : 365;
        dt->year++;
    }
    
    /* Calculate month */
    dt->month = 1;
    while (days >= days_in_month[dt->month - 1]) {
        uint8_t d = days_in_month[dt->month - 1];
        if (dt->month == 2 && is_leap_year(dt->year)) {
            d = 29;
        }
        if (days < d) break;
        days -= d;
        dt->month++;
    }
    
    dt->day = days + 1;
    dt->microsecond = 0;
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void time_manager_init(void)
{
    osal_mutex_create(&g_time.mutex);

    g_time.mission_time = 0;
    g_time.utc_base.seconds = 0;
    g_time.utc_base.subseconds = 0;
    g_time.utc_sync_uptime_s = 0;
    g_time.drift_ppm = 0;
    g_time.utc_synced = false;
}

void time_manager_tick(void)
{
    /* Legacy hook. OpenFSW uses OSAL tick-based time as source of truth.
     * Keep this as a no-op to preserve API stability.
     */
}

ofsw_time_ms_t time_get_ms(void)
{
    return osal_get_time_ms();
}

ofsw_time_us_t time_get_us(void)
{
    return (ofsw_time_us_t)osal_get_time_ms() * 1000ULL;
}

uint32_t time_get_seconds(void)
{
    return (uint32_t)(osal_get_time_ms() / 1000u);
}

ofsw_met_t time_get_met(void)
{
    return g_time.mission_time;
}

void time_set_met(ofsw_met_t met)
{
    osal_mutex_lock(g_time.mutex, OSAL_WAIT_FOREVER);
    g_time.mission_time = met;
    osal_mutex_unlock(g_time.mutex);
}

uint32_t time_get_uptime_seconds(void)
{
    return time_get_seconds();
}

ofsw_time_ms_t time_get_uptime_ms(void)
{
    return time_get_ms();
}

bool time_is_synced(void)
{
    return g_time.utc_synced;
}

void time_sync_utc(const ofsw_timestamp_t *utc)
{
    if (!utc) return;
    
    osal_mutex_lock(g_time.mutex, OSAL_WAIT_FOREVER);
    g_time.utc_base = *utc;
    g_time.utc_sync_uptime_s = time_get_seconds();
    g_time.utc_synced = true;
    osal_mutex_unlock(g_time.mutex);
}

openfsw_status_t time_get_utc(ofsw_timestamp_t *utc)
{
    if (!utc) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    if (!g_time.utc_synced) {
        return OPENFSW_ERROR_NOT_READY;
    }
    
    osal_mutex_lock(g_time.mutex, OSAL_WAIT_FOREVER);

    uint32_t elapsed = time_get_seconds() - g_time.utc_sync_uptime_s;
    
    /* Apply drift correction */
    if (g_time.drift_ppm != 0) {
        int32_t correction = (int32_t)elapsed * g_time.drift_ppm / 1000000;
        elapsed += correction;
    }
    
    utc->seconds = g_time.utc_base.seconds + elapsed;
    utc->subseconds = (osal_get_time_ms() % 1000u) * 1000u;
    
    osal_mutex_unlock(g_time.mutex);
    
    return OPENFSW_OK;
}

openfsw_status_t time_get_datetime(ofsw_datetime_t *dt)
{
    if (!dt) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    ofsw_timestamp_t utc;
    openfsw_status_t status = time_get_utc(&utc);
    if (status != OPENFSW_OK) {
        return status;
    }
    
    seconds_to_datetime(utc.seconds, dt);
    dt->microsecond = utc.subseconds;
    
    return OPENFSW_OK;
}

void time_set_drift_correction(int32_t ppm)
{
    osal_mutex_lock(g_time.mutex, OSAL_WAIT_FOREVER);
    g_time.drift_ppm = ppm;
    osal_mutex_unlock(g_time.mutex);
}

int32_t time_get_drift_correction(void)
{
    return g_time.drift_ppm;
}

void time_get_timestamp(ofsw_timestamp_t *ts)
{
    if (!ts) return;

    ts->seconds = time_get_seconds();
    ts->subseconds = (osal_get_time_ms() % 1000u) * 1000u;
}

uint32_t time_diff_ms(const ofsw_timestamp_t *a, const ofsw_timestamp_t *b)
{
    if (!a || !b) return 0;
    
    int32_t diff_s = (int32_t)a->seconds - (int32_t)b->seconds;
    int32_t diff_us = (int32_t)a->subseconds - (int32_t)b->subseconds;
    
    return (uint32_t)(diff_s * 1000 + diff_us / 1000);
}
