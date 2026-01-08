/**
 * @file startup.S
 * @brief ARM Cortex-M startup code and vector table
 * 
 * OpenFSW-LEO-3U Boot Sequence (Assembly)
 */

.syntax unified
.cpu cortex-m4
.fpu fpv4-sp-d16
.thumb

/*===========================================================================*/
/* Vector Table                                                              */
/*===========================================================================*/
.section .isr_vector,"a",%progbits
.global __isr_vector
.type __isr_vector, %object

__isr_vector:
    .word _estack                   /* 0x00: Initial Stack Pointer */
    .word Reset_Handler             /* 0x04: Reset Handler */
    .word NMI_Handler               /* 0x08: NMI Handler */
    .word HardFault_Handler         /* 0x0C: Hard Fault Handler */
    .word MemManage_Handler         /* 0x10: MPU Fault Handler */
    .word BusFault_Handler          /* 0x14: Bus Fault Handler */
    .word UsageFault_Handler        /* 0x18: Usage Fault Handler */
    .word 0                         /* 0x1C: Reserved */
    .word 0                         /* 0x20: Reserved */
    .word 0                         /* 0x24: Reserved */
    .word 0                         /* 0x28: Reserved */
    .word vPortSVCHandler           /* 0x2C: SVCall Handler (FreeRTOS) */
    .word DebugMon_Handler          /* 0x30: Debug Monitor Handler */
    .word 0                         /* 0x34: Reserved */
    .word xPortPendSVHandler        /* 0x38: PendSV Handler (FreeRTOS) */
    .word xPortSysTickHandler       /* 0x3C: SysTick Handler (FreeRTOS) */
    
    /* External Interrupts */
    .word WWDG_IRQHandler           /* Window Watchdog */
    .word PVD_IRQHandler            /* PVD through EXTI */
    .word TAMP_STAMP_IRQHandler     /* Tamper and TimeStamp */
    .word RTC_WKUP_IRQHandler       /* RTC Wakeup */
    .word FLASH_IRQHandler          /* Flash */
    .word RCC_IRQHandler            /* RCC */
    .word EXTI0_IRQHandler          /* EXTI Line 0 */
    .word EXTI1_IRQHandler          /* EXTI Line 1 */
    .word EXTI2_IRQHandler          /* EXTI Line 2 */
    .word EXTI3_IRQHandler          /* EXTI Line 3 */
    .word EXTI4_IRQHandler          /* EXTI Line 4 */
    .word DMA1_Stream0_IRQHandler   /* DMA1 Stream 0 */
    .word DMA1_Stream1_IRQHandler   /* DMA1 Stream 1 */
    .word DMA1_Stream2_IRQHandler   /* DMA1 Stream 2 */
    .word DMA1_Stream3_IRQHandler   /* DMA1 Stream 3 */
    .word DMA1_Stream4_IRQHandler   /* DMA1 Stream 4 */
    .word DMA1_Stream5_IRQHandler   /* DMA1 Stream 5 */
    .word DMA1_Stream6_IRQHandler   /* DMA1 Stream 6 */
    .word ADC_IRQHandler            /* ADC1/2/3 */
    .word CAN1_TX_IRQHandler        /* CAN1 TX */
    .word CAN1_RX0_IRQHandler       /* CAN1 RX0 */
    .word CAN1_RX1_IRQHandler       /* CAN1 RX1 */
    .word CAN1_SCE_IRQHandler       /* CAN1 SCE */
    .word EXTI9_5_IRQHandler        /* EXTI Lines 5-9 */
    .word TIM1_BRK_TIM9_IRQHandler  /* TIM1 Break / TIM9 */
    .word TIM1_UP_TIM10_IRQHandler  /* TIM1 Update / TIM10 */
    .word TIM1_TRG_COM_TIM11_IRQHandler /* TIM1 Trigger / TIM11 */
    .word TIM1_CC_IRQHandler        /* TIM1 Capture Compare */
    .word TIM2_IRQHandler           /* TIM2 */
    .word TIM3_IRQHandler           /* TIM3 */
    .word TIM4_IRQHandler           /* TIM4 */
    .word I2C1_EV_IRQHandler        /* I2C1 Event */
    .word I2C1_ER_IRQHandler        /* I2C1 Error */
    .word I2C2_EV_IRQHandler        /* I2C2 Event */
    .word I2C2_ER_IRQHandler        /* I2C2 Error */
    .word SPI1_IRQHandler           /* SPI1 */
    .word SPI2_IRQHandler           /* SPI2 */
    .word USART1_IRQHandler         /* USART1 */
    .word USART2_IRQHandler         /* USART2 */
    .word USART3_IRQHandler         /* USART3 */
    .word EXTI15_10_IRQHandler      /* EXTI Lines 10-15 */
    .word RTC_Alarm_IRQHandler      /* RTC Alarm */
    .word OTG_FS_WKUP_IRQHandler    /* USB OTG FS Wakeup */
    
    /* Fill remaining vectors */
    .rept 200
        .word Default_Handler
    .endr

.size __isr_vector, . - __isr_vector

/*===========================================================================*/
/* Reset Handler                                                             */
/*===========================================================================*/
.section .text.Reset_Handler,"ax",%progbits
.global Reset_Handler
.type Reset_Handler, %function

Reset_Handler:
    /* Disable interrupts */
    cpsid i
    
    /* Initialize stack pointer explicitly */
    ldr r0, =_estack
    msr msp, r0
    isb
    
    /* Enable FPU (Cortex-M4F) */
    ldr r0, =0xE000ED88
    ldr r1, [r0]
    orr r1, r1, #(0xF << 20)
    str r1, [r0]
    dsb
    isb
    
    /* Clear FPU context */
    mov r0, #0
    vmov s0, r0
    vmov s1, r0
    vmov s2, r0
    vmov s3, r0
    
    /* Jump to C boot code */
    bl boot_main
    
    /* Should never return, but trap if it does */
1:
    wfi
    b 1b

.size Reset_Handler, . - Reset_Handler

/*===========================================================================*/
/* Default Handler                                                           */
/*===========================================================================*/
.section .text.Default_Handler,"ax",%progbits
.global Default_Handler
.type Default_Handler, %function

Default_Handler:
2:
    bkpt #0
    b 2b

.size Default_Handler, . - Default_Handler

/*===========================================================================*/
/* Fault Handlers with Debug Info                                            */
/*===========================================================================*/
.section .text.HardFault_Handler,"ax",%progbits
.global HardFault_Handler
.type HardFault_Handler, %function

HardFault_Handler:
    /* Save context for debugging */
    tst lr, #4
    ite eq
    mrseq r0, msp
    mrsne r0, psp
    
    /* Store fault info */
    ldr r1, =fault_info
    stm r1, {r0-r3}
    
    /* Hang */
3:
    bkpt #1
    b 3b

.size HardFault_Handler, . - HardFault_Handler

/*===========================================================================*/
/* Weak Aliases for Exception Handlers                                       */
/*===========================================================================*/
.weak NMI_Handler
.thumb_set NMI_Handler, Default_Handler

.weak MemManage_Handler
.thumb_set MemManage_Handler, Default_Handler

.weak BusFault_Handler
.thumb_set BusFault_Handler, Default_Handler

.weak UsageFault_Handler
.thumb_set UsageFault_Handler, Default_Handler

.weak DebugMon_Handler
.thumb_set DebugMon_Handler, Default_Handler

/* FreeRTOS handlers (weak, overridden by port) */
.weak vPortSVCHandler
.thumb_set vPortSVCHandler, Default_Handler

.weak xPortPendSVHandler
.thumb_set xPortPendSVHandler, Default_Handler

.weak xPortSysTickHandler
.thumb_set xPortSysTickHandler, Default_Handler

/* Peripheral IRQ handlers */
.weak WWDG_IRQHandler
.thumb_set WWDG_IRQHandler, Default_Handler

.weak PVD_IRQHandler
.thumb_set PVD_IRQHandler, Default_Handler

.weak TAMP_STAMP_IRQHandler
.thumb_set TAMP_STAMP_IRQHandler, Default_Handler

.weak RTC_WKUP_IRQHandler
.thumb_set RTC_WKUP_IRQHandler, Default_Handler

.weak FLASH_IRQHandler
.thumb_set FLASH_IRQHandler, Default_Handler

.weak RCC_IRQHandler
.thumb_set RCC_IRQHandler, Default_Handler

.weak EXTI0_IRQHandler
.thumb_set EXTI0_IRQHandler, Default_Handler

.weak EXTI1_IRQHandler
.thumb_set EXTI1_IRQHandler, Default_Handler

.weak EXTI2_IRQHandler
.thumb_set EXTI2_IRQHandler, Default_Handler

.weak EXTI3_IRQHandler
.thumb_set EXTI3_IRQHandler, Default_Handler

.weak EXTI4_IRQHandler
.thumb_set EXTI4_IRQHandler, Default_Handler

.weak DMA1_Stream0_IRQHandler
.thumb_set DMA1_Stream0_IRQHandler, Default_Handler

.weak DMA1_Stream1_IRQHandler
.thumb_set DMA1_Stream1_IRQHandler, Default_Handler

.weak DMA1_Stream2_IRQHandler
.thumb_set DMA1_Stream2_IRQHandler, Default_Handler

.weak DMA1_Stream3_IRQHandler
.thumb_set DMA1_Stream3_IRQHandler, Default_Handler

.weak DMA1_Stream4_IRQHandler
.thumb_set DMA1_Stream4_IRQHandler, Default_Handler

.weak DMA1_Stream5_IRQHandler
.thumb_set DMA1_Stream5_IRQHandler, Default_Handler

.weak DMA1_Stream6_IRQHandler
.thumb_set DMA1_Stream6_IRQHandler, Default_Handler

.weak ADC_IRQHandler
.thumb_set ADC_IRQHandler, Default_Handler

.weak CAN1_TX_IRQHandler
.thumb_set CAN1_TX_IRQHandler, Default_Handler

.weak CAN1_RX0_IRQHandler
.thumb_set CAN1_RX0_IRQHandler, Default_Handler

.weak CAN1_RX1_IRQHandler
.thumb_set CAN1_RX1_IRQHandler, Default_Handler

.weak CAN1_SCE_IRQHandler
.thumb_set CAN1_SCE_IRQHandler, Default_Handler

.weak EXTI9_5_IRQHandler
.thumb_set EXTI9_5_IRQHandler, Default_Handler

.weak TIM1_BRK_TIM9_IRQHandler
.thumb_set TIM1_BRK_TIM9_IRQHandler, Default_Handler

.weak TIM1_UP_TIM10_IRQHandler
.thumb_set TIM1_UP_TIM10_IRQHandler, Default_Handler

.weak TIM1_TRG_COM_TIM11_IRQHandler
.thumb_set TIM1_TRG_COM_TIM11_IRQHandler, Default_Handler

.weak TIM1_CC_IRQHandler
.thumb_set TIM1_CC_IRQHandler, Default_Handler

.weak TIM2_IRQHandler
.thumb_set TIM2_IRQHandler, Default_Handler

.weak TIM3_IRQHandler
.thumb_set TIM3_IRQHandler, Default_Handler

.weak TIM4_IRQHandler
.thumb_set TIM4_IRQHandler, Default_Handler

.weak I2C1_EV_IRQHandler
.thumb_set I2C1_EV_IRQHandler, Default_Handler

.weak I2C1_ER_IRQHandler
.thumb_set I2C1_ER_IRQHandler, Default_Handler

.weak I2C2_EV_IRQHandler
.thumb_set I2C2_EV_IRQHandler, Default_Handler

.weak I2C2_ER_IRQHandler
.thumb_set I2C2_ER_IRQHandler, Default_Handler

.weak SPI1_IRQHandler
.thumb_set SPI1_IRQHandler, Default_Handler

.weak SPI2_IRQHandler
.thumb_set SPI2_IRQHandler, Default_Handler

.weak USART1_IRQHandler
.thumb_set USART1_IRQHandler, Default_Handler

.weak USART2_IRQHandler
.thumb_set USART2_IRQHandler, Default_Handler

.weak USART3_IRQHandler
.thumb_set USART3_IRQHandler, Default_Handler

.weak EXTI15_10_IRQHandler
.thumb_set EXTI15_10_IRQHandler, Default_Handler

.weak RTC_Alarm_IRQHandler
.thumb_set RTC_Alarm_IRQHandler, Default_Handler

.weak OTG_FS_WKUP_IRQHandler
.thumb_set OTG_FS_WKUP_IRQHandler, Default_Handler

/*===========================================================================*/
/* Fault Info Storage                                                        */
/*===========================================================================*/
.section .bss.fault_info,"aw",%nobits
.global fault_info
fault_info:
    .space 16
