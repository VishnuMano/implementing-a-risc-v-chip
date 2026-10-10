#include <stdint.h>
#define REG(addr) (*(volatile uint32_t *)(addr))
#define UART_DATA REG(0x20000000u)
#define UART_BUSY REG(0x20000004u)
#define GPIO REG(0x20000008u)
#define TIMER REG(0x2000000cu)
static volatile uint32_t samples[32];
static void putc_uart(char c) {
    while (UART_BUSY & 1u) {}
    UART_DATA = (uint8_t)c;
}
static void puts_uart(const char *s) { while (*s) putc_uart(*s++); }
static void hex(uint32_t n) {
    for (int shift = 28; shift >= 0; shift -= 4)
        putc_uart("0123456789ABCDEF"[(n >> shift) & 15u]);
}
int main(void) {
    uint32_t before = TIMER;
    uint32_t checksum = 0;
    // Volatile RAM accesses ensure the demo really exercises physical storage.
    for (uint32_t i = 0; i < 32; ++i) samples[i] = (i << 4) ^ 0x5au;
    for (uint32_t i = 0; i < 32; ++i) checksum += samples[i];
    if (checksum != 0x2040u || TIMER == before) {
        GPIO = 0xeeu;
        puts_uart("FAIL\n");
    } else {
        GPIO = 0xa5u;
        puts_uart("Hello from RTL!\nchecksum=0x");
        hex(checksum);
        puts_uart("\nPASS\n");
    }
    return 0;
}
