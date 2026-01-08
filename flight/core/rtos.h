#pragma once

#include "../boot/boot.h"

/* Start the RTOS after boot sequencing finishes.
 * Must not return.
 */
void rtos_start(system_mode_t mode);
