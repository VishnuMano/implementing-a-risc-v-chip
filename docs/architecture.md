# Architecture

One external clock, active-low synchronous reset, no internally generated clocks.
Reset must be asserted for at least two clock edges. External reset release must
be synchronized by a future chip wrapper. Current outputs: UART TX, 8-bit GPIO,
and the CPU trap flag. The core is RV32I-configured PicoRV32, with its optional
interrupt, compressed instruction, multiply, and divide features disabled.

| Byte address | Function | Access |
| --- | --- | --- |
| `0x00000000–0x00000fff` | 4 KiB fixed program ROM | Read; writes ignored |
| `0x10000000–0x100003ff` | 1 KiB RAM | Read/write, byte enables |
| `0x20000000` | UART data | Low-byte writes transmit |
| `0x20000004` | UART status | Read bit 0: busy |
| `0x20000008` | GPIO output | Read/write low byte |
| `0x2000000c` | Free-running timer | Read, modulo 2^32 |
| Other addresses | Unmapped | Read `0xdeadbeef`, writes ignored |

The CPU makes aligned bus requests and supplies byte lane strobes for subword
stores. The bus acknowledges a request once; it waits for the prior ready pulse
to clear before accepting another. UART data writes stall while busy. GPIO and
UART writes require byte lane zero. MMIO addresses are exact aligned addresses.

At 10 MHz the UART divides the clock by 87, for about 114,943 baud (8N1).
The timer is polled; this design makes no privileged-architecture or interrupt
compatibility claim. Firmware uses the RV32I/ILP32 bare-metal ABI, without libc.

The entire 1 KiB RAM maps to standard-cell storage in the initial implementation.
This intentionally shows memory's area cost. SRAM macros, pads, ESD, package
connections, test structures, fabrication, and board bring-up are future scope.
