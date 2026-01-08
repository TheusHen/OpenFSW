#pragma once

#include "openfsw/boot.h"

void scheduler_init(openfsw_boot_mode_t mode);

typedef void (*openfsw_job_fn_t)(void);

/* Register a periodic job (milliseconds). Returns false if table full. */
bool scheduler_register_periodic(openfsw_job_fn_t fn, uint32_t period_ms);

/* Drive the scheduler forward by elapsed milliseconds (called from RTOS task). */
void scheduler_step(uint32_t elapsed_ms);
