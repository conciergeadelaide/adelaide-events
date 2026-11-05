"""Batch 6: read-only source health analysis. Python standard library only."""
import csv, json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parent.parent
SOURCES = ("Experience Adelaide", "Plant 3 Bowden", "Adelaide Botanic Gardens")

def parse_day(event):
    for field in ("datetime", "date"):
        raw = str(event.get(field) or "").strip()
        if raw:
            try: return date.fromisoformat(raw[:10])
            except ValueError: pass
    return None

def main():
    events = json.loads((ROOT / "events.json").read_text(encoding="utf-8"))
    if not isinstance(events, list): raise ValueError("events.json must be an array")
    today = date.today()
    print(f"Batch 6 verified source analysis (READ ONLY) | {len(events)} events | {today}")
    rows=[]
    for source in SOURCES:
        subset=[e for e in events if isinstance(e,dict) and e.get("source")==source]
        by_link=defaultdict(list)
        for e in subset:
            link=str(e.get("link") or e.get("url") or "").split("?",1)[0].rstrip("/")
            by_link[link].append(e)
        future=sum(parse_day(e) is not None and parse_day(e)>=today for e in subset)
        past=sum(parse_day(e) is not None and parse_day(e)<today for e in subset)
        invalid=len(subset)-future-past
        print(f"\n{source}: {len(subset)} records, {len(by_link)} unique links")
        print(f"  Start dates: {future} today/future, {past} past, {invalid} missing/unparseable")
        print(f"  Repeated-link records: {sum(max(0,len(g)-1) for g in by_link.values())}")
        for link, group in sorted(by_link.items(),key=lambda kv:-len(kv[1]))[:6]:
            if len(group)>1: print(f"  Recurring: {group[0].get('title','')} — {len(group)} occurrences")
        for e in subset:
            d=parse_day(e)
            rows.append({'source':source,'title':e.get('title',''),'venue':e.get('venue',''),
                         'datetime':e.get('datetime',''),'end_datetime':e.get('end_datetime',''),
                         'date_status':'UNPARSEABLE' if d is None else ('PAST_START' if d<today else 'TODAY_OR_FUTURE'),
                         'link':e.get('link') or e.get('url') or ''})
    dest=ROOT/'source-reliability-report.csv'
    with dest.open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['source','title','venue','datetime','end_datetime','date_status','link']);writer.writeheader();writer.writerows(rows)
    print(f"\nSaved: {dest}")
    print("No scraper or event records changed. Date status refers to START date, not whether a multi-day event is ongoing.")
if __name__=='__main__':main()
