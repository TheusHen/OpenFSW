/**
 * @file eps.h
 * @brief Electrical Power System
 */

#ifndef EPS_H
#define EPS_H

#include "../core/openfsw.h"

/*===========================================================================*/
/* Power Rails                                                               */
/*===========================================================================*/
typedef enum {
    RAIL_3V3_CORE = 0,
    RAIL_5V_SENSORS,
    RAIL_12V_ACTUATORS,
    RAIL_3V3_COMMS,
    RAIL_PAYLOAD,
    RAIL_COUNT
} power_rail_t;

/*===========================================================================*/
/* Battery State                                                             */
/*===========================================================================*/
typedef struct {
    uint16_t voltage_mv;
    int16_t current_ma;         /* Positive = charging */
    uint8_t soc_percent;        /* State of charge */
    int8_t temperature_c;
    uint32_t capacity_mah;
    uint32_t remaining_mah;
} battery_state_t;

/*===========================================================================*/
/* Solar Panel State                                                         */
/*===========================================================================*/
typedef struct {
    uint16_t voltage_mv;
    uint16_t current_ma;
    uint16_t power_mw;
    bool illuminated;
} solar_panel_t;

#define EPS_NUM_SOLAR_PANELS    6

/*===========================================================================*/
/* Power Budget                                                              */
/*===========================================================================*/
typedef struct {
    uint16_t generation_mw;
    uint16_t consumption_mw;
    int16_t balance_mw;
    bool positive;
} power_budget_t;

/*===========================================================================*/
/* EPS Telemetry                                                             */
/*===========================================================================*/
typedef struct {
    battery_state_t battery;
    solar_panel_t panels[EPS_NUM_SOLAR_PANELS];
    power_budget_t budget;
    uint8_t rail_status[RAIL_COUNT];
    uint16_t rail_current_ma[RAIL_COUNT];
    bool low_power_mode;
    bool critical_power;
} eps_telemetry_t;

/*===========================================================================*/
/* Thresholds                                                                */
/*===========================================================================*/
#define EPS_BATTERY_CRITICAL_SOC    10
#define EPS_BATTERY_LOW_SOC         20
#define EPS_BATTERY_NOMINAL_SOC     50
#define EPS_BATTERY_FULL_SOC        95

#define EPS_LOAD_SHED_THRESHOLD_MW  500
#define EPS_SAFE_POWER_THRESHOLD_MW 200

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void eps_init(void);
void eps_periodic(void);

/* Power control */
openfsw_status_t eps_enable_rail(power_rail_t rail);
openfsw_status_t eps_disable_rail(power_rail_t rail);
bool eps_is_rail_enabled(power_rail_t rail);

/* Battery */
const battery_state_t* eps_get_battery_state(void);
uint8_t eps_get_soc(void);
bool eps_is_charging(void);

/* Solar */
uint16_t eps_get_solar_power(void);
bool eps_in_eclipse(void);

/* Power budget */
const power_budget_t* eps_get_budget(void);
bool eps_can_support_load(uint16_t power_mw);

/* Low power mode */
void eps_enter_low_power(void);
void eps_exit_low_power(void);
bool eps_is_low_power(void);

/* Load shedding */
void eps_load_shed(void);
void eps_restore_loads(void);

/* Telemetry */
const eps_telemetry_t* eps_get_telemetry(void);

#endif /* EPS_H */
