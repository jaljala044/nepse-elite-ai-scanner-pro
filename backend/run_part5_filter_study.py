"""Reproducible observed-calendar breadth/peer-RS/broker reference study."""
import pandas as pd, sqlite3, json, sys

def run(price_csv, broker_sqlite):
    p=pd.read_csv(price_csv).sort_values(['symbol','date'])
    c=p.pivot(index='date',columns='symbol',values='close')
    o=p.pivot(index='date',columns='symbol',values='open')
    h=p.pivot(index='date',columns='symbol',values='high')
    v=p.pivot(index='date',columns='symbol',values='volume')
    ret=c/c.shift(20)-1
    breadth=ret.gt(0).sum(axis=1)/ret.notna().sum(axis=1)
    rs=ret.sub(ret.median(axis=1),axis=0)
    br=c.gt(h.shift().rolling(20,min_periods=20).max())
    db=sqlite3.connect(broker_sqlite)
    try:
        days={x[0] for x in db.execute('select day from archive_sessions')}
        broker=pd.read_sql_query('select day,symbol,broker,buy_cents,sell_cents from archive_broker',db)
    finally:
        db.close()
    broker['net']=broker.buy_cents-broker.sell_cents
    broker['gross']=broker.buy_cents+broker.sell_cents
    broker['buyday']=(broker.net>0).astype(int)
    flags=pd.DataFrame(False,index=c.index,columns=c.columns)
    coverage=pd.Series(False,index=c.index)
    for i in range(4,len(c)):
        ds=list(c.index[i-4:i+1])
        if not set(ds)<=days:continue
        coverage.iloc[i]=True
        agg=broker[broker.day.isin(ds)].groupby(['symbol','broker'])[['net','gross','buyday']].sum()
        names=agg[(agg.net>0)&(agg.buyday>=3)&(agg.net*5>=agg.gross)].index.get_level_values(0).unique()
        flags.loc[ds[-1],c.columns.intersection(names)]=True
    rules={'breakout':br,'breakout_breadth':br.mul(breadth>=.5,axis=0),'breakout_rs':br & rs.gt(0),
           'breakout_breadth_rs':br.mul(breadth>=.5,axis=0)&rs.gt(0),'broker_persistence':flags,
           'breakout_broker':br&flags,'matched_breakout':br.mul(coverage,axis=0)}
    valid=c.notna().rolling(26,min_periods=26).sum().shift(-5).eq(26)&v.shift(-1).gt(0)&v.shift(-5).gt(0)
    future=100*(c.shift(-5)/o.shift(-1)-1)-1
    results=[]
    for label,start,end in [('2025','2025-01-01','2025-12-31'),('2026','2026-01-01','2026-11-20')]:
        for name,rule in rules.items():
            vals=[];traded=0
            for s in c:
                busy=-1;n=0
                for i in range(20,len(c)-5):
                    if i<=busy or c.index[i]<start or c.index[i+5]>end or not valid[s].iloc[i] or not rule[s].iloc[i]:continue
                    vals.append(float(future[s].iloc[i]));busy=i+5;n+=1
                traded+=bool(n)
            results.append(dict(period=label,rule=name,n=len(vals),symbols=traded,mean=sum(vals)/len(vals) if vals else None,positive=100*sum(x>0 for x in vals)/len(vals) if vals else None))
    return dict(calendar='observed union',sessions=len(c),broker_complete_windows=int(coverage.sum()),results=results)

if __name__=='__main__':
    print(json.dumps(run(*sys.argv[1:]),indent=2,allow_nan=False))
