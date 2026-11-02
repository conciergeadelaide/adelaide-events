"""Read-only quality report for the Adelaide events database.

Run from the repository root:
    python Scraper\audit_events.py

Creates Scraper/event_quality_report.txt. Never changes events.json.
"""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "events.json"
REPORT = Path(__file__).with_name("event_quality_report.txt")


def clean(value):
    return " ".join(re.sub(r"[^\w]+", " ", str(value or "").casefold()).split())


def datepart(event):
    return str(event.get("datetime") or event.get("date") or "")[:10]


def has_time(event):
    value = str(event.get("datetime") or event.get("date") or "")
    match = re.search(r"T(\d{2}):(\d{2})", value)
    return bool(match and match.group(0) != "T00:00")


def main():
    records = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError("events.json must contain a list")
    missing_time, missing_venue, missing_category, invalid_date = [], [], [], []
    groups = defaultdict(list)
    venue_variants = defaultdict(Counter)
    category_counts = Counter()
    for i, event in enumerate(records, 1):
        if not isinstance(event, dict):
            invalid_date.append((i, "Not an event object"))
            continue
        title = str(event.get("title") or "")
        venue = str(event.get("venue") or "")
        date = datepart(event)
        if not has_time(event):
            missing_time.append((i, title, date))
        if not venue.strip():
            missing_venue.append((i, title, date))
        categories = event.get("category") or []
        if isinstance(categories, str):
            categories = [categories]
        if not categories or categories == ["Other"]:
            missing_category.append((i, title, date))
        for category in categories:
            category_counts[str(category)] += 1
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            invalid_date.append((i, title))
        venue_variants[clean(venue)][venue] += 1
        # Same title, venue, date is only a review candidate: sessions can differ.
        groups[(clean(title), clean(venue), date)].append((i, event))
    candidates = [v for v in groups.values() if len(v) > 1]
    candidates.sort(key=lambda v: (-len(v), datepart(v[0][1])))
    variants = [(k, v) for k, v in venue_variants.items() if k and len(v) > 1]
    lines = [
        "ADELAIDE EVENTS — READ-ONLY DATA QUALITY REPORT",
        f"Total records: {len(records)}",
        f"Potential same-title / same-venue / same-day groups: {len(candidates)}",
        f"Records without confirmed start time: {len(missing_time)}",
        f"Records without venue: {len(missing_venue)}",
        f"Records with missing / Other category: {len(missing_category)}",
        f"Invalid dates: {len(invalid_date)}",
        f"Venue spelling / punctuation variants: {len(variants)}",
        "",
        "IMPORTANT: Repeated performances on the same day are NOT necessarily duplicates.",
        "This report never deletes, merges or edits events.",
        "",
        "POTENTIAL DUPLICATE GROUPS (up to 100)",
    ]
    for group in candidates[:100]:
        for i, event in group:
            lines.append(f"  #{i} | {event.get('datetime','')} | {event.get('title','')} | {event.get('venue','')} | {event.get('source','')}")
        lines.append("")
    lines += ["VENUE NAME VARIANTS"]
    for _, counter in variants:
        lines.append("  " + " | ".join(f"{name} ({count})" for name, count in counter.items()))
    lines += ["", "CATEGORY COUNTS"]
    lines += [f"  {name}: {count}" for name, count in category_counts.most_common()]
    for label, entries in [
        ("MISSING START TIMES (first 100)", missing_time),
        ("MISSING VENUES (first 100)", missing_venue),
        ("MISSING / OTHER CATEGORIES (first 100)", missing_category),
        ("INVALID DATES", invalid_date),
    ]:
        lines += ["", label]
        lines += ["  " + " | ".join(map(str, item)) for item in entries[:100]]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:9]))
    print("Report saved to:", REPORT)


if __name__ == "__main__":
    main()
