#include "system.h"

static openfsw_system_context_t g_ctx;

void openfsw_system_set_context(system_mode_t mode, reset_cause_t reset_cause)
{
    g_ctx.mode = mode;
    g_ctx.reset_cause = reset_cause;
}

const openfsw_system_context_t *openfsw_system_get_context(void)
{
    return &g_ctx;
}
