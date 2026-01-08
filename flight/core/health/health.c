#include "openfsw/health.h"
#include "openfsw/bsp.h"
#include "openfsw/system.h"

typedef struct {
    uint32_t heartbeat;
} health_state_t;

static health_state_t g_health;

void health_init(openfsw_boot_mode_t mode)
{
    (void)mode;
    g_health.heartbeat = 0u;
}

void health_periodic(void)
{
    /* Minimal runtime health signal.
     * Keep it deterministic: no heap, no heavy logging.
     */
    g_health.heartbeat++;

    /* Feed watchdog from a known-good periodic loop. */
    bsp_watchdog_kick();

    const openfsw_system_context_t *ctx = openfsw_system_get_context();
    (void)ctx;
}
