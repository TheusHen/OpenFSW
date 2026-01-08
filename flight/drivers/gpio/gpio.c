/**
 * @file gpio.c
 * @brief Minimal GPIO driver (stub)
 */

#include "gpio.h"

openfsw_status_t gpio_init(const gpio_config_t *config)
{
    if (!config) return OPENFSW_ERROR_INVALID_PARAM;
    return OPENFSW_OK;
}

openfsw_status_t gpio_deinit(gpio_port_t port, uint8_t pin)
{
    (void)port;
    (void)pin;
    return OPENFSW_OK;
}

bool gpio_read(gpio_port_t port, uint8_t pin)
{
    (void)port;
    (void)pin;
    return false;
}

void gpio_write(gpio_port_t port, uint8_t pin, bool value)
{
    (void)port;
    (void)pin;
    (void)value;
}

void gpio_toggle(gpio_port_t port, uint8_t pin)
{
    (void)port;
    (void)pin;
}

openfsw_status_t gpio_irq_enable(gpio_port_t port, uint8_t pin, gpio_irq_t trigger, gpio_irq_callback_t cb)
{
    (void)port;
    (void)pin;
    (void)trigger;
    (void)cb;
    return OPENFSW_ERROR_NOT_READY;
}

openfsw_status_t gpio_irq_disable(gpio_port_t port, uint8_t pin)
{
    (void)port;
    (void)pin;
    return OPENFSW_ERROR_NOT_READY;
}
