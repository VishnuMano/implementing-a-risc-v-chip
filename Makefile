CC_PREFIX ?= riscv64-elf-
PYTHON ?= python3
RUN_TAG ?= baseline
SOURCES = third_party/picorv32/picorv32.v rtl/boot_rom.v rtl/uart_tx.v rtl/soc.v
CFLAGS = -march=rv32i -mabi=ilp32 -Os -ffreestanding -fno-builtin -fno-pic -msmall-data-limit=0 -Wall -Wextra
.PHONY: all firmware test test-bus test-gate synth physical clean
all: test test-gate
build:
	mkdir -p build
build/firmware.elf: firmware/start.S firmware/main.c firmware/link.ld | build
	$(CC_PREFIX)gcc $(CFLAGS) -nostdlib -Wl,--build-id=none,-T,firmware/link.ld firmware/start.S firmware/main.c -o $@
build/firmware.bin: build/firmware.elf
	$(CC_PREFIX)objcopy -O binary $< $@
rtl/boot_rom.v: build/firmware.bin scripts/bin_to_rom.py
	$(PYTHON) scripts/bin_to_rom.py $< $@
firmware: rtl/boot_rom.v
	$(CC_PREFIX)objdump -d build/firmware.elf > build/firmware.dis
build/tb_soc: $(SOURCES) tests/tb_soc.v | build
	iverilog -g2012 -s tb_soc -o $@ $(SOURCES) tests/tb_soc.v
test: firmware build/tb_soc test-bus
	vvp build/tb_soc > build/system-test.log
	cat build/system-test.log
build/tb_bus: $(SOURCES) tests/tb_bus.v | build
	iverilog -g2012 -s tb_bus -o $@ $(SOURCES) tests/tb_bus.v
test-bus: build/tb_bus
	vvp build/tb_bus > build/bus-test.log
	cat build/bus-test.log
test-gate: synth
	iverilog -g2012 -DGATE_TEST -s tb_soc -o build/tb_gate build/soc_generic.v tests/tb_soc.v
	vvp build/tb_gate > build/gate-test.log
	cat build/gate-test.log
	$(PYTHON) scripts/collect_results.py
synth: firmware
	yosys -Q -T -l build/synthesis.log scripts/synth.ys
	$(PYTHON) scripts/collect_results.py
physical: firmware
	$(PYTHON) scripts/run_flow.py --tag $(RUN_TAG)
clean:
	rm -rf build
