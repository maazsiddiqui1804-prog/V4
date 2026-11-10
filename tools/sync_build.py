"""Claude's session-end helper: rebuild the app's Build page copy (data/app/build.json) from the
V4 Dashboard (tasks + phases exported with ArtifactData list/get out_dir). Usage:
    python tools/sync_build.py <export_dir>      # expects <dir>/tasks/*.json and <dir>/ref/phases.json
"""
import datetime as dt
import glob
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
tasks = []
for f in sorted(glob.glob(str(d / "tasks" / "*.json"))):
    x = json.load(open(f))
    x = x.get("data", x)
    tasks.append({k: x.get(k) for k in ["task_id", "phase_id", "phase", "owner", "status", "task"]})
ph = json.load(open(d / "ref" / "phases.json"))
ph = ph.get("data", ph)["rows"]
phases = []
for p in sorted(ph, key=lambda p: p["order"]):
    mine = [t for t in tasks if t["phase_id"] == p["phase_id"]]
    done = sum(t["status"] == "Done" for t in mine)
    phases.append({"id": p["phase_id"], "name": p["phase"], "status": f"{p['phase_status']} — {p['window']}",
                   "pct": round(100 * done / len(mine)) if mine else 100})
out = {"updated": dt.date.today().isoformat(), "note": "Copy of the claude.ai V4 Dashboard; Claude refreshes it each session.",
       "phases": phases, "tasks": tasks}
Path("data/app/build.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(f"{len(tasks)} tasks, {len(phases)} phases written")
