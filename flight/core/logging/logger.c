/**
 * @file logger.c
 * @brief Byte ring-buffer logger implementation
 */

#include "logger.h"
#include "../../osal/osal.h"
#include "../../drivers/bsp.h"
#include <string.h>

static struct {
    uint8_t buf[OPENFSW_LOG_BUFFER_SIZE];
    uint32_t head;
    uint32_t tail;
    uint32_t count;
    osal_mutex_t mutex;
    bool initialized;
} g_log;

void logger_init(void)
{
    osal_mutex_create(&g_log.mutex);
    memset(g_log.buf, 0, sizeof(g_log.buf));
    g_log.head = 0u;
    g_log.tail = 0u;
    g_log.count = 0u;
    g_log.initialized = true;
}

static void logger_push_byte(uint8_t b)
{
    if (g_log.count == OPENFSW_LOG_BUFFER_SIZE) {
        /* Drop oldest */
        g_log.tail = (g_log.tail + 1u) % OPENFSW_LOG_BUFFER_SIZE;
        g_log.count--;
    }

    g_log.buf[g_log.head] = b;
    g_log.head = (g_log.head + 1u) % OPENFSW_LOG_BUFFER_SIZE;
    g_log.count++;
}

void logger_write_bytes(const uint8_t *data, uint32_t len)
{
    if (!g_log.initialized) return;
    if (!data || len == 0u) return;

    osal_mutex_lock(g_log.mutex, OSAL_WAIT_FOREVER);
    for (uint32_t i = 0; i < len; i++) {
        logger_push_byte(data[i]);
    }
    osal_mutex_unlock(g_log.mutex);
}

void logger_write_str(const char *str)
{
    if (!str) return;
    logger_write_bytes((const uint8_t *)str, (uint32_t)strlen(str));
}

uint32_t logger_export(uint8_t *out, uint32_t max_len)
{
    if (!g_log.initialized) return 0u;
    if (!out || max_len == 0u) return 0u;

    uint32_t copied = 0u;
    osal_mutex_lock(g_log.mutex, OSAL_WAIT_FOREVER);

    while (copied < max_len && g_log.count > 0u) {
        out[copied++] = g_log.buf[g_log.tail];
        g_log.tail = (g_log.tail + 1u) % OPENFSW_LOG_BUFFER_SIZE;
        g_log.count--;
    }

    osal_mutex_unlock(g_log.mutex);
    return copied;
}

void logger_flush_debug(void)
{
    if (!g_log.initialized) return;

    uint8_t tmp[128];
    for (;;) {
        uint32_t n = logger_export(tmp, (uint32_t)sizeof(tmp));
        if (n == 0u) break;
        for (uint32_t i = 0; i < n; i++) {
            bsp_debug_putchar((char)tmp[i]);
        }
    }
}
