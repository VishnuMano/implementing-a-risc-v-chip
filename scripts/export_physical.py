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
parser.add_argument("--history-run",type=pathlib.Path)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent
run=args.run.resolve()
history=args.history_run.resolve() if args.history_run else run
if args.completed and "Flow complete" not in (run/"flow.log").read_text():
    raise SystemExit("Run has not logged successful flow completion")
config=json.loads((run/"resolved.json").read_text())
manifest_path=run/"source-manifest.json"
if not manifest_path.exists():manifest_path=history/"source-manifest.json"
source_manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {"source_commit":None,"source_files":{}}
images=root/"results/images"
images.mkdir(exist_ok=True)
tech=pya.Technology()
tech.load(config["KLAYOUT_TECH"])
lefs=[v for k,v in config["TECH_LEFS"].items() if fnmatch.fnmatch(config["DEFAULT_CORNER"],k)] + config["CELL_LEFS"]

def render(source,output):
    variants=[images/"final-metal.png",images/"final-device.png"] if source.suffix==".gds" else []
    if output.exists() and output.stat().st_mtime>=source.stat().st_mtime and all(p.exists() for p in variants):return
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
    if source.suffix==".gds":
        palette={65:0x538268,66:0xbc6a42,67:0x59689c,68:0x557daa,69:0xb78856,70:0x6ba594,71:0x9589b6,72:0xc9b85f}
        iterator=view.begin_layers()
        while not iterator.at_end():
            props=iterator.current()
            props.visible=props.source_layer in palette and props.source_datatype in [20,44]
            if props.source_layer in palette:
                props.fill_color=palette[props.source_layer]
                props.frame_color=palette[props.source_layer]
            view.set_layer_properties(iterator,props)
            iterator.next()
    view.zoom_fit()
    bbox=view.active_cellview().layout().top_cell().dbbox()
    view.save_image_with_options(str(output),1800,int(1800*bbox.height()/bbox.width()),oversampling=1)
    if variants:
        for variant in variants:
            iterator=view.begin_layers()
            while not iterator.at_end():
                props=iterator.current()
                props.visible=props.source_datatype in [20,44] and ((68<=props.source_layer<=72) if "metal" in variant.name else (65<=props.source_layer<=67))
                view.set_layer_properties(iterator,props)
                iterator.next()
            view.save_image_with_options(str(variant),1800,int(1800*bbox.height()/bbox.width()),oversampling=1)
            print("Rendered",variant.name,flush=True)
    view.destroy()
    print("Rendered",output.name,flush=True)

specs=[
 ("Synthesis","12-openroad-staprepnr","No coordinates yet: mapped library cells and pre-placement timing estimates."),
 ("Floorplan","23-odb-addroutingobstructions","Core rows, physical support cells, and power distribution before signal placement."),
 ("Placement","31-openroad-stamidpnr","Cells have coordinates. This timing snapshot precedes subsequent repair and clock-tree synthesis."),
 ("Clock tree","38-openroad-stamidpnr-2","Clock buffers and timing-repair cells have been inserted. Hold repair has run; signal routing is still ahead."),
 ("Global routing","43-openroad-stamidpnr-3","Signal routes are planned and estimated parasitics updated. These are routing guides, before detailed legal track assignment."),
 ("Detailed routing","55-openroad-stapostpnr","Legal tracks and vias connect cells. Filler insertion and parasitic extraction have run; timing is evaluated across all configured corners."),
]
stages=[]
for name,dirname,description in specs:
    folder=(history if name in ["Synthesis","Floorplan","Placement","Clock tree"] else run)/dirname
    if not folder.exists() and name in ["Global routing","Detailed routing"]:
        matches=sorted(run.glob("*-openroad-"+("stamidpnr*" if name=="Global routing" else "stapostpnr")))
        if matches:folder=matches[-1]
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
                   "logic_area":metrics.get("design__instance__area",0)-sum(metrics.get("design__instance__area__class:"+c,0) for c in ["fill_cell","tap_cell","antenna_cell"]),
                   "cells":metrics.get("design__instance__count"),
                   "slack":None if name=="Floorplan" else metrics.get("timing__setup__ws"),
                   "corner":"extracted multicorner" if name=="Detailed routing" else config["DEFAULT_CORNER"] if name not in ["Synthesis","Floorplan"] else "pre-placement multicorner" if name=="Synthesis" else None,
                   "source_state":str(statefile.relative_to(root)),"metrics":metrics})
states=sorted(run.glob("[0-9]*-*/state_out.json"))
latest=json.loads(states[-1].read_text())
gds=latest.get("gds")
if gds:
    render(pathlib.Path(gds),images/"final-gds.png")
    m=latest["metrics"]
    stages.append({"name":"Final GDS","description":"GDS geometry, including standard-cell internals and routed interconnect. Final metrics come from the latest completed step.","image":"final-gds.png","area":m.get("design__instance__area"),"logic_area":m.get("design__instance__area",0)-sum(m.get("design__instance__area__class:"+c,0) for c in ["fill_cell","tap_cell","antenna_cell"]),"cells":m.get("design__instance__count"),"slack":m.get("timing__setup__ws"),"corner":"aggregate of final STA corners","source_state":str(states[-1].relative_to(root)),"metrics":m})
m=latest["metrics"]
check_keys=[("Magic DRC violations","magic__drc_error__count",""),
            ("KLayout DRC violations","klayout__drc_error__count",""),
            ("LVS errors","design__lvs_error__count",""),
            ("Antenna-violating nets","antenna__violating__nets",""),
            ("Setup violations","timing__setup_vio__count",""),
            ("Hold violations","timing__hold_vio__count",""),
            ("Worst setup slack","timing__setup__ws","ns"),
            ("Worst hold slack","timing__hold__ws","ns"),
            ("Maximum slew violations","design__max_slew_violation__count",""),
            ("Maximum capacitance violations","design__max_cap_violation__count",""),
            ("Unannotated nets after filtering","timing__unannotated_net_filtered__count",""),
            ("Lint warnings (reviewed separately)","design__lint_warning__count","")]
checks=[{"name":name,"value":m.get(key),"unit":unit,"key":key} for name,key,unit in check_keys]
result={"completed":args.completed,"run":run.name,"librelane":"3.0.16",
        "source_commit":source_manifest["source_commit"],"source_files":source_manifest["source_files"],
        "pdk_revision":"8afc8346a57fe1ab7934ba5a6056ea8b43078e71",
        "docker_digests":source_manifest.get("docker_digests"),
        "clock_period_ns":config["CLOCK_PERIOD"],"default_corner":config["DEFAULT_CORNER"],
        "sta_corners":config.get("STA_CORNERS"),"stages":stages,"checks":checks,"final_metrics":m}
def seconds(value):
    h,m,s=value.split(":")
    return int(h)*3600+int(m)*60+float(s)
result["runtime"]=[]
for folder in sorted(run.glob("[0-9]*-*")):
    processes=list(folder.rglob("*.process_stats.json"))
    if not (folder/"runtime.txt").exists():continue
    stats=[json.loads(p.read_text()) for p in processes]
    result["runtime"].append({"stage":folder.name,"seconds":seconds((folder/"runtime.txt").read_text().strip()),
                              "peak_rss": [s["peak_resources"]["memory_rss"] for s in stats]})
if gds:result["gds_sha256"]=hashlib.sha256(pathlib.Path(gds).read_bytes()).hexdigest()
if gds:result["layer_views"]={"all":"final-gds.png","metal":"final-metal.png","device":"final-device.png"}
(root/"results/physical.json").write_text(json.dumps(result,indent=2)+"\n")
print("Exported physical metrics",flush=True)
