# Firmware (flight-side)

The flight software lives under `flight/` and is built as a bare-metal ARM ELF (`openfsw.elf`).

## Build

Configure:

`cmake -S . -B build-arm -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake -G "Unix Makefiles"`

Build:

`cmake --build build-arm -j`

## Testing

CTest is used for orchestration:

`ctest --test-dir build-arm --output-on-failure`

Currently, the CTest test list includes a `pytest` test (host-side) to provide a single place to run validation. Bare-metal runtime tests are not executed on the host.

## Notes

- The linker script is in `linker/linker.ld`.
- FreeRTOS kernel sources are vendored in `third_party/FreeRTOS-Kernel/`.
- The build uses `-specs=nosys.specs`; syscall stubs are expected in typical bare-metal environments.
