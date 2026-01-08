#include "../scheduler.h"
#include "../config.h"
#include "../health.h"

typedef struct {
    openfsw_job_fn_t fn;
    uint32_t period_ms;
    uint32_t next_run_ms;
    bool used;
} sched_job_t;

static struct {
    uint32_t now_ms;
    sched_job_t jobs[OPENFSW_SCHED_MAX_JOBS];
} g_sched;

static void scheduler_reset(void)
{
    g_sched.now_ms = 0u;
    for (uint32_t i = 0; i < OPENFSW_SCHED_MAX_JOBS; i++) {
        g_sched.jobs[i].used = false;
        g_sched.jobs[i].fn = 0;
        g_sched.jobs[i].period_ms = 0u;
        g_sched.jobs[i].next_run_ms = 0u;
    }
}

void scheduler_init(system_mode_t mode)
{
    (void)mode;
    scheduler_reset();

    /* Built-in periodic job(s). Keep safe-mode minimal. */
    (void)scheduler_register_periodic(health_periodic, (mode == MODE_SAFE) ? 500u : 100u);
}

bool scheduler_register_periodic(openfsw_job_fn_t fn, uint32_t period_ms)
{
    if (fn == 0 || period_ms == 0u) {
        return false;
    }

    for (uint32_t i = 0; i < OPENFSW_SCHED_MAX_JOBS; i++) {
        if (!g_sched.jobs[i].used) {
            g_sched.jobs[i].used = true;
            g_sched.jobs[i].fn = fn;
            g_sched.jobs[i].period_ms = period_ms;
            g_sched.jobs[i].next_run_ms = g_sched.now_ms + period_ms;
            return true;
        }
    }

    return false;
}

/* Called from RTOS scheduler task each tick step. */
void scheduler_step(uint32_t elapsed_ms)
{
    g_sched.now_ms += elapsed_ms;

    for (uint32_t i = 0; i < OPENFSW_SCHED_MAX_JOBS; i++) {
        if (!g_sched.jobs[i].used) {
            continue;
        }

        if (g_sched.now_ms >= g_sched.jobs[i].next_run_ms) {
            g_sched.jobs[i].next_run_ms += g_sched.jobs[i].period_ms;
            g_sched.jobs[i].fn();
        }
    }
}
