"""Run the firmware smoke test on a saved SKY130 mapped netlist, without SDF."""
import argparse
import json
import pathlib
import subprocess
parser=argparse.ArgumentParser()
parser.add_argument("run",type=pathlib.Path)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent
run=args.run.resolve()
config=json.loads((run/"resolved.json").read_text())
states=sorted(run.glob("[0-9]*-*/state_out.json"))
state=json.loads(states[-1].read_text())
netlist=state["nl"]
subprocess.run(["iverilog","-g2012","-DFUNCTIONAL","-DUNIT_DELAY=","-DGATE_TEST","-DPNR_TEST","-s","tb_soc","-o","build/tb_pnr"]+config["CELL_VERILOG_MODELS"]+[netlist,"tests/tb_soc.v"],cwd=root,check=True)
with (root/"build/pnr-test.log").open("w") as log:
    subprocess.run(["vvp","build/tb_pnr"],cwd=root,stdout=log,stderr=subprocess.STDOUT,check=True)
print((root/"build/pnr-test.log").read_text())
result={"run":run.name,"netlist":str(pathlib.Path(netlist).relative_to(root)),"passed":True,"sdf_annotated":False,"transcript":(root/"build/pnr_uart.txt").read_text()}
(root/"results/mapped-test.json").write_text(json.dumps(result,indent=2)+"\n")
