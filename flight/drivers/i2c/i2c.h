/**
 * @file i2c.h
 * @brief I2C Driver Interface
 */

#ifndef I2C_H
#define I2C_H

#include "../../core/openfsw.h"

/*===========================================================================*/
/* Types                                                                     */
/*===========================================================================*/
typedef enum {
    I2C_BUS_1 = 0,
    I2C_BUS_2,
    I2C_BUS_COUNT
} i2c_bus_t;

typedef enum {
    I2C_SPEED_STANDARD = 100000,   /* 100 kHz */
    I2C_SPEED_FAST = 400000,       /* 400 kHz */
    I2C_SPEED_FAST_PLUS = 1000000  /* 1 MHz */
} i2c_speed_t;

typedef struct {
    i2c_bus_t bus;
    i2c_speed_t speed;
    uint32_t timeout_ms;
} i2c_config_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

openfsw_status_t i2c_init(const i2c_config_t *config);
openfsw_status_t i2c_deinit(i2c_bus_t bus);

/* Basic transfers */
openfsw_status_t i2c_write(i2c_bus_t bus, uint8_t addr, const uint8_t *data, uint32_t len);
openfsw_status_t i2c_read(i2c_bus_t bus, uint8_t addr, uint8_t *data, uint32_t len);

/* Register access */
openfsw_status_t i2c_write_reg(i2c_bus_t bus, uint8_t addr, uint8_t reg, uint8_t value);
openfsw_status_t i2c_read_reg(i2c_bus_t bus, uint8_t addr, uint8_t reg, uint8_t *value);
openfsw_status_t i2c_read_regs(i2c_bus_t bus, uint8_t addr, uint8_t reg, uint8_t *data, uint32_t len);

/* Combined transfer */
openfsw_status_t i2c_write_read(i2c_bus_t bus, uint8_t addr, 
                                 const uint8_t *write_data, uint32_t write_len,
                                 uint8_t *read_data, uint32_t read_len);

/* Bus management */
openfsw_status_t i2c_scan(i2c_bus_t bus, uint8_t *found_addrs, uint8_t *count, uint8_t max_count);
bool i2c_is_device_ready(i2c_bus_t bus, uint8_t addr);
void i2c_reset(i2c_bus_t bus);

#endif /* I2C_H */
