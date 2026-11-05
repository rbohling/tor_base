"""Alternate local and onion requests from the SAME client. Do not infer pure Tor overhead."""
import argparse, csv, getpass, re, statistics, time, json
from pathlib import Path
from datetime import datetime, timezone
import requests
p=argparse.ArgumentParser(); p.add_argument('--local',default='http://127.0.0.1:8080'); p.add_argument('--onion',required=True)
p.add_argument('--proxy',default='socks5h://127.0.0.1:9150'); p.add_argument('--username',required=True); p.add_argument('--repeats',type=int,default=20); p.add_argument('--output',default='results/http')
a=p.parse_args()
from urllib.parse import urlparse
if not urlparse(a.onion).hostname or not urlparse(a.onion).hostname.endswith('.onion'): p.error('--onion must be an onion URL')
if a.repeats<5: p.error('Use at least five repeats')
password=getpass.getpass('Lab password: ')
sessions={}; urls={'local':a.local.rstrip('/'),'onion':a.onion.rstrip('/')}
for mode in urls:
    s=requests.Session(); s.trust_env=False
    if mode=='onion': s.proxies={'http':a.proxy,'https':a.proxy}
    r=s.get(urls[mode]+'/login',timeout=90); r.raise_for_status()
    csrf=re.search(r'name="csrf_token" value="([^"]+)"',r.text)
    if not csrf: raise RuntimeError('Login form missing CSRF token')
    r=s.post(urls[mode]+'/login',data={'username':a.username,'password':password,'csrf_token':csrf[1]},timeout=90)
    r.raise_for_status()
    if urlparse(r.url).path=='/login': raise RuntimeError('Login failed')
    sessions[mode]=s
    for _ in range(2): s.get(urls[mode]+'/benchmark',timeout=90).raise_for_status()
rows=[]
for i in range(a.repeats):
    for mode in (['local','onion'] if i%2==0 else ['onion','local']):
        start=time.perf_counter()
        try:
            r=sessions[mode].get(urls[mode]+'/benchmark',timeout=90); r.raise_for_status(); payload=r.json()
            rows.append({'iteration':i+1,'mode':mode,'http_ms':(time.perf_counter()-start)*1000,'db_roundtrip_ms':payload['db_roundtrip_ms'],'count':payload['count'],'ok':1})
        except (requests.RequestException,ValueError,KeyError):
            rows.append({'iteration':i+1,'mode':mode,'http_ms':(time.perf_counter()-start)*1000,'db_roundtrip_ms':'','count':'','ok':0})
out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
with (out/'raw.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
summary={'utc':datetime.now(timezone.utc).isoformat(),'repeats':a.repeats,'warmups':2,'modes':{}}
for mode in urls:
    good=[r['http_ms'] for r in rows if r['mode']==mode and r['ok']]
    summary['modes'][mode]={'successes':len(good),'failures':a.repeats-len(good),'median_http_ms':statistics.median(good) if good else None}
summary['limitations']='Warm persistent sessions, one client, one service. HTTP minus DB time includes application, queues and transport. It is not pure Tor latency.'
(out/'summary.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2))
