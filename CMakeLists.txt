cmake_minimum_required(VERSION 3.20)

project(OpenFSW C ASM)

include(CTest)

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
)
target_include_directories(freertos_kernel PUBLIC
  third_party/FreeRTOS-Kernel/include
  third_party/FreeRTOS-Kernel/portable/GCC/ARM_CM4F
  flight/rtos
)
target_compile_options(freertos_kernel PRIVATE -ffreestanding -fno-builtin -fdata-sections -ffunction-sections)

if(OPENFSW_CPU STREQUAL "cortex-m4" OR OPENFSW_CPU STREQUAL "cortex-m4f")
  set(OPENFSW_FPU_FLAGS -mfpu=fpv4-sp-d16 -mfloat-abi=hard)
  target_compile_options(freertos_kernel PRIVATE ${OPENFSW_FPU_FLAGS})
endif()

add_executable(openfsw.elf
  flight/boot/startup.S
  flight/boot/boot.c
  flight/core/system.c
  flight/core/health/health.c
  flight/core/scheduler/scheduler.c
  flight/rtos/rtos_freertos.c
  flight/rtos/freertos_hooks.c
  flight/rtos/port_compat.c
)

if(OPENFSW_BSP STREQUAL "stm32f4")
  target_sources(openfsw.elf PRIVATE flight/drivers/bsp_stm32f4.c)
else()
  target_sources(openfsw.elf PRIVATE flight/drivers/bsp_generic.c)
endif()

target_include_directories(openfsw.elf PRIVATE
  flight
  flight/core
  flight/core/health
  flight/core/scheduler
  flight/boot
  flight/drivers
  flight/rtos
  flight/comms
)

target_link_libraries(openfsw.elf PRIVATE freertos_kernel)

target_compile_options(openfsw.elf PRIVATE
  -ffreestanding
  -fno-builtin
  -fdata-sections
  -ffunction-sections
  -Wall -Wextra -Werror
)

if(OPENFSW_CPU STREQUAL "cortex-m4" OR OPENFSW_CPU STREQUAL "cortex-m4f")
  target_compile_options(openfsw.elf PRIVATE ${OPENFSW_FPU_FLAGS})
endif()

target_link_options(openfsw.elf PRIVATE
  -T${CMAKE_SOURCE_DIR}/linker/linker.ld
  -specs=nosys.specs
  -Wl,--gc-sections
  -Wl,-Map=${CMAKE_BINARY_DIR}/openfsw.map
)

if(OPENFSW_CPU STREQUAL "cortex-m4" OR OPENFSW_CPU STREQUAL "cortex-m4f")
  target_link_options(openfsw.elf PRIVATE ${OPENFSW_FPU_FLAGS})
endif()

if(BUILD_TESTING)
  find_package(Python3 COMPONENTS Interpreter REQUIRED)
  add_test(
    NAME pytest
    COMMAND ${Python3_EXECUTABLE} -m pytest -q --disable-warnings --maxfail=1 ${CMAKE_SOURCE_DIR}/tests
  )
  set_tests_properties(pytest PROPERTIES ENVIRONMENT "PYTHONPATH=${CMAKE_SOURCE_DIR}")
endif()
