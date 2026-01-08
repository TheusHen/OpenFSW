#ifndef OPENFSW_SYSTEM_H
#define OPENFSW_SYSTEM_H

#include "openfsw.h"

typedef struct {
    system_mode_t mode;
    reset_cause_t reset_cause;
} openfsw_system_context_t;

void openfsw_system_set_context(system_mode_t mode, reset_cause_t reset_cause);
const openfsw_system_context_t *openfsw_system_get_context(void);

#endif /* OPENFSW_SYSTEM_H */
