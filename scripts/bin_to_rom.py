#!/usr/bin/env python3
"""Bake firmware into a combinational ROM case statement (no $readmemh)."""
import pathlib
import sys
binary = pathlib.Path(sys.argv[1]).read_bytes()
if len(binary) > 4096:
    raise SystemExit("Firmware exceeds 4 KiB ROM")
binary += bytes((-len(binary)) % 4)
lines = ["// Generated from firmware; regenerate with make firmware.",
         "`default_nettype none", "module boot_rom(input wire [9:0] addr, output reg [31:0] data);",
         "always @* begin", "    case (addr)"]
for offset in range(0, len(binary), 4):
    word = int.from_bytes(binary[offset:offset+4], "little")
    lines.append(f"        10'd{offset//4}: data = 32'h{word:08x};")
lines += ["        default: data = 32'h00000013; // NOP", "    endcase", "end", "endmodule", "`default_nettype wire", ""]
pathlib.Path(sys.argv[2]).write_text("\n".join(lines))
print(f"ROM: {len(binary)} / 4096 bytes")
