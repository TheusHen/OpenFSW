/**
 * @file uart.h
 * @brief UART Driver Interface
 */

#ifndef UART_H
#define UART_H

#include "../../core/openfsw.h"

/*===========================================================================*/
/* Types                                                                     */
/*===========================================================================*/
typedef enum {
    UART_PORT_1 = 0,
    UART_PORT_2,
    UART_PORT_3,
    UART_PORT_DEBUG,
    UART_PORT_COUNT
} uart_port_t;

typedef enum {
    UART_PARITY_NONE = 0,
    UART_PARITY_ODD,
    UART_PARITY_EVEN
} uart_parity_t;

typedef enum {
    UART_STOP_1 = 0,
    UART_STOP_2
} uart_stopbits_t;

typedef struct {
    uart_port_t port;
    uint32_t baudrate;
    uart_parity_t parity;
    uart_stopbits_t stopbits;
    uint8_t databits;
    bool hw_flow_control;
    uint32_t rx_buffer_size;
    uint32_t tx_buffer_size;
} uart_config_t;

typedef void (*uart_rx_callback_t)(uart_port_t port, uint8_t byte);

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

openfsw_status_t uart_init(const uart_config_t *config);
openfsw_status_t uart_deinit(uart_port_t port);

/* Transmit */
openfsw_status_t uart_write(uart_port_t port, const uint8_t *data, uint32_t len);
openfsw_status_t uart_write_byte(uart_port_t port, uint8_t byte);
openfsw_status_t uart_puts(uart_port_t port, const char *str);
uint32_t uart_write_available(uart_port_t port);

/* Receive */
openfsw_status_t uart_read(uart_port_t port, uint8_t *data, uint32_t len, uint32_t *actual);
openfsw_status_t uart_read_byte(uart_port_t port, uint8_t *byte, uint32_t timeout_ms);
uint32_t uart_read_available(uart_port_t port);
void uart_flush_rx(uart_port_t port);

/* Callbacks */
void uart_set_rx_callback(uart_port_t port, uart_rx_callback_t callback);

/* Status */
bool uart_is_tx_complete(uart_port_t port);

#endif /* UART_H */
