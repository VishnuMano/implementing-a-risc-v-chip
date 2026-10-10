# Implementing A RISC-V Chip

An interactive journey from RTL to GDS using open-source tools.

This project integrates an existing PicoRV32 processor with a fixed-program ROM,
1 KiB of RAM, a UART transmitter, GPIO, and a timer. We write and verify the SoC
integration and take it through synthesis and physical implementation. The target
is a SKY130 SoC core layout, without a pad ring or fabricated silicon.

## Reproduce simulation and generic synthesis

Required: GNU make, Python 3, Icarus Verilog, Yosys, and a RISC-V bare-metal GCC
toolchain that accepts `-march=rv32i -mabi=ilp32`.

On Apple Silicon with Homebrew:

```sh
brew install icarus-verilog yosys riscv64-elf-gcc
make test synth
```

On Linux, use your distribution's packages and override the compiler prefix:

```sh
make CC_PREFIX=riscv64-unknown-elf- test synth
```

The generated `rtl/boot_rom.v` contains actual ROM logic. RAM has no assumed
power-on contents; startup clears BSS. Initialized `.data` is rejected by the
linker until a ROM-to-RAM copy routine is provided.

Tests exercise byte writes, address boundaries, immutable ROM, UART stalling,
reset during UART transmission, timer progression, and the complete firmware.
The system test decodes the serial pin and expects:

```text
Hello from RTL!
checksum=0x00002040
PASS
```

Generated artifacts: `build/soc.vcd`, `build/bus.csv`, `build/firmware.dis`,
`build/soc_generic.v`, `build/synthesis.log`, and `results/baseline.json`.
Generic synthesis statistics are not SKY130 cell area or timing results.

## Physical flow

Use a Python 3.12 virtual environment, Docker, and LibreLane:

```sh
python3 -m venv .venv
.venv/bin/pip install -r flow/requirements.txt
.venv/bin/python -m librelane --dockerized --pdk-root "$PWD/build/pdk" --smoke-test
make PYTHON=.venv/bin/python physical
```

On macOS, Docker can run in Colima. Provision enough RAM and disk for the PDK and
flow. Run the smoke test before hardening this SoC. Initial timing target: 100 ns
(10 MHz). Physical results and check status will be published only after the
actual flow completes.

## Provenance

CPU: [YosysHQ/PicoRV32](https://github.com/YosysHQ/picorv32), pinned unmodified to
`ef203c2b0a3fb793280f5114941416c425c5b461`. Upstream is archived. Its verification
is distinct from this project's SoC integration tests; no exhaustive ISA
verification claim is made.

See [architecture](docs/architecture.md) for interfaces and design decisions.
