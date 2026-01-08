#pragma once

#include "openfsw/boot.h"

void health_init(openfsw_boot_mode_t mode);

/* Called periodically from the scheduler task (runtime monitoring). */
void health_periodic(void);
