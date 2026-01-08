#pragma once

#include "openfsw/boot.h"

typedef struct {
    openfsw_boot_mode_t mode;
    openfsw_reset_cause_t reset_cause;
} openfsw_system_context_t;

void openfsw_system_set_context(openfsw_boot_mode_t mode, openfsw_reset_cause_t reset_cause);
const openfsw_system_context_t *openfsw_system_get_context(void);
