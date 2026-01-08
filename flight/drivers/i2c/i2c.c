/**
 * @file i2c.c
 * @brief Minimal I2C driver (stub)
 */

#include "i2c.h"

openfsw_status_t i2c_init(const i2c_config_t *config)
{
    if (!config) return OPENFSW_ERROR_INVALID_PARAM;
    if (config->bus >= I2C_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_OK;
}

openfsw_status_t i2c_deinit(i2c_bus_t bus)
{
    if (bus >= I2C_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_OK;
}

openfsw_status_t i2c_write(i2c_bus_t bus, uint8_t addr, const uint8_t *data, uint32_t len)
{
    (void)addr;
    if (bus >= I2C_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    if (!data && len != 0u) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_ERROR_NOT_READY;
}

openfsw_status_t i2c_read(i2c_bus_t bus, uint8_t addr, uint8_t *data, uint32_t len)
{
    (void)addr;
    if (bus >= I2C_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    if (!data && len != 0u) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_ERROR_NOT_READY;
}

openfsw_status_t i2c_write_reg(i2c_bus_t bus, uint8_t addr, uint8_t reg, uint8_t value)
{
    uint8_t buf[2] = {reg, value};
    return i2c_write(bus, addr, buf, 2);
}

openfsw_status_t i2c_read_reg(i2c_bus_t bus, uint8_t addr, uint8_t reg, uint8_t *value)
{
    if (!value) return OPENFSW_ERROR_INVALID_PARAM;
    return i2c_write_read(bus, addr, &reg, 1, value, 1);
}

openfsw_status_t i2c_read_regs(i2c_bus_t bus, uint8_t addr, uint8_t reg, uint8_t *data, uint32_t len)
{
    return i2c_write_read(bus, addr, &reg, 1, data, len);
}

openfsw_status_t i2c_write_read(i2c_bus_t bus, uint8_t addr,
                                const uint8_t *write_data, uint32_t write_len,
                                uint8_t *read_data, uint32_t read_len)
{
    (void)write_data;
    (void)write_len;
    (void)read_data;
    (void)read_len;
    if (bus >= I2C_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    (void)addr;
    return OPENFSW_ERROR_NOT_READY;
}

openfsw_status_t i2c_scan(i2c_bus_t bus, uint8_t *found_addrs, uint8_t *count, uint8_t max_count)
{
    (void)found_addrs;
    if (count) *count = 0;
    (void)max_count;
    if (bus >= I2C_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_ERROR_NOT_READY;
}

bool i2c_is_device_ready(i2c_bus_t bus, uint8_t addr)
{
    (void)bus;
    (void)addr;
    return false;
}

void i2c_reset(i2c_bus_t bus)
{
    (void)bus;
}
