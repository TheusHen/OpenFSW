#pragma once

#include "openfsw/boot.h"

/* Start the RTOS after boot sequencing finishes.
 * Must not return.
 */
void rtos_start(openfsw_boot_mode_t mode);
