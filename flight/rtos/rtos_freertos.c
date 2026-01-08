#include "../core/rtos.h"
#include "../drivers/bsp.h"
#include "../core/scheduler.h"
#include "../core/health.h"

#include "FreeRTOS.h"
#include "task.h"

/* One task runs the OpenFSW scheduler loop (fixed-table jobs). */
static StaticTask_t sched_tcb;
static StackType_t sched_stack[512];

static void openfsw_scheduler_task(void *arg)
{
    (void)arg;

    TickType_t last_wake = xTaskGetTickCount();

    for (;;) {
        /* 1ms tick expected. If you change configTICK_RATE_HZ, update this. */
        vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(10));

        /* Drive jobs. */
        scheduler_step(10);

        /* Extra safety: ensure watchdog gets kicked even if no job runs. */
        bsp_watchdog_kick();
    }
}

__attribute__((noreturn)) void rtos_start(system_mode_t mode)
{
    health_init(mode);
    scheduler_init(mode);

    /* Create scheduler task using static allocation (no heap). */
    (void)xTaskCreateStatic(openfsw_scheduler_task,
                            "sched",
                            (uint32_t)(sizeof(sched_stack) / sizeof(sched_stack[0])),
                            0,
                            (UBaseType_t)2,
                            sched_stack,
                            &sched_tcb);

    vTaskStartScheduler();

    /* Should never reach here. */
    taskDISABLE_INTERRUPTS();
    for (;;) {
    }
}
