/**
 * @file osal_freertos.c
 * @brief OSAL Implementation for FreeRTOS
 */

#include "osal.h"
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"
#include "queue.h"
#include "timers.h"

/*===========================================================================*/
/* Static Memory Pools                                                       */
/*===========================================================================*/
#define OSAL_MAX_TASKS    16
#define OSAL_MAX_MUTEXES  16
#define OSAL_MAX_SEMS     16
#define OSAL_MAX_QUEUES   8
#define OSAL_MAX_TIMERS   8
#define OSAL_TASK_STACK_SIZE 512

static StaticTask_t task_tcbs[OSAL_MAX_TASKS];
static StackType_t task_stacks[OSAL_MAX_TASKS][OSAL_TASK_STACK_SIZE];
static uint8_t task_used[OSAL_MAX_TASKS];

static StaticSemaphore_t mutex_buffers[OSAL_MAX_MUTEXES];
static uint8_t mutex_used[OSAL_MAX_MUTEXES];

static StaticSemaphore_t sem_buffers[OSAL_MAX_SEMS];
static uint8_t sem_used[OSAL_MAX_SEMS];

static StaticQueue_t queue_buffers[OSAL_MAX_QUEUES];
static uint8_t queue_storage[OSAL_MAX_QUEUES][256];
static uint8_t queue_used[OSAL_MAX_QUEUES];

static StaticTimer_t timer_buffers[OSAL_MAX_TIMERS];
static uint8_t timer_used[OSAL_MAX_TIMERS];

/*===========================================================================*/
/* Task API                                                                  */
/*===========================================================================*/

openfsw_status_t osal_task_create(const osal_task_config_t *config, osal_task_t *task)
{
    if (!config || !task) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    /* Find free slot */
    int slot = -1;
    for (int i = 0; i < OSAL_MAX_TASKS; i++) {
        if (!task_used[i]) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        return OPENFSW_ERROR_NO_MEMORY;
    }
    
    TaskHandle_t handle = xTaskCreateStatic(
        (TaskFunction_t)config->function,
        config->name,
        OSAL_TASK_STACK_SIZE,
        config->arg,
        (UBaseType_t)config->priority,
        task_stacks[slot],
        &task_tcbs[slot]
    );
    
    if (handle == NULL) {
        return OPENFSW_ERROR;
    }
    
    task_used[slot] = 1;
    *task = (osal_task_t)handle;
    return OPENFSW_OK;
}

openfsw_status_t osal_task_delete(osal_task_t task)
{
    if (!task) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    vTaskDelete((TaskHandle_t)task);
    return OPENFSW_OK;
}

void osal_task_delay(uint32_t ms)
{
    vTaskDelay(pdMS_TO_TICKS(ms));
}

void osal_task_delay_until(uint32_t *last_wake, uint32_t period_ms)
{
    TickType_t wake = (TickType_t)*last_wake;
    vTaskDelayUntil(&wake, pdMS_TO_TICKS(period_ms));
    *last_wake = (uint32_t)wake;
}

void osal_task_yield(void)
{
    taskYIELD();
}

uint32_t osal_task_get_stack_high_water(osal_task_t task)
{
    return (uint32_t)uxTaskGetStackHighWaterMark((TaskHandle_t)task);
}

const char* osal_task_get_name(osal_task_t task)
{
    return pcTaskGetName((TaskHandle_t)task);
}

/*===========================================================================*/
/* Mutex API                                                                 */
/*===========================================================================*/

openfsw_status_t osal_mutex_create(osal_mutex_t *mutex)
{
    if (!mutex) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    int slot = -1;
    for (int i = 0; i < OSAL_MAX_MUTEXES; i++) {
        if (!mutex_used[i]) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        return OPENFSW_ERROR_NO_MEMORY;
    }
    
    SemaphoreHandle_t handle = xSemaphoreCreateMutexStatic(&mutex_buffers[slot]);
    if (handle == NULL) {
        return OPENFSW_ERROR;
    }
    
    mutex_used[slot] = 1;
    *mutex = (osal_mutex_t)handle;
    return OPENFSW_OK;
}

openfsw_status_t osal_mutex_delete(osal_mutex_t mutex)
{
    if (!mutex) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    vSemaphoreDelete((SemaphoreHandle_t)mutex);
    return OPENFSW_OK;
}

openfsw_status_t osal_mutex_lock(osal_mutex_t mutex, uint32_t timeout_ms)
{
    if (!mutex) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    TickType_t ticks = (timeout_ms == OSAL_WAIT_FOREVER) ? portMAX_DELAY : pdMS_TO_TICKS(timeout_ms);
    
    if (xSemaphoreTake((SemaphoreHandle_t)mutex, ticks) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR_TIMEOUT;
}

openfsw_status_t osal_mutex_unlock(osal_mutex_t mutex)
{
    if (!mutex) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    if (xSemaphoreGive((SemaphoreHandle_t)mutex) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

/*===========================================================================*/
/* Semaphore API                                                             */
/*===========================================================================*/

openfsw_status_t osal_sem_create(osal_sem_t *sem, uint32_t initial, uint32_t max)
{
    if (!sem) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    int slot = -1;
    for (int i = 0; i < OSAL_MAX_SEMS; i++) {
        if (!sem_used[i]) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        return OPENFSW_ERROR_NO_MEMORY;
    }
    
    SemaphoreHandle_t handle = xSemaphoreCreateCountingStatic(max, initial, &sem_buffers[slot]);
    if (handle == NULL) {
        return OPENFSW_ERROR;
    }
    
    sem_used[slot] = 1;
    *sem = (osal_sem_t)handle;
    return OPENFSW_OK;
}

openfsw_status_t osal_sem_delete(osal_sem_t sem)
{
    if (!sem) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    vSemaphoreDelete((SemaphoreHandle_t)sem);
    return OPENFSW_OK;
}

openfsw_status_t osal_sem_take(osal_sem_t sem, uint32_t timeout_ms)
{
    if (!sem) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    TickType_t ticks = (timeout_ms == OSAL_WAIT_FOREVER) ? portMAX_DELAY : pdMS_TO_TICKS(timeout_ms);
    
    if (xSemaphoreTake((SemaphoreHandle_t)sem, ticks) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR_TIMEOUT;
}

openfsw_status_t osal_sem_give(osal_sem_t sem)
{
    if (!sem) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    if (xSemaphoreGive((SemaphoreHandle_t)sem) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

openfsw_status_t osal_sem_give_from_isr(osal_sem_t sem)
{
    if (!sem) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    BaseType_t higher_prio_woken = pdFALSE;
    if (xSemaphoreGiveFromISR((SemaphoreHandle_t)sem, &higher_prio_woken) == pdTRUE) {
        portYIELD_FROM_ISR(higher_prio_woken);
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

/*===========================================================================*/
/* Queue API                                                                 */
/*===========================================================================*/

openfsw_status_t osal_queue_create(osal_queue_t *queue, uint32_t length, uint32_t item_size)
{
    if (!queue || length == 0 || item_size == 0) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    int slot = -1;
    for (int i = 0; i < OSAL_MAX_QUEUES; i++) {
        if (!queue_used[i]) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        return OPENFSW_ERROR_NO_MEMORY;
    }
    
    if (length * item_size > sizeof(queue_storage[0])) {
        return OPENFSW_ERROR_NO_MEMORY;
    }
    
    QueueHandle_t handle = xQueueCreateStatic(length, item_size, queue_storage[slot], &queue_buffers[slot]);
    if (handle == NULL) {
        return OPENFSW_ERROR;
    }
    
    queue_used[slot] = 1;
    *queue = (osal_queue_t)handle;
    return OPENFSW_OK;
}

openfsw_status_t osal_queue_delete(osal_queue_t queue)
{
    if (!queue) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    vQueueDelete((QueueHandle_t)queue);
    return OPENFSW_OK;
}

openfsw_status_t osal_queue_send(osal_queue_t queue, const void *item, uint32_t timeout_ms)
{
    if (!queue || !item) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    TickType_t ticks = (timeout_ms == OSAL_WAIT_FOREVER) ? portMAX_DELAY : pdMS_TO_TICKS(timeout_ms);
    
    if (xQueueSend((QueueHandle_t)queue, item, ticks) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR_TIMEOUT;
}

openfsw_status_t osal_queue_receive(osal_queue_t queue, void *item, uint32_t timeout_ms)
{
    if (!queue || !item) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    TickType_t ticks = (timeout_ms == OSAL_WAIT_FOREVER) ? portMAX_DELAY : pdMS_TO_TICKS(timeout_ms);
    
    if (xQueueReceive((QueueHandle_t)queue, item, ticks) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR_TIMEOUT;
}

openfsw_status_t osal_queue_send_from_isr(osal_queue_t queue, const void *item)
{
    if (!queue || !item) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    BaseType_t higher_prio_woken = pdFALSE;
    if (xQueueSendFromISR((QueueHandle_t)queue, item, &higher_prio_woken) == pdTRUE) {
        portYIELD_FROM_ISR(higher_prio_woken);
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

uint32_t osal_queue_get_count(osal_queue_t queue)
{
    if (!queue) {
        return 0;
    }
    return (uint32_t)uxQueueMessagesWaiting((QueueHandle_t)queue);
}

/*===========================================================================*/
/* Timer API                                                                 */
/*===========================================================================*/

openfsw_status_t osal_timer_create(const osal_timer_config_t *config, osal_timer_t *timer)
{
    if (!config || !timer) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    int slot = -1;
    for (int i = 0; i < OSAL_MAX_TIMERS; i++) {
        if (!timer_used[i]) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        return OPENFSW_ERROR_NO_MEMORY;
    }
    
    TimerHandle_t handle = xTimerCreateStatic(
        config->name,
        pdMS_TO_TICKS(config->period_ms),
        config->auto_reload ? pdTRUE : pdFALSE,
        config->arg,
        (TimerCallbackFunction_t)config->callback,
        &timer_buffers[slot]
    );
    
    if (handle == NULL) {
        return OPENFSW_ERROR;
    }
    
    timer_used[slot] = 1;
    *timer = (osal_timer_t)handle;
    return OPENFSW_OK;
}

openfsw_status_t osal_timer_start(osal_timer_t timer)
{
    if (!timer) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    if (xTimerStart((TimerHandle_t)timer, 0) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

openfsw_status_t osal_timer_stop(osal_timer_t timer)
{
    if (!timer) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    if (xTimerStop((TimerHandle_t)timer, 0) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

openfsw_status_t osal_timer_reset(osal_timer_t timer)
{
    if (!timer) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    if (xTimerReset((TimerHandle_t)timer, 0) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

openfsw_status_t osal_timer_delete(osal_timer_t timer)
{
    if (!timer) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    if (xTimerDelete((TimerHandle_t)timer, 0) == pdTRUE) {
        return OPENFSW_OK;
    }
    return OPENFSW_ERROR;
}

/*===========================================================================*/
/* Time API                                                                  */
/*===========================================================================*/

uint32_t osal_get_tick_count(void)
{
    return (uint32_t)xTaskGetTickCount();
}

uint32_t osal_get_tick_rate_hz(void)
{
    return (uint32_t)configTICK_RATE_HZ;
}

ofsw_time_ms_t osal_get_time_ms(void)
{
    return (ofsw_time_ms_t)(xTaskGetTickCount() * 1000 / configTICK_RATE_HZ);
}

/*===========================================================================*/
/* Critical Section                                                          */
/*===========================================================================*/

void osal_enter_critical(void)
{
    taskENTER_CRITICAL();
}

void osal_exit_critical(void)
{
    taskEXIT_CRITICAL();
}

uint32_t osal_enter_critical_from_isr(void)
{
    return (uint32_t)taskENTER_CRITICAL_FROM_ISR();
}

void osal_exit_critical_from_isr(uint32_t state)
{
    taskEXIT_CRITICAL_FROM_ISR(state);
}
