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
make test test-gate
```

On Linux, use your distribution's packages and override the compiler prefix:

```sh
make CC_PREFIX=riscv64-unknown-elf- test test-gate
```

The generated `rtl/boot_rom.v` contains actual ROM logic. RAM has no assumed
power-on contents; startup clears BSS. Initialized `.data` is rejected by the
linker until a ROM-to-RAM copy routine is provided.

Tests exercise byte writes, address boundaries, immutable ROM, UART stalling,
reset during UART transmission, timer progression, and the complete firmware.
The same firmware test also runs on the generic synthesized netlist. This is
a functional smoke test, not a proof of RTL/netlist equivalence or a test of
extracted physical timing.
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
.venv/bin/python -m librelane --docker-no-tty --dockerized --pdk-root "$PWD/build/pdk" --condensed --smoke-test
make PYTHON=.venv/bin/python physical
```

On macOS, Docker can run in Colima. Provision enough RAM and disk for the PDK and
flow. Run the smoke test before hardening this SoC. Initial timing target: 100 ns
(10 MHz). Physical results and check status will be published only after the
actual flow completes. Runtime results describe this machine and should not be
treated as a universal requirement.

## Article datasets

After a run, export actual states and simulation traces:

```sh
python3 scripts/export_waveform.py
.venv/bin/python scripts/export_physical.py flow/runs/baseline --completed
python3 scripts/export_experiments.py
python3 scripts/export_article_data.py /path/to/vishnumano.com/builds/risc-v
```

Use `--completed` only after a successful full flow. The export preserves raw
metrics and source-state paths. The default run tag differs when `make physical`
is used; substitute its directory. The clock experiments stop at pre-placement
STA; they are not three fully routed chips:

```sh
.venv/bin/python -m librelane --docker-no-tty --dockerized --pdk-root "$PWD/build/pdk" --condensed -j 4 --run-tag clock-50 -c CLOCK_PERIOD=50 --to OpenROAD.STAPrePNR flow/config.json
.venv/bin/python -m librelane --docker-no-tty --dockerized --pdk-root "$PWD/build/pdk" --condensed -j 4 --run-tag clock-20 -c CLOCK_PERIOD=20 --to OpenROAD.STAPrePNR flow/config.json
```

## Provenance

CPU: [YosysHQ/PicoRV32](https://github.com/YosysHQ/picorv32), pinned unmodified to
`ef203c2b0a3fb793280f5114941416c425c5b461`. Upstream is archived. Its verification
is distinct from this project's SoC integration tests; no exhaustive ISA
verification claim is made.

See [architecture](docs/architecture.md) for interfaces and design decisions.
