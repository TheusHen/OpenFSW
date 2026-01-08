/* Cortex-M startup: vector table + Reset_Handler
 * Note: keeps boot minimal; no heavy logging; no heap.
 */

.syntax unified
.cpu cortex-m4
.thumb

.section .isr_vector,"a",%progbits
.global __isr_vector
.type __isr_vector, %object

__isr_vector:
  .word _estack
  .word Reset_Handler
  .word NMI_Handler
  .word HardFault_Handler
  .word MemManage_Handler
  .word BusFault_Handler
  .word UsageFault_Handler
  .word 0
  .word 0
  .word 0
  .word 0
  .word vPortSVCHandler
  .word DebugMon_Handler
  .word 0
  .word xPortPendSVHandler
  .word xPortSysTickHandler

  /* External interrupts (weak default, size kept generic) */
  .rept 240
    .word Default_Handler
  .endr

.size __isr_vector, . - __isr_vector

.section .text.Reset_Handler,"ax",%progbits
.global Reset_Handler
.type Reset_Handler, %function

Reset_Handler:
  /* Initialize stack (MSP) explicitly */
  ldr   r0, =_estack
  msr   msp, r0
  isb

  /* Jump to C boot. */
  bl    boot_main

  /* If boot_main returns, trap. */
1:
  b     1b

.size Reset_Handler, . - Reset_Handler

/* Default exception handlers */
.section .text.Default_Handler,"ax",%progbits
.global Default_Handler
.type Default_Handler, %function
Default_Handler:
2:
  b 2b
.size Default_Handler, . - Default_Handler

/* Weak aliases for core exception handlers */
.weak NMI_Handler
.thumb_set NMI_Handler, Default_Handler
.weak HardFault_Handler
.thumb_set HardFault_Handler, Default_Handler
.weak MemManage_Handler
.thumb_set MemManage_Handler, Default_Handler
.weak BusFault_Handler
.thumb_set BusFault_Handler, Default_Handler
.weak UsageFault_Handler
.thumb_set UsageFault_Handler, Default_Handler
.weak SVC_Handler
.thumb_set SVC_Handler, Default_Handler
.weak DebugMon_Handler
.thumb_set DebugMon_Handler, Default_Handler
.weak PendSV_Handler
.thumb_set PendSV_Handler, Default_Handler
.weak SysTick_Handler
.thumb_set SysTick_Handler, Default_Handler
