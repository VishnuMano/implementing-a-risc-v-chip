#!/usr/bin/env python3
"""Export measured data and exact source excerpts for the static article."""
import csv
import hashlib
import html
import json
import pathlib
import re
import shutil
import subprocess
import sys

root = pathlib.Path(__file__).resolve().parent.parent
target = pathlib.Path(sys.argv[1])
target.mkdir(parents=True, exist_ok=True)
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
base = "https://github.com/VishnuMano/implementing-a-risc-v-chip"
def excerpt(path, start, end):
    return {"text": "\n".join((root/path).read_text().splitlines()[start-1:end]),
            "url": f"{base}/blob/{commit}/{path}#L{start}-L{end}"}
components = [
    {"id":"cpu", "name":"RISC-V CPU", "detail":"PicoRV32 executes RV32I instructions. It requests instruction and data transfers through one valid/ready bus. We reuse the CPU and write the surrounding SoC; the optional multiplier, divider, compressed instructions, and interrupt interface are disabled.", "code":excerpt("rtl/soc.v",20,36)},
    {"id":"rom", "name":"Program ROM", "detail":"The program starts at address zero. A generated case statement encodes the compiled firmware into gates. Unused ROM words return a NOP. This is fixed hardware, not a flash device that can be reprogrammed after fabrication.", "code":excerpt("rtl/boot_rom.v",1,14)},
    {"id":"ram", "name":"Working RAM", "detail":"256 words hold 1 KiB. Each write has four byte-enable bits. There is no assumed power-on initialization: startup clears BSS and the demo writes every sample before reading it. Standard cells implement this memory in the first layout.", "code":excerpt("rtl/soc.v",55,61)},
    {"id":"uart", "name":"UART transmitter", "detail":"A low-byte write to 0x20000000 starts an 8N1 frame: a start bit, eight data bits, and a stop bit. At a 10 MHz clock, the divider of 87 gives approximately 114,943 baud. Writes wait while the transmitter is busy.", "code":excerpt("rtl/uart_tx.v",15,30)},
    {"id":"gpio", "name":"GPIO output", "detail":"The low byte of 0x20000008 drives eight output pins. Firmware writes 0xA5 on success, or 0xEE on failure. Writes that do not enable byte lane zero leave it unchanged.", "code":excerpt("rtl/soc.v",68,72)},
    {"id":"timer", "name":"Timer", "detail":"A 32-bit counter advances once per clock and wraps modulo 2^32. Firmware reads it through 0x2000000C. This version polls the timer; it has no timer interrupt.", "code":excerpt("rtl/soc.v",41,49)},
]
baseline = json.loads((root/"results/baseline.json").read_text())
counts = []
for name, stats in baseline["synthesis"]["modules"].items():
    label = "CPU" if "picorv32" in name else "UART" if "uart_tx" in name else "ROM" if "boot_rom" in name else "RAM + bus + timer + GPIO"
    counts.append({"name":label, "value":stats["num_cells"] - stats.get("num_submodules",0)})
trace = list(csv.DictReader((root/"build/bus.csv").open()))
# Keep early fetches plus all data/MMIO activity. No invented cycles.
trace = [row for i,row in enumerate(trace) if i < 30 or int(row["address"],16) >= 0x10000000]
data = {"commit":commit, "repository":base, "components":components,
        "firmware":excerpt("firmware/main.c",19,38),
        "generic_cells":counts, "simulation":baseline["simulation"],
        "trace":trace, "physical":None}
if (root/"results/waveform.json").exists():
    data["waveform"] = json.loads((root/"results/waveform.json").read_text())
if (root/"results/experiments.json").exists():
    data["experiments"] = json.loads((root/"results/experiments.json").read_text())
    shutil.copy2(root/"results/experiments.json",target/"experiments.json")
if (root/"results/physical.json").exists():
    data["physical"] = json.loads((root/"results/physical.json").read_text())
    shutil.copy2(root/"results/physical.json",target/"physical.json")
    for image in (root/"results/images").glob("*.png"):
        shutil.copy2(image,target/image.name)
(target/"data.json").write_text(json.dumps(data,indent=2)+"\n")
article=target.parent/"implementing-a-risc-v-chip.html"
if article.exists():
    source=article.read_text()
    source=re.sub(r'(<pre id="firmware-code"><code>).*?(</code></pre>)',lambda m:m[1]+html.escape(data["firmware"]["text"])+m[2],source,flags=re.S)
    article.write_text(source)
shutil.copy2(root/"results/baseline.json",target/"generic-synthesis.json")
shutil.copy2(root/"build/uart.txt",target/"uart.txt")
shutil.copy2(root/"build/bus.csv",target/"bus.csv")
print(f"Exported article data for {commit[:12]} to {target}")
