# Ground segment

The ground segment lives under `ground/` and provides:

- CCSDS/PUS packet decoding for telemetry (TM)
- CCSDS/PUS packet encoding for telecommands (TC)
- A simple command scheduler
- A lightweight housekeeping archive example

## Run the example

`PYTHONPATH=. python3 -m ground.examples.ground_example`

The example prints:
- Telecommand packets (hex)
- Telemetry decoding of a sample TM packet
- Scheduler execution results
- Housekeeping archive statistics

## Key modules

- `ground/telecommand/packet_encoder.py` — builds CCSDS primary + PUS TC secondary header and CRC
- `ground/telecommand/command_builder.py` — higher-level command building
- `ground/telecommand/command_scheduler.py` — scheduled execution
- `ground/telemetry/packet_decoder.py` — CCSDS primary + PUS TM secondary header decoding + CRC
- `ground/telemetry/telemetry_processor.py` — processing hook pattern

## Testing

Pytest unit tests are under `tests/unit/` and include basic TM/TC encode/decode + CRC checks.
