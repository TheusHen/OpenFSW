/**
 * @file spi.h
 * @brief SPI Driver Interface
 */

#ifndef SPI_H
#define SPI_H

#include "../../core/openfsw.h"

/*===========================================================================*/
/* Types                                                                     */
/*===========================================================================*/
typedef enum {
    SPI_BUS_1 = 0,
    SPI_BUS_2,
    SPI_BUS_3,
    SPI_BUS_COUNT
} spi_bus_t;

typedef enum {
    SPI_MODE_0 = 0,  /* CPOL=0, CPHA=0 */
    SPI_MODE_1,      /* CPOL=0, CPHA=1 */
    SPI_MODE_2,      /* CPOL=1, CPHA=0 */
    SPI_MODE_3       /* CPOL=1, CPHA=1 */
} spi_mode_t;

typedef struct {
    spi_bus_t bus;
    spi_mode_t mode;
    uint32_t clock_hz;
    bool msb_first;
    uint8_t bits_per_word;
    uint32_t timeout_ms;
} spi_config_t;

typedef struct {
    uint8_t port;
    uint8_t pin;
} spi_cs_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

openfsw_status_t spi_init(const spi_config_t *config);
openfsw_status_t spi_deinit(spi_bus_t bus);

/* Basic transfers */
openfsw_status_t spi_write(spi_bus_t bus, const spi_cs_t *cs, const uint8_t *data, uint32_t len);
openfsw_status_t spi_read(spi_bus_t bus, const spi_cs_t *cs, uint8_t *data, uint32_t len);
openfsw_status_t spi_transfer(spi_bus_t bus, const spi_cs_t *cs, 
                               const uint8_t *tx_data, uint8_t *rx_data, uint32_t len);

/* Register access */
openfsw_status_t spi_write_reg(spi_bus_t bus, const spi_cs_t *cs, uint8_t reg, uint8_t value);
openfsw_status_t spi_read_reg(spi_bus_t bus, const spi_cs_t *cs, uint8_t reg, uint8_t *value);
openfsw_status_t spi_read_regs(spi_bus_t bus, const spi_cs_t *cs, uint8_t reg, uint8_t *data, uint32_t len);

/* CS control */
void spi_cs_assert(const spi_cs_t *cs);
void spi_cs_deassert(const spi_cs_t *cs);

#endif /* SPI_H */
