ENTRY(_start)
MEMORY {
    ROM (rx) : ORIGIN = 0x00000000, LENGTH = 4K
    RAM (rw) : ORIGIN = 0x10000000, LENGTH = 1K
}
SECTIONS {
    .text : { *(.text.start) *(.text*) *(.rodata*) } > ROM
    .data : { *(.data*) *(.sdata*) } > RAM
    .bss (NOLOAD) : {
        . = ALIGN(4); _bss_start = .;
        *(.bss*) *(.sbss*) *(COMMON)
        . = ALIGN(4); _bss_end = .;
    } > RAM
    _stack_top = ORIGIN(RAM) + LENGTH(RAM);
    ASSERT(SIZEOF(.data) == 0, "Initialized RAM data requires a ROM copy routine")
    ASSERT(_bss_end <= _stack_top - 256, "Reserve at least 256 bytes for stack")
}
