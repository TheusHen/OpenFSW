/**
 * @file adcs_interface.h
 * @brief C interface for ADCS telemetry exchange.
 */

#ifndef ADCS_INTERFACE_H
#define ADCS_INTERFACE_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    float quaternion[4];   /* w, x, y, z */
    float rate_rad_s[3];
    float error_angle_rad;
    uint8_t mode;
    uint8_t status;
    bool valid;
} adcs_telemetry_t;

void adcs_get_telemetry(adcs_telemetry_t *telemetry);
void adcs_set_telemetry(const adcs_telemetry_t *telemetry);

#endif /* ADCS_INTERFACE_H */
