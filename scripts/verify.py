"""Record reproducible local verification without exporting private test fixtures."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
commands=[[sys.executable,"scripts/build_native.py"],["node","tests/crypto.test.mjs"],[sys.executable,"-m","unittest","discover","-s","tests","-v"],["node","--check","web/app.js"]]
results=[]
for command in commands:
    run=subprocess.run(command,cwd=root,text=True,capture_output=True)
    results.append({"command":command,"exit_code":run.returncode,"output":(run.stdout+run.stderr).strip()})
    print(results[-1]["output"])
    if run.returncode:break
paths=[*root.glob("src/*.*"),*root.glob("web/*.*"),*root.glob("tests/*.*")]
evidence={"recorded_at":datetime.now(timezone.utc).isoformat(),"scope":"Local crypto, native evaluator, input boundary and loopback HTTP checks","live_api":False,"passed":all(r["exit_code"]==0 for r in results),"checks":results,"sha256":{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}}
(root/"evidence").mkdir(exist_ok=True)
(root/"evidence"/"local-verification.json").write_text(json.dumps(evidence,indent=2)+"\n")
sys.exit(0 if evidence["passed"] else 1)
