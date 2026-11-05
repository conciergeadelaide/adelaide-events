"""Offline read-only audit of the events.json file; Python standard library only."""
import json, collections, pathlib, re, sys
path=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path("events.json")
events=json.loads(path.read_text(encoding="utf-8"))
print("Events:",len(events))
print("Sources:",len(set(str(e.get("source") or "") for e in events)))
missing_images=[e for e in events if not str(e.get("image") or "").startswith(("https://","http://"))]
missing_links=[e for e in events if not str(e.get("link") or "").startswith(("https://","http://"))]
print("Missing/invalid image URLs:",len(missing_images))
print("Missing/invalid event links:",len(missing_links))
for e in missing_images[:20]: print("  IMAGE:",e.get("datetime"),"|",e.get("title"),"|",e.get("source"))
for e in missing_links[:20]: print("  LINK:",e.get("datetime"),"|",e.get("title"),"|",e.get("source"))
groups=collections.defaultdict(list)
def clean(s): return " ".join(re.sub(r"[^a-z0-9]+"," ",str(s or "").casefold()).split())
for e in events:
 key=(clean(e.get("title")),clean(e.get("venue")),str(e.get("datetime") or "")[:10])
 groups[key].append(e)
ambiguous=[(k,v) for k,v in groups.items() if len(v)>1 and len(set(e.get("source") for e in v))>1]
print("Cross-source same-title/venue/day groups to review:",len(ambiguous))
for (title,venue,day),group in ambiguous:
 print("  REVIEW:",day,"|",group[0].get("title"),"|",group[0].get("venue"))
 for e in group: print("    ",e.get("datetime"),"|",e.get("source"))
print("This audit checks data only; it does not verify live websites or images.")
