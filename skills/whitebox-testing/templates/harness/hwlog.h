/**
 * @file  hwlog.h
 * @brief 硬件调用记录器: 测试用例通过它断言被测代码对外设的操作序列(如阀步进相序)。
 */
#ifndef __HWLOG_H__
#define __HWLOG_H__

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    HW_EV_GPIO_SET = 0,
    HW_EV_GPIO_RESET,
    HW_EV_GPIO_TOGGLE,
    HW_EV_USART_FUNC,     /* arg1 = 实例号, arg2 = USART_RX/TX, arg3 = ENABLE/DISABLE */
    HW_EV_UART_SEND,      /* arg1 = 实例号, arg2 = 长度, data = 内容拷贝 */
    HW_EV_IWDT_FEED,
    HW_EV_ADC_READ,       /* arg1 = 通道号 */
    HW_EV_FLASH_READ,     /* arg1 = 地址, arg2 = 长度 */
    HW_EV_FLASH_WRITE,    /* arg1 = 地址, arg2 = 长度 */
    HW_EV_MAX
} hw_ev_kind_t;

typedef struct {
    hw_ev_kind_t kind;
    uint32_t arg1;
    uint32_t arg2;
    uint32_t arg3;
    uint8_t  data[64];
    uint32_t data_len;
} hw_ev_t;

#define HWLOG_CAP 4096

void     hwlog_reset(void);
uint32_t hwlog_count(void);
const hw_ev_t *hwlog_at(uint32_t idx);
uint32_t hwlog_count_kind(hw_ev_kind_t kind);

/* ---- 可编程返回值(模拟外设) ---- */
extern uint16_t g_u16AdcValue;      /* ADC_ReadChannel_ADCx 返回值 */
extern uint8_t  g_u8AdcResult;      /* ADC_ReadChannel_ADCx 返回码(LL_OK/LL_ERR) */
extern int32_t  g_i32FlashWriteRc;  /* bsp_Dataflash_WriteData 返回码 */
extern int32_t  g_i32FlashReadRc;   /* bsp_Dataflash_ReadData 返回码 */

#ifdef __cplusplus
}
#endif

#endif /* __HWLOG_H__ */
