"""Scheduled evidence backup runner. Local trusted operator configuration only."""
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import fcntl

def _digest(row):
    return hashlib.sha256(json.dumps(row,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def _read(path):
    rows=[]
    previous=None
    if not Path(path).exists():
        return rows
    for line in Path(path).read_text().splitlines():
        row=json.loads(line)
        digest=row.pop("sha256")
        if row.get("previous_sha256")!=previous or _digest(row)!=digest:
            raise ValueError("invalid receipt chain")
        row["sha256"]=digest
        rows.append(row)
        previous=digest
    return rows

def run_scheduled_backup(*,config,receipt_path,lock_path,run_id,now_utc=None):
    for key in ("quiesce_argv","backup_argv","resume_argv"):
        argv=config[key]
        if not isinstance(argv,list) or not argv or not all(isinstance(x,str) for x in argv) or not Path(argv[0]).is_absolute():
            raise ValueError("absolute path to executable required")
    timeout=config["command_timeout_seconds"]
    if not isinstance(timeout,(int,float)) or not 0<timeout<=3600:
        raise ValueError("invalid timeout")
    now=now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("timezone required")
    receipt_path,lock_path=Path(receipt_path),Path(lock_path)
    receipt_path.parent.mkdir(parents=True,exist_ok=True)
    lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        prior=_read(receipt_path)
        if any(r["run_id"]==run_id for r in prior):
            raise ValueError("duplicate run id")
        def run(key):
            return subprocess.run(config[key],shell=False,check=True,capture_output=True,text=True,timeout=timeout)
        status="backup_failed"
        error=None
        try:
            run("quiesce_argv")
            report=json.loads(run("backup_argv").stdout)
            if report.get("status")=="backup_verified" and report.get("verification",{}).get("status")=="verified":
                status="backup_verified"
            else:
                error="backup verification not confirmed"
        except Exception as exc:
            error=type(exc).__name__
        finally:
            try:
                run("resume_argv")
            except Exception as exc:
                status="backup_failed"
                error="resume_failed:"+type(exc).__name__
        row={"run_id":run_id,"at":now.astimezone(timezone.utc).isoformat(),"status":status,"error":error,
             "previous_sha256":prior[-1]["sha256"] if prior else None}
        row["sha256"]=_digest(row)
        with receipt_path.open("a") as f:
            f.write(json.dumps(row,sort_keys=True)+"\n")
            f.flush()
            os.fsync(f.fileno())
        return row

def audit_backup_schedule(receipt_path,*,expected_interval_hours=24,grace_hours=2,now_utc=None):
    result={"production_eligible":False,"issues":[],"events_checked":0,"ledger_status":"verified","latest_run_status":None}
    try:
        rows=_read(receipt_path)
        result["events_checked"]=len(rows)
        if not rows:
            result["issues"].append("no_backup_receipts")
        else:
            last=rows[-1]
            result["latest_run_status"]=last["status"]
            if last["status"]!="backup_verified":
                result["issues"].append("latest_backup_run_failed")
            age=((now_utc or datetime.now(timezone.utc))-datetime.fromisoformat(last["at"])).total_seconds()/3600
            if age>expected_interval_hours+grace_hours:
                result["issues"].append("scheduled_backup_overdue")
            if age<0:
                result["issues"].append("future_receipt")
    except (OSError,ValueError,KeyError,TypeError):
        result["ledger_status"]="invalid"
        result["issues"].append("invalid_receipt_chain")
    result["status"]="attention_required" if result["issues"] else "healthy"
    return result
