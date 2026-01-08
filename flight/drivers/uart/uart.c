/**
 * @file uart.c
 * @brief Minimal UART driver (stub + debug backend)
 */

#include "uart.h"
#include "../bsp.h"

static uart_rx_callback_t g_rx_cb[UART_PORT_COUNT];

openfsw_status_t uart_init(const uart_config_t *config)
{
    if (!config) return OPENFSW_ERROR_INVALID_PARAM;
    if (config->port >= UART_PORT_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    /* Board-specific UART setup is provided by BSP/board layer.
     * This module defines the common API surface.
     */
    return OPENFSW_OK;
}

openfsw_status_t uart_deinit(uart_port_t port)
{
    if (port >= UART_PORT_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    g_rx_cb[port] = 0;
    return OPENFSW_OK;
}

openfsw_status_t uart_write(uart_port_t port, const uint8_t *data, uint32_t len)
{
    if (port >= UART_PORT_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    if (!data || len == 0u) return OPENFSW_OK;

    /* Default: route to BSP debug output. */
    for (uint32_t i = 0; i < len; i++) {
        bsp_debug_putchar((char)data[i]);
    }
    return OPENFSW_OK;
}

openfsw_status_t uart_write_byte(uart_port_t port, uint8_t byte)
{
    if (port >= UART_PORT_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    bsp_debug_putchar((char)byte);
    return OPENFSW_OK;
}

openfsw_status_t uart_puts(uart_port_t port, const char *str)
{
    if (port >= UART_PORT_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    if (!str) return OPENFSW_ERROR_INVALID_PARAM;
    bsp_debug_puts(str);
    return OPENFSW_OK;
}

uint32_t uart_write_available(uart_port_t port)
{
    (void)port;
    return 0xFFFFFFFFu;
}

openfsw_status_t uart_read(uart_port_t port, uint8_t *data, uint32_t len, uint32_t *actual)
{
    (void)data;
    (void)len;
    if (actual) *actual = 0u;
    if (port >= UART_PORT_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_ERROR_NOT_READY;
}

openfsw_status_t uart_read_byte(uart_port_t port, uint8_t *byte, uint32_t timeout_ms)
{
    (void)timeout_ms;
    if (port >= UART_PORT_COUNT) return OPENFSW_ERROR_INVALID_PARAM;
    if (!byte) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_ERROR_NOT_READY;
}

uint32_t uart_read_available(uart_port_t port)
{
    (void)port;
    return 0u;
}

void uart_flush_rx(uart_port_t port)
{
    (void)port;
}

void uart_set_rx_callback(uart_port_t port, uart_rx_callback_t callback)
{
    if (port >= UART_PORT_COUNT) return;
    g_rx_cb[port] = callback;
}

bool uart_is_tx_complete(uart_port_t port)
{
    (void)port;
    return true;
}

void uart_rx_isr_byte(uart_port_t port, uint8_t byte)
{
    if (port >= UART_PORT_COUNT) return;
    if (g_rx_cb[port]) {
        g_rx_cb[port](port, byte);
    }
}
