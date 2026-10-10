#!/usr/bin/env python3
"""Export snapshots and metrics from one actual LibreLane run (requires pya)."""
import argparse
import fnmatch
import hashlib
import json
import pathlib
import subprocess
import time
import pya

parser=argparse.ArgumentParser()
parser.add_argument("run",type=pathlib.Path)
parser.add_argument("--completed",action="store_true")
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent
run=args.run.resolve()
config=json.loads((run/"resolved.json").read_text())
images=root/"results/images"
images.mkdir(exist_ok=True)
tech=pya.Technology()
tech.load(config["KLAYOUT_TECH"])
lefs=[v for k,v in config["TECH_LEFS"].items() if fnmatch.fnmatch(config["DEFAULT_CORNER"],k)] + config["CELL_LEFS"]

def render(source,output):
    if output.exists() and output.stat().st_mtime>=source.stat().st_mtime:return
    view=pya.LayoutView()
    view.set_config("background-color","#101511")
    view.set_config("grid-visible","false")
    view.set_config("text-visible","false")
    if source.suffix==".gds":view.load_layout(str(source))
    else:
        options=tech.load_layout_options
        options.lefdef_config.map_file=config["KLAYOUT_DEF_LAYER_MAP"]
        options.lefdef_config.macro_resolution_mode=1
        options.lefdef_config.read_lef_with_def=False
        options.lefdef_config.lef_files=lefs
        view.load_layout(str(source),options,config["KLAYOUT_TECH"])
    view.max_hier()
    view.load_layer_props(config["KLAYOUT_PROPERTIES"])
    view.zoom_fit()
    bbox=view.active_cellview().layout().top_cell().dbbox()
    view.save_image_with_options(str(output),1800,int(1800*bbox.height()/bbox.width()),oversampling=1)
    view.destroy()
    print("Rendered",output.name,flush=True)

specs=[
 ("Synthesis","12-openroad-staprepnr","No coordinates yet: mapped library cells and pre-placement timing estimates."),
 ("Floorplan","23-odb-addroutingobstructions","Core rows, physical support cells, and power distribution before signal placement."),
 ("Placement","31-openroad-stamidpnr","Cells have coordinates. This timing snapshot precedes subsequent repair and clock-tree synthesis."),
 ("Clock tree","38-openroad-stamidpnr-2","Clock buffers and timing-repair cells have been inserted. Hold repair has run; signal routing is still ahead."),
 ("Global routing","43-openroad-stamidpnr-3","Signal routes are planned and estimated parasitics updated. These are routing guides, before detailed legal track assignment."),
]
stages=[]
for name,dirname,description in specs:
    folder=run/dirname
    statefile=folder/"state_out.json"
    if not statefile.exists():continue
    state=json.loads(statefile.read_text())
    metrics=state["metrics"]
    image=None
    source=pathlib.Path(state["def"]) if state.get("def") else None
    if source:
        image=dirname.split("-",1)[0]+"-"+name.lower().replace(" ","-")+".png"
        render(source,images/image)
    stages.append({"name":name,"description":description,"image":image,
                   "area":metrics.get("design__instance__area"),
                   "cells":metrics.get("design__instance__count"),
                   "slack":None if name=="Floorplan" else metrics.get("timing__setup__ws"),
                   "corner":config["DEFAULT_CORNER"] if name not in ["Synthesis","Floorplan"] else "pre-placement multicorner" if name=="Synthesis" else None,
                   "source_state":str(statefile.relative_to(root)),"metrics":metrics})
states=sorted(run.glob("[0-9]*-*/state_out.json"))
latest=json.loads(states[-1].read_text())
gds=latest.get("gds")
if gds:
    render(pathlib.Path(gds),images/"final-gds.png")
    m=latest["metrics"]
    stages.append({"name":"Final GDS","description":"GDS geometry, including standard-cell internals and routed interconnect. Final metrics come from the latest completed step.","image":"final-gds.png","area":m.get("design__instance__area"),"cells":m.get("design__instance__count"),"slack":m.get("timing__setup__ws"),"corner":"aggregate of final STA corners","source_state":str(states[-1].relative_to(root)),"metrics":m})
m=latest["metrics"]
check_keys=[("Magic DRC violations","magic__drc_error__count",""),
            ("KLayout DRC violations","klayout__drc_error__count",""),
            ("LVS errors","design__lvs_error__count",""),
            ("Antenna-violating nets","design__antenna_violation__count",""),
            ("Setup violations","timing__setup_vio__count",""),
            ("Hold violations","timing__hold_vio__count",""),
            ("Worst setup slack","timing__setup__ws","ns"),
            ("Worst hold slack","timing__hold__ws","ns"),
            ("Unconstrained endpoints","timing__unconstrained__count",""),
            ("Lint warnings (reviewed separately)","design__lint_warning__count","")]
checks=[{"name":name,"value":m.get(key),"unit":unit,"key":key} for name,key,unit in check_keys]
result={"completed":args.completed,"run":"baseline","librelane":"3.0.16",
        "source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
        "pdk_revision":"8afc8346a57fe1ab7934ba5a6056ea8b43078e71",
        "docker_digest":"sha256:02d50f259d483979e126ef188a50f5b61e1d285b9d538312f280b087439b0302",
        "clock_period_ns":config["CLOCK_PERIOD"],"default_corner":config["DEFAULT_CORNER"],
        "sta_corners":config.get("STA_CORNERS"),"stages":stages,"checks":checks,"final_metrics":m}
def seconds(value):
    h,m,s=value.split(":")
    return int(h)*3600+int(m)*60+float(s)
result["runtime"]=[]
for folder in sorted(run.glob("[0-9]*-*")):
    processes=list(folder.glob("*.process_stats.json"))
    if not processes:continue
    stats=[json.loads(p.read_text()) for p in processes]
    result["runtime"].append({"stage":folder.name,"seconds":sum(seconds(s["time"]["runtime"]) for s in stats),
                              "peak_rss": [s["peak_resources"]["memory_rss"] for s in stats]})
if gds:result["gds_sha256"]=hashlib.sha256(pathlib.Path(gds).read_bytes()).hexdigest()
(root/"results/physical.json").write_text(json.dumps(result,indent=2)+"\n")
print("Exported physical metrics",flush=True)
