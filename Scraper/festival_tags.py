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


MAJOR_EVENT_CATEGORY = "Festival/Major Events"

# Curated parent events. Do not classify individual concerts, theatre productions,
# sporting matches or other programme activities solely because they share a source.
MAJOR_EVENT_TITLE_PATTERNS = (
    r"^bp adelaide grand final(?: 20\d{2})?$",
    r"^womadelaide(?: 20\d{2})?$",
    r"^adelaide fringe(?: festival)?(?: 20\d{2})?$",
    r"^adelaide festival(?: 20\d{2})?$",
    r"^illuminate adelaide(?: 20\d{2})?$",
    r"^(?:sala festival|south australian living artists festival)(?: 20\d{2})?$",
    r"^(?:south australian |sa |20\d{2} )?multicultural festival(?: 20\d{2})?$",
    r"^adelaide film festival(?: 20\d{2})?$",
    r"^ozasia festival(?: 20\d{2})?$",
    r"^adelaide cabaret festival(?: 20\d{2})?$",
    r"^tasting australia(?: 20\d{2})?$",
    r"^adelaide motorsport festival(?: 20\d{2})?$",
    r"^adelaide beer (?:&|and) bbq festival(?: 20\d{2})?$",
    r"^(?:lucky dumpling market|moon lanterns at lucky dumpling market)(?: 20\d{2})?$",
    r"^(?:santos )?tour down under(?: 20\d{2})?$",
    r"^adelaide international(?: tennis)?(?: tournament)?(?: 20\d{2})?$",
    r"^liv golf(?: adelaide)?(?: 20\d{2})?$",
    r"^(?:adelaide |national pharmaci(?:es|y) )?christmas pageant(?: 20\d{2})?$",
    r"^(?:adelaide )?carols by candlelight(?: 20\d{2})?$",
)

def assign_major_event_category(event):
    """Apply the requested single primary category without losing other tags."""
    title = re.sub(r"\s+", " ", str(event.get("title") or "")).strip()
    categories = event.get("category") or []
    if isinstance(categories, str):
        categories = [categories]
    categories = [str(value).strip() for value in categories if str(value).strip()]
    categories = [MAJOR_EVENT_CATEGORY if value.casefold() == "festival"
                  else value for value in categories]

    # A festival-specific programme title remains in its existing category.
    if any(re.fullmatch(pattern, title, re.I) for pattern in MAJOR_EVENT_TITLE_PATTERNS):
        categories = [MAJOR_EVENT_CATEGORY]
    event["category"] = list(dict.fromkeys(categories)) or ["Other"]
    return event
