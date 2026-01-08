/**
 * @file osal.h
 * @brief Operating System Abstraction Layer
 * 
 * Provides portable interface for RTOS primitives.
 * Supports: FreeRTOS, Zephyr, RTEMS (compile-time selection)
 */

#ifndef OSAL_H
#define OSAL_H

#include "../core/openfsw.h"

/*===========================================================================*/
/* Configuration                                                             */
/*===========================================================================*/
#define OSAL_WAIT_FOREVER   0xFFFFFFFF
#define OSAL_NO_WAIT        0

/*===========================================================================*/
/* Types                                                                     */
/*===========================================================================*/

typedef void* osal_task_t;
typedef void* osal_mutex_t;
typedef void* osal_sem_t;
typedef void* osal_queue_t;
typedef void* osal_timer_t;

typedef void (*osal_task_fn_t)(void *arg);
typedef void (*osal_timer_fn_t)(void *arg);

typedef struct {
    const char *name;
    osal_task_fn_t function;
    void *arg;
    uint32_t stack_size;
    uint8_t priority;
} osal_task_config_t;

typedef struct {
    const char *name;
    osal_timer_fn_t callback;
    void *arg;
    uint32_t period_ms;
    bool auto_reload;
} osal_timer_config_t;

/*===========================================================================*/
/* Task API                                                                  */
/*===========================================================================*/
openfsw_status_t osal_task_create(const osal_task_config_t *config, osal_task_t *task);
openfsw_status_t osal_task_delete(osal_task_t task);
void osal_task_delay(uint32_t ms);
void osal_task_delay_until(uint32_t *last_wake, uint32_t period_ms);
void osal_task_yield(void);
uint32_t osal_task_get_stack_high_water(osal_task_t task);
const char* osal_task_get_name(osal_task_t task);

/*===========================================================================*/
/* Mutex API                                                                 */
/*===========================================================================*/
openfsw_status_t osal_mutex_create(osal_mutex_t *mutex);
openfsw_status_t osal_mutex_delete(osal_mutex_t mutex);
openfsw_status_t osal_mutex_lock(osal_mutex_t mutex, uint32_t timeout_ms);
openfsw_status_t osal_mutex_unlock(osal_mutex_t mutex);

/*===========================================================================*/
/* Semaphore API                                                             */
/*===========================================================================*/
openfsw_status_t osal_sem_create(osal_sem_t *sem, uint32_t initial, uint32_t max);
openfsw_status_t osal_sem_delete(osal_sem_t sem);
openfsw_status_t osal_sem_take(osal_sem_t sem, uint32_t timeout_ms);
openfsw_status_t osal_sem_give(osal_sem_t sem);
openfsw_status_t osal_sem_give_from_isr(osal_sem_t sem);

/*===========================================================================*/
/* Queue API                                                                 */
/*===========================================================================*/
openfsw_status_t osal_queue_create(osal_queue_t *queue, uint32_t length, uint32_t item_size);
openfsw_status_t osal_queue_delete(osal_queue_t queue);
openfsw_status_t osal_queue_send(osal_queue_t queue, const void *item, uint32_t timeout_ms);
openfsw_status_t osal_queue_receive(osal_queue_t queue, void *item, uint32_t timeout_ms);
openfsw_status_t osal_queue_send_from_isr(osal_queue_t queue, const void *item);
uint32_t osal_queue_get_count(osal_queue_t queue);

/*===========================================================================*/
/* Timer API                                                                 */
/*===========================================================================*/
openfsw_status_t osal_timer_create(const osal_timer_config_t *config, osal_timer_t *timer);
openfsw_status_t osal_timer_start(osal_timer_t timer);
openfsw_status_t osal_timer_stop(osal_timer_t timer);
openfsw_status_t osal_timer_reset(osal_timer_t timer);
openfsw_status_t osal_timer_delete(osal_timer_t timer);

/*===========================================================================*/
/* Time API                                                                  */
/*===========================================================================*/
uint32_t osal_get_tick_count(void);
uint32_t osal_get_tick_rate_hz(void);
ofsw_time_ms_t osal_get_time_ms(void);

/*===========================================================================*/
/* Critical Section                                                          */
/*===========================================================================*/
void osal_enter_critical(void);
void osal_exit_critical(void);
uint32_t osal_enter_critical_from_isr(void);
void osal_exit_critical_from_isr(uint32_t state);

/*===========================================================================*/
/* Memory (Static only - no heap)                                            */
/*===========================================================================*/
/* Note: All allocations use static memory pools, not heap */

#endif /* OSAL_H */
