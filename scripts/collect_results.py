"""Publish measured results; generic synthesis is not PDK cell mapping."""
import csv
import json
import pathlib
import subprocess
root = pathlib.Path(__file__).resolve().parent.parent
stats = json.loads((root / "build/synthesis.json").read_text())
trace = list(csv.DictReader((root / "build/bus.csv").open())) if (root / "build/bus.csv").exists() else []
result = {
    "schema_version": 1,
    "stage": "generic_synthesis",
    "technology_mapped": False,
    "yosys_version": subprocess.check_output(["yosys", "-V"], text=True).strip(),
    "synthesis": stats,
    "simulation": {"uart_transcript": (root / "build/uart.txt").read_text() if (root / "build/uart.txt").exists() else None,
                   "bus_transactions": len(trace)},
}
(root / "results/baseline.json").write_text(json.dumps(result, indent=2) + "\n")
print("Exported measured generic-synthesis results to results/baseline.json")
