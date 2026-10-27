"""Conservative festival labels for the Concierge Adelaide events guide.

Only identify explicit festival references or a small verified programme list.
Avoid classifying every event at a festival venue as a festival event.
"""
import re

FESTIVAL_PATTERNS = (
    ("OzAsia Festival", (r"ozasia", r"oz-asia")),
    ("Adelaide Fringe", (r"adelaide[ -]fringe", r"fringe festival")),
    ("WOMADelaide", (r"womadelaide",)),
    ("Adelaide Festival", (r"adelaide festival(?! centre)",)),
    ("Adelaide Film Festival", (r"adelaide film festival",)),
    ("Adelaide Italian Festival", (r"adelaide italian festival",)),
    ("Illuminate Adelaide", (r"illuminate adelaide",)),
    ("Tasting Australia", (r"tasting australia",)),
    ("SALA Festival", (r"sala festival", r"south australian living artists")),
    ("Feast Festival", (r"feast festival",)),
    ("Adelaide Cabaret Festival", (r"adelaide cabaret festival",)),
    ("Adelaide Guitar Festival", (r"adelaide guitar festival",)),
    ("Adelaide Writers' Week", (r"adelaide writers.? week",)),
    ("Nature Festival", (r"nature festival",)),
    ("Reunion Festival", (r"reunion festival",)),
    ("Sidebyside Festival", (r"sidebyside festival",)),
    ("2026 Multicultural Festival", (r"2026 multicultural festival",)),
)

# These are identifiable 2026 OzAsia programme activities in the supplied dataset.
OZASIA_2026_TITLES = {
    "hong kong dragon", "lucky dumpling market",
    "moon lanterns at lucky dumpling market",
    "ceramic tile painting workshop with jake yang",
}


def assign_festivals(event):
    title = str(event.get("title") or "").strip()
    link = str(event.get("link") or event.get("url") or "")
    text = title + " " + link
    matches = []
    for name, patterns in FESTIVAL_PATTERNS:
        if any(re.search(pattern, text, re.I) for pattern in patterns):
            matches.append(name)
    if title.casefold() in OZASIA_2026_TITLES and "OzAsia Festival" not in matches:
        matches.append("OzAsia Festival")
    # Recompute instead of retaining stale tags from previous scraper runs.
    if matches:
        event["festival"] = matches
    else:
        event.pop("festival", None)
    return event
