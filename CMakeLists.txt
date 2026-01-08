cmake_minimum_required(VERSION 3.20)

project(OpenFSW C ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(OPENFSW_BSP "stm32f4" CACHE STRING "BSP selection: stm32f4 or generic")

add_library(freertos_kernel STATIC)
target_sources(freertos_kernel PRIVATE
  third_party/FreeRTOS-Kernel/list.c
  third_party/FreeRTOS-Kernel/queue.c
  third_party/FreeRTOS-Kernel/tasks.c
  third_party/FreeRTOS-Kernel/timers.c
  third_party/FreeRTOS-Kernel/event_groups.c
  third_party/FreeRTOS-Kernel/stream_buffer.c
  third_party/FreeRTOS-Kernel/portable/GCC/ARM_CM4F/port.c
  third_party/FreeRTOS-Kernel/portable/GCC/ARM_CM4F/portASM.S
)
target_include_directories(freertos_kernel PUBLIC
  third_party/FreeRTOS-Kernel/include
  third_party/FreeRTOS-Kernel/portable/GCC/ARM_CM4F
  src/rtos/freertos
)
target_compile_options(freertos_kernel PRIVATE -ffreestanding -fno-builtin -fdata-sections -ffunction-sections)

add_executable(openfsw.elf
  src/boot/startup_arm_cm.S
  src/boot/boot.c
  src/boot/system.c
  src/health/health.c
  src/scheduler/scheduler.c
  src/rtos/rtos_freertos.c
  src/rtos/freertos/freertos_hooks.c
)

if(OPENFSW_BSP STREQUAL "stm32f4")
  target_sources(openfsw.elf PRIVATE src/bsp/stm32f4/bsp_stm32f4.c)
else()
  target_sources(openfsw.elf PRIVATE src/bsp/bsp_generic.c)
endif()

target_include_directories(openfsw.elf PRIVATE include)

target_link_libraries(openfsw.elf PRIVATE freertos_kernel)

target_compile_options(openfsw.elf PRIVATE
  -ffreestanding
  -fno-builtin
  -fdata-sections
  -ffunction-sections
  -Wall -Wextra -Werror
)

target_link_options(openfsw.elf PRIVATE
  -T${CMAKE_SOURCE_DIR}/linker/linker.ld
  -nostdlib
  -Wl,--gc-sections
  -Wl,-Map=${CMAKE_BINARY_DIR}/openfsw.map
)
