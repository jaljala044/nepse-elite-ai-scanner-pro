"""Content-addressed research strategy freeze; not independent certification."""
import json,hashlib,re
from .point_in_time import _aware

def freeze_configuration(*, strategy, methodology, code_sha, parameters, dataset_sha256, frozen_at, holdout_start):
    if not all(isinstance(x,str) and x.strip() for x in (strategy,methodology)):
        raise ValueError("strategy and methodology required")
    if not re.fullmatch(r"[0-9a-f]{40}",code_sha) or not re.fullmatch(r"[0-9a-f]{64}",dataset_sha256):
        raise ValueError("pinned code and dataset hashes required")
    if not isinstance(parameters,dict) or not parameters:
        raise ValueError("nonempty parameters required")
    if _aware(frozen_at)>=_aware(holdout_start):
        raise ValueError("holdout must follow freeze")
    record=dict(strategy=strategy,methodology=methodology,code_sha=code_sha,parameters=parameters,
        dataset_sha256=dataset_sha256,frozen_at=_aware(frozen_at).isoformat(),holdout_start=_aware(holdout_start).isoformat(),
        independent_holdout_verified=False,production_eligible=False)
    payload=json.dumps(record,sort_keys=True,separators=(",",":"),allow_nan=False)
    return {"record":json.loads(payload),"freeze_sha256":hashlib.sha256(payload.encode()).hexdigest()}

def verify_configuration(envelope, *, expected_sha256):
    try:
        r=envelope["record"]
        rebuilt=freeze_configuration(**{k:r[k] for k in ("strategy","methodology","code_sha","parameters","dataset_sha256","frozen_at","holdout_start")})
        return rebuilt==envelope and rebuilt["freeze_sha256"]==expected_sha256
    except (ValueError,TypeError,KeyError,AttributeError):
        return False
