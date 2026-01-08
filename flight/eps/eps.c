/**
 * @file eps.c
 * @brief Electrical Power System Implementation
 */

#include "eps.h"
#include "../osal/osal.h"
#include "../drivers/bsp.h"
#include "../fdir/fdir.h"
#include "../core/mode/mode_manager.h"

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    eps_telemetry_t telemetry;
    osal_mutex_t mutex;
    bool initialized;
} g_eps;

/*===========================================================================*/
/* Helper Functions                                                          */
/*===========================================================================*/

static void eps_update_battery(void)
{
    /* In real implementation, read from battery monitor IC via I2C */
    /* For now, use simulation values */
    g_eps.telemetry.battery.voltage_mv = 3700;
    g_eps.telemetry.battery.current_ma = 0;
    g_eps.telemetry.battery.soc_percent = 80;
    g_eps.telemetry.battery.temperature_c = 25;
    g_eps.telemetry.battery.capacity_mah = 5200;
    g_eps.telemetry.battery.remaining_mah = 
        (g_eps.telemetry.battery.capacity_mah * g_eps.telemetry.battery.soc_percent) / 100;
}

static void eps_update_solar(void)
{
    /* Read from solar panel current sensors */
    uint16_t total_power = 0;
    
    for (int i = 0; i < EPS_NUM_SOLAR_PANELS; i++) {
        /* Simulation: alternate panels illuminated */
        g_eps.telemetry.panels[i].illuminated = (i % 2 == 0);
        if (g_eps.telemetry.panels[i].illuminated) {
            g_eps.telemetry.panels[i].voltage_mv = 2400;
            g_eps.telemetry.panels[i].current_ma = 200;
            g_eps.telemetry.panels[i].power_mw = 480;
        } else {
            g_eps.telemetry.panels[i].voltage_mv = 0;
            g_eps.telemetry.panels[i].current_ma = 0;
            g_eps.telemetry.panels[i].power_mw = 0;
        }
        total_power += g_eps.telemetry.panels[i].power_mw;
    }
    
    g_eps.telemetry.budget.generation_mw = total_power;
}

static void eps_update_consumption(void)
{
    uint16_t total = 0;
    
    for (int i = 0; i < RAIL_COUNT; i++) {
        if (g_eps.telemetry.rail_status[i]) {
            /* Read from current sensors */
            g_eps.telemetry.rail_current_ma[i] = 50 + (i * 20); /* Placeholder */
            total += (g_eps.telemetry.rail_current_ma[i] * 3300) / 1000; /* mW at 3.3V approx */
        } else {
            g_eps.telemetry.rail_current_ma[i] = 0;
        }
    }
    
    g_eps.telemetry.budget.consumption_mw = total;
}

static void eps_update_budget(void)
{
    g_eps.telemetry.budget.balance_mw = 
        (int16_t)g_eps.telemetry.budget.generation_mw - 
        (int16_t)g_eps.telemetry.budget.consumption_mw;
    
    g_eps.telemetry.budget.positive = (g_eps.telemetry.budget.balance_mw > 0);
    
    /* Update charging current */
    if (g_eps.telemetry.budget.positive) {
        g_eps.telemetry.battery.current_ma = g_eps.telemetry.budget.balance_mw / 4; /* Rough estimate */
    } else {
        g_eps.telemetry.battery.current_ma = g_eps.telemetry.budget.balance_mw / 4;
    }
}

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void eps_init(void)
{
    osal_mutex_create(&g_eps.mutex);
    
    /* Enable essential rails */
    g_eps.telemetry.rail_status[RAIL_3V3_CORE] = 1;
    g_eps.telemetry.rail_status[RAIL_5V_SENSORS] = 1;
    g_eps.telemetry.rail_status[RAIL_3V3_COMMS] = 1;
    g_eps.telemetry.rail_status[RAIL_12V_ACTUATORS] = 0;
    g_eps.telemetry.rail_status[RAIL_PAYLOAD] = 0;
    
    g_eps.telemetry.low_power_mode = false;
    g_eps.telemetry.critical_power = false;
    
    eps_update_battery();
    eps_update_solar();
    eps_update_consumption();
    eps_update_budget();
    
    g_eps.initialized = true;
}

void eps_periodic(void)
{
    if (!g_eps.initialized) {
        return;
    }
    
    osal_mutex_lock(g_eps.mutex, OSAL_WAIT_FOREVER);
    
    eps_update_battery();
    eps_update_solar();
    eps_update_consumption();
    eps_update_budget();
    
    /* Check for critical conditions */
    if (g_eps.telemetry.battery.soc_percent <= EPS_BATTERY_CRITICAL_SOC) {
        g_eps.telemetry.critical_power = true;
        fdir_report_fault(FAULT_POWER_CRITICAL, SUBSYS_EPS);
        eps_load_shed();
    } else if (g_eps.telemetry.battery.soc_percent <= EPS_BATTERY_LOW_SOC) {
        if (!g_eps.telemetry.low_power_mode) {
            eps_enter_low_power();
        }
    } else if (g_eps.telemetry.battery.soc_percent >= EPS_BATTERY_NOMINAL_SOC) {
        if (g_eps.telemetry.low_power_mode) {
            eps_exit_low_power();
        }
        g_eps.telemetry.critical_power = false;
    }
    
    osal_mutex_unlock(g_eps.mutex);
}

openfsw_status_t eps_enable_rail(power_rail_t rail)
{
    if (rail >= RAIL_COUNT) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    osal_mutex_lock(g_eps.mutex, OSAL_WAIT_FOREVER);
    g_eps.telemetry.rail_status[rail] = 1;
    bsp_power_enable_rail(rail);
    osal_mutex_unlock(g_eps.mutex);
    
    return OPENFSW_OK;
}

openfsw_status_t eps_disable_rail(power_rail_t rail)
{
    if (rail >= RAIL_COUNT) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    /* Don't allow disabling core rail */
    if (rail == RAIL_3V3_CORE) {
        return OPENFSW_ERROR_PERMISSION;
    }
    
    osal_mutex_lock(g_eps.mutex, OSAL_WAIT_FOREVER);
    g_eps.telemetry.rail_status[rail] = 0;
    bsp_power_disable_rail(rail);
    osal_mutex_unlock(g_eps.mutex);
    
    return OPENFSW_OK;
}

bool eps_is_rail_enabled(power_rail_t rail)
{
    if (rail >= RAIL_COUNT) {
        return false;
    }
    return g_eps.telemetry.rail_status[rail] != 0;
}

const battery_state_t* eps_get_battery_state(void)
{
    return &g_eps.telemetry.battery;
}

uint8_t eps_get_soc(void)
{
    return g_eps.telemetry.battery.soc_percent;
}

bool eps_is_charging(void)
{
    return g_eps.telemetry.battery.current_ma > 0;
}

uint16_t eps_get_solar_power(void)
{
    return g_eps.telemetry.budget.generation_mw;
}

bool eps_in_eclipse(void)
{
    return g_eps.telemetry.budget.generation_mw < 50;
}

const power_budget_t* eps_get_budget(void)
{
    return &g_eps.telemetry.budget;
}

bool eps_can_support_load(uint16_t power_mw)
{
    if (g_eps.telemetry.critical_power) {
        return false;
    }
    
    if (g_eps.telemetry.low_power_mode) {
        return power_mw < 100;
    }
    
    return (g_eps.telemetry.budget.balance_mw + (int16_t)power_mw) > 0;
}

void eps_enter_low_power(void)
{
    osal_mutex_lock(g_eps.mutex, OSAL_WAIT_FOREVER);
    
    g_eps.telemetry.low_power_mode = true;
    
    /* Disable non-essential rails */
    eps_disable_rail(RAIL_12V_ACTUATORS);
    eps_disable_rail(RAIL_PAYLOAD);
    
    mode_manager_request(MODE_LOW_POWER);
    
    osal_mutex_unlock(g_eps.mutex);
}

void eps_exit_low_power(void)
{
    osal_mutex_lock(g_eps.mutex, OSAL_WAIT_FOREVER);
    
    g_eps.telemetry.low_power_mode = false;
    
    /* Re-enable rails */
    eps_enable_rail(RAIL_12V_ACTUATORS);
    
    osal_mutex_unlock(g_eps.mutex);
}

bool eps_is_low_power(void)
{
    return g_eps.telemetry.low_power_mode;
}

void eps_load_shed(void)
{
    osal_mutex_lock(g_eps.mutex, OSAL_WAIT_FOREVER);
    
    /* Disable all non-essential loads */
    eps_disable_rail(RAIL_PAYLOAD);
    eps_disable_rail(RAIL_12V_ACTUATORS);
    eps_disable_rail(RAIL_5V_SENSORS);
    
    g_eps.telemetry.low_power_mode = true;
    
    osal_mutex_unlock(g_eps.mutex);
}

void eps_restore_loads(void)
{
    osal_mutex_lock(g_eps.mutex, OSAL_WAIT_FOREVER);
    
    if (g_eps.telemetry.battery.soc_percent >= EPS_BATTERY_NOMINAL_SOC) {
        eps_enable_rail(RAIL_5V_SENSORS);
        eps_enable_rail(RAIL_12V_ACTUATORS);
        g_eps.telemetry.low_power_mode = false;
    }
    
    osal_mutex_unlock(g_eps.mutex);
}

const eps_telemetry_t* eps_get_telemetry(void)
{
    return &g_eps.telemetry;
}
