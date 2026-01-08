/* Minimal linker script for Cortex-M (adjust MEMORY for your target). */

ENTRY(Reset_Handler)

MEMORY
{
  FLASH (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 256K
}

_estack = ORIGIN(RAM) + LENGTH(RAM);

SECTIONS
{
  .isr_vector :
  {
    KEEP(*(.isr_vector))
  } > FLASH

  .text :
  {
    *(.text*)
    *(.rodata*)
    *(.glue_7)
    *(.glue_7t)
    *(.eh_frame*)
    . = ALIGN(4);
  } > FLASH

  /* .data in RAM, load from FLASH */
  __data_load__ = LOADADDR(.data);
  .data :
  {
    __data_start__ = .;
    *(.data*)
    . = ALIGN(4);
    __data_end__ = .;
  } > RAM AT > FLASH

  .bss :
  {
    __bss_start__ = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    __bss_end__ = .;
  } > RAM

  /* Optional: keep stack/heap sections out (we avoid heap). */
  . = ALIGN(8);

  /DISCARD/ :
  {
    *(.note*)
    *(.comment*)
  }
}
