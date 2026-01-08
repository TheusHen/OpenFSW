#include "FreeRTOS.h"
#include "task.h"

/* Static allocation for Idle task (required when dynamic alloc disabled). */
static StaticTask_t idle_tcb;
static StackType_t idle_stack[configMINIMAL_STACK_SIZE];

#if (configUSE_TIMERS == 1)
static StaticTask_t timer_tcb;
static StackType_t timer_stack[configTIMER_TASK_STACK_DEPTH];
#endif

void vApplicationGetIdleTaskMemory(StaticTask_t **ppxIdleTaskTCBBuffer,
                                  StackType_t **ppxIdleTaskStackBuffer,
                                  uint32_t *pulIdleTaskStackSize)
{
    *ppxIdleTaskTCBBuffer = &idle_tcb;
    *ppxIdleTaskStackBuffer = idle_stack;
    *pulIdleTaskStackSize = (uint32_t)configMINIMAL_STACK_SIZE;
}

#if (configUSE_TIMERS == 1)
void vApplicationGetTimerTaskMemory(StaticTask_t **ppxTimerTaskTCBBuffer,
                                    StackType_t **ppxTimerTaskStackBuffer,
                                    uint32_t *pulTimerTaskStackSize)
{
    *ppxTimerTaskTCBBuffer = &timer_tcb;
    *ppxTimerTaskStackBuffer = timer_stack;
    *pulTimerTaskStackSize = (uint32_t)configTIMER_TASK_STACK_DEPTH;
}
#endif

void vApplicationStackOverflowHook(TaskHandle_t xTask, char *pcTaskName)
{
    (void)xTask;
    (void)pcTaskName;
    taskDISABLE_INTERRUPTS();
    for (;;) {
    }
}
