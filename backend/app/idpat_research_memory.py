import sqlite3,json
from .idpat_experimental_research import register_plan

def store_plan(path,plan,assessment_time):
    result=register_plan(plan,assessment_time)
    payload=json.dumps(plan,sort_keys=True)
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS idpat_plans (id TEXT PRIMARY KEY,payload TEXT NOT NULL,first_review TEXT NOT NULL)")
        cursor=db.execute("INSERT OR IGNORE INTO idpat_plans VALUES (?,?,?)",(result["plan_id"],payload,assessment_time))
        return dict(result,inserted=cursor.rowcount==1)
