/**
 * @file ccsds.h
 * @brief CCSDS Space Packet Protocol Implementation
 */

#ifndef CCSDS_H
#define CCSDS_H

#include "../../core/openfsw.h"

/*===========================================================================*/
/* CCSDS Packet Definitions                                                  */
/*===========================================================================*/

/* Packet Version Number */
#define CCSDS_VERSION           0

/* Packet Type */
#define CCSDS_TYPE_TM           0   /* Telemetry */
#define CCSDS_TYPE_TC           1   /* Telecommand */

/* Secondary Header Flag */
#define CCSDS_SEC_HDR_ABSENT    0
#define CCSDS_SEC_HDR_PRESENT   1

/* Sequence Flags */
#define CCSDS_SEQ_CONTINUATION  0
#define CCSDS_SEQ_FIRST         1
#define CCSDS_SEQ_LAST          2
#define CCSDS_SEQ_STANDALONE    3

/* Maximum sizes */
#define CCSDS_MAX_PACKET_SIZE   4096
#define CCSDS_PRIMARY_HDR_SIZE  6
#define CCSDS_SEC_HDR_SIZE      10

/*===========================================================================*/
/* CCSDS Structures                                                          */
/*===========================================================================*/

/* Primary Header (6 bytes) */
typedef struct __attribute__((packed)) {
    uint16_t packet_id;      /* Version(3) + Type(1) + SecHdr(1) + APID(11) */
    uint16_t sequence_ctrl;  /* SeqFlags(2) + SeqCount(14) */
    uint16_t packet_length;  /* Data length - 1 */
} ccsds_primary_header_t;

/* Secondary Header for TM (10 bytes) */
typedef struct __attribute__((packed)) {
    uint32_t coarse_time;    /* Seconds since epoch */
    uint16_t fine_time;      /* Subseconds */
    uint8_t service_type;
    uint8_t service_subtype;
    uint8_t destination_id;
    uint8_t spare;
} ccsds_tm_secondary_header_t;

/* Secondary Header for TC (10 bytes) */
typedef struct __attribute__((packed)) {
    uint8_t service_type;
    uint8_t service_subtype;
    uint8_t source_id;
    uint8_t spare;
    uint32_t scheduled_time;
    uint16_t ack_flags;
} ccsds_tc_secondary_header_t;

/* Complete Telemetry Packet */
typedef struct {
    ccsds_primary_header_t primary;
    ccsds_tm_secondary_header_t secondary;
    uint8_t data[CCSDS_MAX_PACKET_SIZE - CCSDS_PRIMARY_HDR_SIZE - CCSDS_SEC_HDR_SIZE - 2];
    uint16_t crc;
    uint16_t data_length;
} ccsds_tm_packet_t;

/* Complete Telecommand Packet */
typedef struct {
    ccsds_primary_header_t primary;
    ccsds_tc_secondary_header_t secondary;
    uint8_t data[CCSDS_MAX_PACKET_SIZE - CCSDS_PRIMARY_HDR_SIZE - CCSDS_SEC_HDR_SIZE - 2];
    uint16_t crc;
    uint16_t data_length;
} ccsds_tc_packet_t;

/*===========================================================================*/
/* APID Definitions (Application Process ID)                                 */
/*===========================================================================*/
typedef enum {
    APID_IDLE = 0,
    APID_SYSTEM = 1,
    APID_HEALTH = 2,
    APID_POWER = 3,
    APID_ADCS = 4,
    APID_COMMS = 5,
    APID_PAYLOAD = 6,
    APID_TIME = 7,
    APID_FDIR = 8,
    APID_FILE = 9,
    APID_MAX = 2047
} ccsds_apid_t;

/*===========================================================================*/
/* PUS Service Types (ECSS-E-ST-70-41C)                                      */
/*===========================================================================*/
typedef enum {
    PUS_SVC_REQUEST_VERIFICATION = 1,
    PUS_SVC_DEVICE_ACCESS = 2,
    PUS_SVC_HOUSEKEEPING = 3,
    PUS_SVC_PARAMETER_STATS = 4,
    PUS_SVC_EVENT_REPORTING = 5,
    PUS_SVC_MEMORY_MGMT = 6,
    PUS_SVC_FUNCTION_MGMT = 8,
    PUS_SVC_TIME_MGMT = 9,
    PUS_SVC_SCHEDULING = 11,
    PUS_SVC_ONBOARD_MONITOR = 12,
    PUS_SVC_LARGE_DATA = 13,
    PUS_SVC_PACKET_FWD = 14,
    PUS_SVC_STORAGE_RETRIEVAL = 15,
    PUS_SVC_TEST = 17,
    PUS_SVC_ONBOARD_CTRL = 18,
    PUS_SVC_EVENT_ACTION = 19
} pus_service_t;

/*===========================================================================*/
/* API                                                                       */
/*===========================================================================*/

void ccsds_init(void);

/* Packet construction */
void ccsds_build_tm_header(ccsds_tm_packet_t *pkt, uint16_t apid, 
                            uint8_t service_type, uint8_t service_subtype);
void ccsds_build_tc_header(ccsds_tc_packet_t *pkt, uint16_t apid,
                            uint8_t service_type, uint8_t service_subtype);

/* Data handling */
openfsw_status_t ccsds_tm_set_data(ccsds_tm_packet_t *pkt, const uint8_t *data, uint16_t len);
openfsw_status_t ccsds_tc_get_data(const ccsds_tc_packet_t *pkt, uint8_t *data, uint16_t *len);

/* Finalization */
void ccsds_finalize_tm(ccsds_tm_packet_t *pkt);
uint16_t ccsds_tm_get_total_length(const ccsds_tm_packet_t *pkt);

/* Parsing */
openfsw_status_t ccsds_parse_tc(const uint8_t *raw, uint16_t len, ccsds_tc_packet_t *pkt);
bool ccsds_validate_tc(const ccsds_tc_packet_t *pkt);

/* Serialization */
uint16_t ccsds_serialize_tm(const ccsds_tm_packet_t *pkt, uint8_t *buffer, uint16_t max_len);

/* Utilities */
uint16_t ccsds_calc_crc(const uint8_t *data, uint16_t len);
uint16_t ccsds_get_apid(const ccsds_primary_header_t *hdr);
uint16_t ccsds_get_sequence(const ccsds_primary_header_t *hdr);
uint16_t ccsds_next_sequence(uint16_t apid);

#endif /* CCSDS_H */
