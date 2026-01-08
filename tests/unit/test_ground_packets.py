import struct

from ground.telecommand.packet_encoder import CCSDSEncoder, TCPacketConfig
from ground.telemetry.packet_decoder import CCSDSDecoder, CCSDSPacketType


def test_tc_packet_roundtrip_primary_header_and_crc_valid():
    enc = CCSDSEncoder(TCPacketConfig(apid=100))
    pkt = enc.encode_packet(service_type=17, service_subtype=1, data=b"")

    dec = CCSDSDecoder(expected_apid=100)
    decoded = dec.decode_packet(pkt)
    assert decoded is not None

    assert decoded.primary_header.apid == 100
    assert decoded.primary_header.packet_type == CCSDSPacketType.TELECOMMAND
    assert decoded.crc_valid is True


def test_tm_packet_decodes_pus_secondary_header_and_crc_valid():
    # Build a minimal TM packet with a 10-byte PUS secondary header
    apid = 100
    version = 0
    packet_type = 0  # TM
    sec_hdr_flag = 1

    # Primary header fields
    word1 = (version << 13) | (packet_type << 12) | (sec_hdr_flag << 11) | (apid & 0x7FF)
    word2 = (3 << 14) | 1  # seq flags + seq count

    pus0 = (1 << 4) | 0  # PUS version in high nibble
    service = 3
    subtype = 25
    dest_id = 0
    time_s = 123456789
    time_sub = 0
    pus = struct.pack(">BBBBIH", pus0, service, subtype, dest_id, time_s, time_sub)
    user = b"\x00\x01\x02\x03"

    # packet_data_length = (len(data_field) - 1) where data_field includes sec hdr + user + crc
    data_field_wo_crc = pus + user
    packet_data_length = len(data_field_wo_crc) + 2 - 1
    word3 = packet_data_length

    primary = struct.pack(">HHH", word1, word2, word3)

    # CRC is CRC-16 CCITT of all bytes except the CRC itself
    dec = CCSDSDecoder(expected_apid=apid)
    crc = dec._calculate_crc(primary + data_field_wo_crc)  # type: ignore[attr-defined]

    pkt = primary + data_field_wo_crc + struct.pack(">H", crc)

    decoded = dec.decode_packet(pkt)
    assert decoded is not None
    assert decoded.primary_header.packet_type == CCSDSPacketType.TELEMETRY
    assert decoded.crc_valid is True
    assert decoded.secondary_header is not None
    assert decoded.secondary_header.service_type == service
    assert decoded.secondary_header.service_subtype == subtype
    assert decoded.secondary_header.time_seconds == time_s
    assert decoded.data == user
