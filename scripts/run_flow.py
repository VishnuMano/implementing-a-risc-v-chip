"""Run the pinned flow and preserve source provenance before invoking tools."""
import argparse
import hashlib
import importlib.metadata
import json
import pathlib
import subprocess
import sys
parser=argparse.ArgumentParser()
parser.add_argument("--tag",default="baseline")
parser.add_argument("--jobs",type=int,default=8)
args=parser.parse_args()
root=pathlib.Path(__file__).resolve().parent.parent
run=root/"flow/runs"/args.tag
if run.exists():raise SystemExit("Run tag already exists; use make RUN_TAG=another-name physical")
if importlib.metadata.version("librelane")!="3.0.16":raise SystemExit("Install flow/requirements.txt first")
paths=sorted(list((root/"rtl").glob("*.v"))+list((root/"firmware").glob("*"))+[root/"third_party/picorv32/picorv32.v",root/"flow/config.json",root/"flow/constraints.sdc"])
manifest={"source_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip(),
          "source_files":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
          "librelane":"3.0.16"}
(root/"build").mkdir(exist_ok=True)
pending=root/"build"/(args.tag+"-source-manifest.json")
pending.write_text(json.dumps(manifest,indent=2)+"\n")
command=[sys.executable,"-m","librelane","--docker-no-tty","--dockerized","--pdk-root",str(root/"build/pdk"),"--condensed","-j",str(args.jobs),"--run-tag",args.tag,"flow/config.json"]
result=subprocess.run(command,cwd=root)
try:
    manifest["docker_digests"]=json.loads(subprocess.check_output(["docker","image","inspect","ghcr.io/librelane/librelane:3.0.16","--format","{{json .RepoDigests}}"],text=True))
except subprocess.CalledProcessError:manifest["docker_digests"]=None
pending.write_text(json.dumps(manifest,indent=2)+"\n")
if run.exists():(run/"source-manifest.json").write_text(pending.read_text())
raise SystemExit(result.returncode)
