/**
 * @file ccsds.c
 * @brief CCSDS Space Packet Protocol Implementation
 */

#include "ccsds.h"
#include "../../osal/osal.h"
#include "../../core/time/time_manager.h"
#include <string.h>

/*===========================================================================*/
/* State                                                                     */
/*===========================================================================*/
static struct {
    uint16_t sequence_counts[APID_MAX + 1];
    osal_mutex_t mutex;
    bool initialized;
} g_ccsds;

/*===========================================================================*/
/* CRC-16 CCITT                                                              */
/*===========================================================================*/
static const uint16_t crc_table[256] = {
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
    0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
    0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
    0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
    0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
    0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
    0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
    0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
    0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
    0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
    0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
    0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
    0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
    0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
    0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
    0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
    0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
    0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
    0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
    0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
    0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
    0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
    0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0
};

/*===========================================================================*/
/* Public Functions                                                          */
/*===========================================================================*/

void ccsds_init(void)
{
    osal_mutex_create(&g_ccsds.mutex);
    memset(g_ccsds.sequence_counts, 0, sizeof(g_ccsds.sequence_counts));
    g_ccsds.initialized = true;
}

uint16_t ccsds_calc_crc(const uint8_t *data, uint16_t len)
{
    uint16_t crc = 0xFFFF;
    
    for (uint16_t i = 0; i < len; i++) {
        crc = (crc << 8) ^ crc_table[((crc >> 8) ^ data[i]) & 0xFF];
    }
    
    return crc;
}

uint16_t ccsds_next_sequence(uint16_t apid)
{
    if (apid > APID_MAX) {
        return 0;
    }
    
    osal_mutex_lock(g_ccsds.mutex, OSAL_WAIT_FOREVER);
    uint16_t seq = g_ccsds.sequence_counts[apid];
    g_ccsds.sequence_counts[apid] = (seq + 1) & 0x3FFF;
    osal_mutex_unlock(g_ccsds.mutex);
    
    return seq;
}

uint16_t ccsds_get_apid(const ccsds_primary_header_t *hdr)
{
    return hdr->packet_id & 0x07FF;
}

uint16_t ccsds_get_sequence(const ccsds_primary_header_t *hdr)
{
    return hdr->sequence_ctrl & 0x3FFF;
}

void ccsds_build_tm_header(ccsds_tm_packet_t *pkt, uint16_t apid,
                            uint8_t service_type, uint8_t service_subtype)
{
    if (!pkt) return;
    
    memset(pkt, 0, sizeof(*pkt));
    
    /* Primary header */
    pkt->primary.packet_id = (CCSDS_VERSION << 13) | 
                              (CCSDS_TYPE_TM << 12) | 
                              (CCSDS_SEC_HDR_PRESENT << 11) | 
                              (apid & 0x07FF);
    
    pkt->primary.sequence_ctrl = (CCSDS_SEQ_STANDALONE << 14) | 
                                  ccsds_next_sequence(apid);
    
    /* Secondary header */
    ofsw_timestamp_t ts;
    time_get_timestamp(&ts);
    pkt->secondary.coarse_time = ts.seconds;
    pkt->secondary.fine_time = (uint16_t)(ts.subseconds & 0xFFFF);
    pkt->secondary.service_type = service_type;
    pkt->secondary.service_subtype = service_subtype;
    pkt->secondary.destination_id = 0;
    pkt->secondary.spare = 0;
    
    pkt->data_length = 0;
}

void ccsds_build_tc_header(ccsds_tc_packet_t *pkt, uint16_t apid,
                            uint8_t service_type, uint8_t service_subtype)
{
    if (!pkt) return;
    
    memset(pkt, 0, sizeof(*pkt));
    
    pkt->primary.packet_id = (CCSDS_VERSION << 13) | 
                              (CCSDS_TYPE_TC << 12) | 
                              (CCSDS_SEC_HDR_PRESENT << 11) | 
                              (apid & 0x07FF);
    
    pkt->primary.sequence_ctrl = (CCSDS_SEQ_STANDALONE << 14);
    
    pkt->secondary.service_type = service_type;
    pkt->secondary.service_subtype = service_subtype;
    pkt->secondary.source_id = 0;
    pkt->secondary.spare = 0;
    pkt->secondary.scheduled_time = 0;
    pkt->secondary.ack_flags = 0;
    
    pkt->data_length = 0;
}

openfsw_status_t ccsds_tm_set_data(ccsds_tm_packet_t *pkt, const uint8_t *data, uint16_t len)
{
    if (!pkt || !data) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    uint16_t max_len = sizeof(pkt->data);
    if (len > max_len) {
        return OPENFSW_ERROR_OVERFLOW;
    }
    
    memcpy(pkt->data, data, len);
    pkt->data_length = len;
    
    return OPENFSW_OK;
}

void ccsds_finalize_tm(ccsds_tm_packet_t *pkt)
{
    if (!pkt) return;
    
    /* Calculate total data length (secondary header + data + CRC - 1) */
    uint16_t total = CCSDS_SEC_HDR_SIZE + pkt->data_length + 2 - 1;
    pkt->primary.packet_length = total;
    
    /* Calculate CRC over entire packet except CRC field itself */
    uint8_t temp[CCSDS_MAX_PACKET_SIZE];
    uint16_t offset = 0;
    
    memcpy(&temp[offset], &pkt->primary, CCSDS_PRIMARY_HDR_SIZE);
    offset += CCSDS_PRIMARY_HDR_SIZE;
    
    memcpy(&temp[offset], &pkt->secondary, CCSDS_SEC_HDR_SIZE);
    offset += CCSDS_SEC_HDR_SIZE;
    
    memcpy(&temp[offset], pkt->data, pkt->data_length);
    offset += pkt->data_length;
    
    pkt->crc = ccsds_calc_crc(temp, offset);
}

uint16_t ccsds_tm_get_total_length(const ccsds_tm_packet_t *pkt)
{
    if (!pkt) return 0;
    return CCSDS_PRIMARY_HDR_SIZE + CCSDS_SEC_HDR_SIZE + pkt->data_length + 2;
}

uint16_t ccsds_serialize_tm(const ccsds_tm_packet_t *pkt, uint8_t *buffer, uint16_t max_len)
{
    if (!pkt || !buffer) return 0;
    
    uint16_t total = ccsds_tm_get_total_length(pkt);
    if (total > max_len) return 0;
    
    uint16_t offset = 0;
    
    /* Primary header (big-endian) */
    buffer[offset++] = (pkt->primary.packet_id >> 8) & 0xFF;
    buffer[offset++] = pkt->primary.packet_id & 0xFF;
    buffer[offset++] = (pkt->primary.sequence_ctrl >> 8) & 0xFF;
    buffer[offset++] = pkt->primary.sequence_ctrl & 0xFF;
    buffer[offset++] = (pkt->primary.packet_length >> 8) & 0xFF;
    buffer[offset++] = pkt->primary.packet_length & 0xFF;
    
    /* Secondary header */
    buffer[offset++] = (pkt->secondary.coarse_time >> 24) & 0xFF;
    buffer[offset++] = (pkt->secondary.coarse_time >> 16) & 0xFF;
    buffer[offset++] = (pkt->secondary.coarse_time >> 8) & 0xFF;
    buffer[offset++] = pkt->secondary.coarse_time & 0xFF;
    buffer[offset++] = (pkt->secondary.fine_time >> 8) & 0xFF;
    buffer[offset++] = pkt->secondary.fine_time & 0xFF;
    buffer[offset++] = pkt->secondary.service_type;
    buffer[offset++] = pkt->secondary.service_subtype;
    buffer[offset++] = pkt->secondary.destination_id;
    buffer[offset++] = pkt->secondary.spare;
    
    /* Data */
    memcpy(&buffer[offset], pkt->data, pkt->data_length);
    offset += pkt->data_length;
    
    /* CRC */
    buffer[offset++] = (pkt->crc >> 8) & 0xFF;
    buffer[offset++] = pkt->crc & 0xFF;
    
    return offset;
}

openfsw_status_t ccsds_parse_tc(const uint8_t *raw, uint16_t len, ccsds_tc_packet_t *pkt)
{
    if (!raw || !pkt || len < CCSDS_PRIMARY_HDR_SIZE + CCSDS_SEC_HDR_SIZE + 2) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    memset(pkt, 0, sizeof(*pkt));
    
    uint16_t offset = 0;
    
    /* Parse primary header */
    pkt->primary.packet_id = ((uint16_t)raw[offset] << 8) | raw[offset + 1];
    offset += 2;
    pkt->primary.sequence_ctrl = ((uint16_t)raw[offset] << 8) | raw[offset + 1];
    offset += 2;
    pkt->primary.packet_length = ((uint16_t)raw[offset] << 8) | raw[offset + 1];
    offset += 2;
    
    /* Parse secondary header */
    pkt->secondary.service_type = raw[offset++];
    pkt->secondary.service_subtype = raw[offset++];
    pkt->secondary.source_id = raw[offset++];
    pkt->secondary.spare = raw[offset++];
    pkt->secondary.scheduled_time = ((uint32_t)raw[offset] << 24) | 
                                     ((uint32_t)raw[offset + 1] << 16) |
                                     ((uint32_t)raw[offset + 2] << 8) | 
                                     raw[offset + 3];
    offset += 4;
    pkt->secondary.ack_flags = ((uint16_t)raw[offset] << 8) | raw[offset + 1];
    offset += 2;
    
    /* Parse data */
    uint16_t data_len = pkt->primary.packet_length + 1 - CCSDS_SEC_HDR_SIZE - 2;
    if (data_len > sizeof(pkt->data)) {
        return OPENFSW_ERROR_OVERFLOW;
    }
    
    memcpy(pkt->data, &raw[offset], data_len);
    pkt->data_length = data_len;
    offset += data_len;
    
    /* Parse CRC */
    pkt->crc = ((uint16_t)raw[offset] << 8) | raw[offset + 1];
    
    return OPENFSW_OK;
}

bool ccsds_validate_tc(const ccsds_tc_packet_t *pkt)
{
    if (!pkt) return false;
    
    /* Check version */
    if ((pkt->primary.packet_id >> 13) != CCSDS_VERSION) {
        return false;
    }
    
    /* Check type */
    if (((pkt->primary.packet_id >> 12) & 0x01) != CCSDS_TYPE_TC) {
        return false;
    }
    
    /* Verify CRC */
    uint8_t temp[CCSDS_MAX_PACKET_SIZE];
    uint16_t offset = 0;
    
    temp[offset++] = (pkt->primary.packet_id >> 8) & 0xFF;
    temp[offset++] = pkt->primary.packet_id & 0xFF;
    temp[offset++] = (pkt->primary.sequence_ctrl >> 8) & 0xFF;
    temp[offset++] = pkt->primary.sequence_ctrl & 0xFF;
    temp[offset++] = (pkt->primary.packet_length >> 8) & 0xFF;
    temp[offset++] = pkt->primary.packet_length & 0xFF;
    
    temp[offset++] = pkt->secondary.service_type;
    temp[offset++] = pkt->secondary.service_subtype;
    temp[offset++] = pkt->secondary.source_id;
    temp[offset++] = pkt->secondary.spare;
    temp[offset++] = (pkt->secondary.scheduled_time >> 24) & 0xFF;
    temp[offset++] = (pkt->secondary.scheduled_time >> 16) & 0xFF;
    temp[offset++] = (pkt->secondary.scheduled_time >> 8) & 0xFF;
    temp[offset++] = pkt->secondary.scheduled_time & 0xFF;
    temp[offset++] = (pkt->secondary.ack_flags >> 8) & 0xFF;
    temp[offset++] = pkt->secondary.ack_flags & 0xFF;
    
    memcpy(&temp[offset], pkt->data, pkt->data_length);
    offset += pkt->data_length;
    
    uint16_t calc_crc = ccsds_calc_crc(temp, offset);
    
    return (calc_crc == pkt->crc);
}

openfsw_status_t ccsds_tc_get_data(const ccsds_tc_packet_t *pkt, uint8_t *data, uint16_t *len)
{
    if (!pkt || !data || !len) {
        return OPENFSW_ERROR_INVALID_PARAM;
    }
    
    memcpy(data, pkt->data, pkt->data_length);
    *len = pkt->data_length;
    
    return OPENFSW_OK;
}
