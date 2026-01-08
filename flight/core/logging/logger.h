/**
 * @file logger.h
 * @brief Byte ring-buffer logger
 */

#ifndef OPENFSW_LOGGER_H
#define OPENFSW_LOGGER_H

#include "../openfsw.h"

void logger_init(void);

/* Append bytes to the ring buffer (drops oldest on overflow). */
void logger_write_bytes(const uint8_t *data, uint32_t len);
void logger_write_str(const char *str);

/* Export up to max_len bytes (oldest-first). Returns bytes copied. */
uint32_t logger_export(uint8_t *out, uint32_t max_len);

/* Optional: flush the current buffer to the debug UART backend. */
void logger_flush_debug(void);

#endif
