"""Compare completed mapped-synthesis/pre-placement STA runs, not routed timing."""
import json
import pathlib
root=pathlib.Path(__file__).resolve().parent.parent
rows=[]
for tag in ["baseline","clock-50","clock-20"]:
    run=root/"flow/runs"/tag
    config=json.loads((run/"resolved.json").read_text())
    metrics=json.loads((run/"12-openroad-staprepnr/state_out.json").read_text())["metrics"]
    rows.append({"run":tag,"period_ns":config["CLOCK_PERIOD"],"target_mhz":1000/config["CLOCK_PERIOD"],
                 "area_um2":metrics["design__instance__area"],"cells":metrics["design__instance__count"],
                 "setup_slack_ns":metrics["timing__setup__ws"],
                 "corners":{k.split("__corner:")[1]:v for k,v in metrics.items() if k.startswith("timing__setup__ws__corner:")},
                 "source_state":str((run/"12-openroad-staprepnr/state_out.json").relative_to(root))})
(root/"results/experiments.json").write_text(json.dumps({"stage":"mapped synthesis / pre-placement STA", "strategy":"AREA 0","runs":rows},indent=2)+"\n")
