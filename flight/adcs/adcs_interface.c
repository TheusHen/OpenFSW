/**
 * @file adcs_interface.c
 * @brief C interface for ADCS telemetry exchange.
 */

#include "adcs_interface.h"
#include <string.h>

static adcs_telemetry_t g_adcs_telemetry = {
    .quaternion = {1.0f, 0.0f, 0.0f, 0.0f},
    .rate_rad_s = {0.0f, 0.0f, 0.0f},
    .error_angle_rad = 0.0f,
    .mode = 0,
    .status = 0,
    .valid = false,
};

void adcs_get_telemetry(adcs_telemetry_t *telemetry)
{
    if (!telemetry) {
        return;
    }
    memcpy(telemetry, &g_adcs_telemetry, sizeof(adcs_telemetry_t));
}

void adcs_set_telemetry(const adcs_telemetry_t *telemetry)
{
    if (!telemetry) {
        return;
    }
    memcpy(&g_adcs_telemetry, telemetry, sizeof(adcs_telemetry_t));
}
