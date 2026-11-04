#!/usr/bin/env python3
"""Batch 7: READ-ONLY review of preserved unmatched events from 2026-11-04 scrape.
Never changes events.json. Uses a fixed snapshot of the scrape log's preserved keys.
"""
import csv, json
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parent.parent
TODAY = date.today()
PRESERVED_KEYS = set(tuple(row) for row in [("'Sweat Your Prayers' 5Rhythms McLaren Vale", '2026-12-06'), ("'Sweat Your Prayers' 5Rhythms McLaren Vale", '2027-02-07'), ('2026 SA ASSA Christmas Connect', '2026-11-11'), ('A Day in the Gully', '2027-02-27'), ('Adelaide Hills Ready-Set-Connect', '2026-11-11'), ('Bachata By The Beach - Latin Dance Party', '2026-11-29'), ('Beaumont House Open Days', '2026-12-06'), ('Chiodos ‘All’s Well That Ends Well’ 20 Year Anniversary Tour', '2026-11-26'), ('Day Moves', '2026-12-31'), ('End of Year Celebration - Adelaide', '2026-11-19'), ('Good News Festival 2026', '2026-12-26'), ('Hills Business - Strength in Diversity', '2026-11-04'), ('ICOM NATHIST 2026 Annual Conference', '2026-11-09'), ('Intergenerational Playgroup, The Learning Tree', '2026-11-05'), ('Intergenerational Playgroup, The Learning Tree', '2026-11-12'), ('Intergenerational Playgroup, The Learning Tree', '2026-11-19'), ('Intergenerational Playgroup, The Learning Tree', '2026-11-26'), ('Intergenerational Playgroup, The Learning Tree', '2026-12-03'), ('Intergenerational Playgroup, The Learning Tree', '2026-12-10'), ('It’s In Our Nature: A Queer Tour of the Museum', '2026-11-07'), ('Jenny and Joel Creasey Live', '2026-11-08'), ('Lip Sync LIVE! - Adelaide', '2027-03-13'), ('MECCA Burnside Village: THE MECCA HOLIDAY SOIREE', '2026-11-04'), ('METAL ON MURRAY 10 - SATURDAY MARCH 20TH - THE PA HOTEL, GAWLER', '2027-03-20'), ("Marley Love - Don't Know My Name EP Launch (with Erin Buku + Inner Tribe DJ's)", '2026-11-28'), ('Mindful Clay, Pottery wheel, Hand Building & Colors', '2026-03-27'), ('Minus18 Queer Formal® Adelaide 2026', '2026-11-06'), ('Miracle', '2026-11-04'), ('Monet to Matisse: Defying Tradition', '2026-10-29'), ('Motivate Dance Studio Concert 2026', '2026-11-21'), ('Origins', '2026-11-08'), ('Poppin Out 2026 - Adelaide', '2026-11-07'), ('Port Noarlunga Music Festival', '2026-11-20'), ('Queer Joy', '2026-11-08'), ('RU Pretty Enuff Australian Tour ‘26', '2026-11-05'), ('RUFUS RICE: RICE AGE – ADELAIDE', '2026-11-03'), ('SWEETIE - DOGTOOTH ALBUM TOUR w/ ELLA ION (18+)', '2026-12-05'), ('Single Lesbian, Bi & Queer Women @ No.6 East - City', '2026-11-22'), ('Sparkling Sounds: Sunset Edition ft. Cosmos Midnight', '2026-11-21'), ('Sunday at The Cedars - Monthly Talks Series', '2026-12-06'), ('Sunday at The Cedars - Monthly Talks Series', '2027-02-07'), ('Sunday at The Cedars - Monthly Talks Series', '2027-03-07'), ('Sunday at The Cedars - Monthly Talks Series', '2027-04-04'), ('Sunday at The Cedars - Monthly Talks Series', '2027-05-02'), ('Sunday at The Cedars - Monthly Talks Series', '2027-06-06'), ('The Art of Seafood: Fish for the Table', '2026-11-05'), ('UnWined Uncovered', '2026-11-27'), ('Vinyl Thursdays', '2026-11-05'), ('Vinyl Thursdays', '2026-11-12'), ('Vinyl Thursdays', '2026-11-19'), ('Vinyl Thursdays', '2026-11-26'), ('Watchman House', '2026-11-07'), ('Watchman House', '2026-12-05'), ('Women in Innovation Awards 2026', '2026-11-06')])

def main():
    path = ROOT / "events.json"
    events = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(events, list):
        raise ValueError("events.json must contain a list")
    found = []
    for event in events:
        title = str(event.get("title", ""))
        start = str(event.get("datetime", ""))[:10]
        if (title, start) not in PRESERVED_KEYS:
            continue
        end = str(event.get("end_datetime", ""))[:10]
        try:
            start_day = date.fromisoformat(start)
        except ValueError:
            start_day = None
        try:
            end_day = date.fromisoformat(end)
        except ValueError:
            end_day = None
        if start_day is None:
            priority, reason = "HIGH", "Invalid/missing start date"
        elif end_day and end_day < TODAY:
            priority, reason = "HIGH", "End date has passed"
        elif start_day < TODAY and end_day is None:
            priority, reason = "HIGH", "Past start with no end date"
        elif start_day < TODAY and end_day and end_day >= TODAY:
            priority, reason = "MEDIUM", "Ongoing event: confirm end date and schedule"
        else:
            priority, reason = "REVIEW", "Not rediscovered by scraper; confirm official listing"
        found.append({"priority":priority,"reason":reason,"title":title,"source":event.get("source",""),"venue":event.get("venue",""),"start":start,"end":end,"link":event.get("link","")})
    order = {"HIGH":0,"MEDIUM":1,"REVIEW":2}
    found.sort(key=lambda r:(order[r["priority"]],r["start"],r["title"]))
    out = ROOT / "batch-7-preserved-events-review.csv"
    with out.open("w",newline="",encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["priority","reason","title","source","venue","start","end","link"])
        writer.writeheader();writer.writerows(found)
    print(f"Events in database: {len(events)}")
    print(f"Preserved keys from previous scrape log: {len(PRESERVED_KEYS)}")
    print(f"Matching event records: {len(found)}")
    for level in ("HIGH","MEDIUM","REVIEW"):
        print(f"  {level}: {sum(r['priority']==level for r in found)}")
    print(f"CSV saved: {out}")
    print("READ ONLY: events.json not changed. Flags are review suggestions, NOT confirmed cancellations.")

if __name__ == "__main__":
    main()
