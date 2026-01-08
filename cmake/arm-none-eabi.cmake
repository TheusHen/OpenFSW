# Toolchain file for ARM bare-metal builds.
# Usage:
#   cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake

set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)

set(TOOLCHAIN_PREFIX arm-none-eabi)

find_program(CMAKE_C_COMPILER   ${TOOLCHAIN_PREFIX}-gcc)
find_program(CMAKE_ASM_COMPILER ${TOOLCHAIN_PREFIX}-gcc)
find_program(CMAKE_OBJCOPY      ${TOOLCHAIN_PREFIX}-objcopy)
find_program(CMAKE_SIZE         ${TOOLCHAIN_PREFIX}-size)

if(NOT CMAKE_C_COMPILER)
  message(FATAL_ERROR "arm-none-eabi-gcc not found in PATH")
endif()

# Default CPU: Cortex-M4 (common in smallsat OBCs). Adjust as needed.
set(OPENFSW_CPU cortex-m4 CACHE STRING "Target CPU (e.g., cortex-m0, cortex-m3, cortex-m4, cortex-m7)")

add_compile_options(
  -mcpu=${OPENFSW_CPU}
  -mthumb
  -g3
  -Os
)

add_link_options(
  -mcpu=${OPENFSW_CPU}
  -mthumb
)
