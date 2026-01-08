#pragma once

#include "../boot/boot.h"

void health_init(system_mode_t mode);

/* Called periodically from the scheduler task (runtime monitoring). */
void health_periodic(void);
