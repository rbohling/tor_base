"""MySQL-only paired index experiment; writes raw CSV and execution plans."""
import argparse, csv, json, platform, statistics, time
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import text
from torbase import create_app
p=argparse.ArgumentParser(); p.add_argument('--user-id',type=int,default=1); p.add_argument('--repeats',type=int,default=30); p.add_argument('--output',default='results/sql')
a=p.parse_args()
if a.repeats<5: p.error('Use at least five repeats.')
engine=create_app().extensions['engine']
if engine.dialect.name!='mysql': p.error('This experiment requires MySQL 8.0.18+ or 8.4.')
out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
params={'uid':a.user_id,'prefix':'Lab 019%'}
queries={
 'ignore_composite':'SELECT id,title FROM posts IGNORE INDEX (ix_posts_owner_title) WHERE user_id=:uid AND title LIKE :prefix ORDER BY title,id LIMIT 100',
 'optimizer_choice':'SELECT id,title FROM posts WHERE user_id=:uid AND title LIKE :prefix ORDER BY title,id LIMIT 100'}
rows=[]; plans={}
with engine.connect() as c:
    metadata={'utc':datetime.now(timezone.utc).isoformat(),'server':c.scalar(text('SELECT VERSION()')),
        'python':platform.python_version(),'rows':c.scalar(text('SELECT COUNT(*) FROM posts')),
        'parameters':params,'repeats':a.repeats,'warmups_per_variant':3}
    for mode,q in queries.items():
        plans[mode]='\n'.join(str(r[0]) for r in c.execute(text('EXPLAIN ANALYZE '+q),params))
        for _ in range(3): c.execute(text(q),params).all()
    expected=None
    for i in range(a.repeats):
        order=list(queries) if i%2==0 else list(reversed(queries))
        for mode in order:
            start=time.perf_counter(); result=c.execute(text(queries[mode]),params).all()
            elapsed=(time.perf_counter()-start)*1000
            if expected is None: expected=result
            if result!=expected: raise RuntimeError('Query results differ; experiment invalid.')
            rows.append({'iteration':i+1,'mode':mode,'db_roundtrip_ms':elapsed,'rows_returned':len(result)})
if not expected: raise RuntimeError('No matching rows. Seed 20,000 notes for this user first.')
with (out/'raw.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
(out/'plans.json').write_text(json.dumps(plans,indent=2))
metadata['median_ms']={m:statistics.median(r['db_roundtrip_ms'] for r in rows if r['mode']==m) for m in queries}
metadata['interpretation']='Client-observed SQL round trips. Baseline ignores only the composite index; other indexes remain. Inspect plans before claiming index use.'
(out/'summary.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata,indent=2))
