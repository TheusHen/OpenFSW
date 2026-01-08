/**
 * @file spi.c
 * @brief Minimal SPI driver (stub)
 */

#include "spi.h"

openfsw_status_t spi_init(const spi_config_t *config)
{
    if (!config) return OPENFSW_ERROR_INVALID_PARAM;
    if (config->bus >= SPI_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_OK;
}

openfsw_status_t spi_deinit(spi_bus_t bus)
{
    if (bus >= SPI_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_OK;
}

openfsw_status_t spi_write(spi_bus_t bus, const spi_cs_t *cs, const uint8_t *data, uint32_t len)
{
    return spi_transfer(bus, cs, data, NULL, len);
}

openfsw_status_t spi_read(spi_bus_t bus, const spi_cs_t *cs, uint8_t *data, uint32_t len)
{
    return spi_transfer(bus, cs, NULL, data, len);
}

openfsw_status_t spi_transfer(spi_bus_t bus, const spi_cs_t *cs,
                              const uint8_t *tx_data, uint8_t *rx_data, uint32_t len)
{
    (void)cs;
    if (bus >= SPI_BUS_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    if ((!tx_data && !rx_data) && len != 0u) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_ERROR_NOT_READY;
}

openfsw_status_t spi_write_reg(spi_bus_t bus, const spi_cs_t *cs, uint8_t reg, uint8_t value)
{
    uint8_t buf[2] = {reg, value};
    return spi_write(bus, cs, buf, 2);
}

openfsw_status_t spi_read_reg(spi_bus_t bus, const spi_cs_t *cs, uint8_t reg, uint8_t *value)
{
    if (!value) return OPENFSW_ERROR_INVALID_PARAM;
    return spi_transfer(bus, cs, &reg, value, 1);
}

openfsw_status_t spi_read_regs(spi_bus_t bus, const spi_cs_t *cs, uint8_t reg, uint8_t *data, uint32_t len)
{
    return spi_transfer(bus, cs, &reg, data, len);
}

void spi_cs_assert(const spi_cs_t *cs)
{
    (void)cs;
}

void spi_cs_deassert(const spi_cs_t *cs)
{
    (void)cs;
}
