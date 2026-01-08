#include "../core/rtos.h"
#include "../drivers/bsp.h"
#include "../core/scheduler.h"
#include "../core/health.h"
#include "../core/time/time_manager.h"
#include "../core/logging/event_log.h"
#include "../core/logging/logger.h"
#include "../core/health/health_monitor.h"
#include "../core/mode/mode_manager.h"
#include "../eps/eps.h"
#include "../comms/telecommand.h"
#include "../comms/telemetry.h"
#include "../comms/beacon/beacon.h"

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
    /* Core services (safe to initialize before scheduler starts).
     * Keep init order deterministic.
     */
    event_log_init();
    logger_init();
    time_manager_init();
    health_monitor_init();
    mode_manager_init(mode);
    eps_init();
    telecommand_init();
    telemetry_init();
    beacon_init();

    health_init(mode);
    scheduler_init(mode);

    /* Periodic background services (driven by the OpenFSW scheduler task). */
    (void)scheduler_register_periodic(mode_manager_process, 200u);
    (void)scheduler_register_periodic(health_monitor_periodic, 200u);
    (void)scheduler_register_periodic(eps_periodic, 1000u);
    (void)scheduler_register_periodic(telecommand_periodic, 50u);
    (void)scheduler_register_periodic(telemetry_periodic, 200u);
    (void)scheduler_register_periodic(beacon_periodic, 1000u);

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
