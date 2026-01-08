/**
 * @file gpio.h
 * @brief GPIO Driver Interface
 */

#ifndef GPIO_H
#define GPIO_H

#include "../../core/openfsw.h"

/*===========================================================================*/
/* Types                                                                     */
/*===========================================================================*/
typedef enum {
    GPIO_PORT_A = 0,
    GPIO_PORT_B,
    GPIO_PORT_C,
    GPIO_PORT_D,
    GPIO_PORT_E,
    GPIO_PORT_F,
    GPIO_PORT_G,
    GPIO_PORT_H,
    GPIO_PORT_COUNT
} gpio_port_t;

typedef enum {
    GPIO_MODE_INPUT = 0,
    GPIO_MODE_OUTPUT,
    GPIO_MODE_ALTERNATE,
    GPIO_MODE_ANALOG
} gpio_mode_t;

typedef enum {
    GPIO_PULL_NONE = 0,
    GPIO_PULL_UP,
    GPIO_PULL_DOWN
} gpio_pull_t;

typedef enum {
    GPIO_SPEED_LOW = 0,
    GPIO_SPEED_MEDIUM,
    GPIO_SPEED_HIGH,
    GPIO_SPEED_VERY_HIGH
} gpio_speed_t;

typedef enum {
    GPIO_IRQ_NONE = 0,
    GPIO_IRQ_RISING,
    GPIO_IRQ_FALLING,
    GPIO_IRQ_BOTH
} gpio_irq_t;

typedef struct {
    gpio_port_t port;
    uint8_t pin;
    gpio_mode_t mode;
    gpio_pull_t pull;
    gpio_speed_t speed;
    uint8_t alternate;
} gpio_config_t;

typedef void (*gpio_irq_callback_t)(gpio_port_t port, uint8_t pin);

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

openfsw_status_t gpio_init(const gpio_config_t *config);
openfsw_status_t gpio_deinit(gpio_port_t port, uint8_t pin);

/* Read/Write */
bool gpio_read(gpio_port_t port, uint8_t pin);
void gpio_write(gpio_port_t port, uint8_t pin, bool value);
void gpio_toggle(gpio_port_t port, uint8_t pin);

/* Interrupt */
openfsw_status_t gpio_irq_enable(gpio_port_t port, uint8_t pin, gpio_irq_t trigger, gpio_irq_callback_t cb);
openfsw_status_t gpio_irq_disable(gpio_port_t port, uint8_t pin);

#endif /* GPIO_H */
