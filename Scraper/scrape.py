import json
import re
import sys
from difflib import SequenceMatcher
from datetime import datetime
import os
import shutil
import requests
from urllib.parse import urlparse

from bs4 import BeautifulSoup

try:
    # Works when running:
    # python Scraper\scrape.py
    from config import SOURCES
    from parsers import (
        parse_json_ld,
        parse_adelaide_oval,
        parse_adelaide_convention_centre,
        parse_adelaide_festival_centre,
        parse_hindley_st_music_hall,
        parse_adelaide_entertainment_centre,
        parse_coopers_stadium,
        parse_immersive_light_and_art,
        parse_adelaide_town_hall,
        parse_lion_arts_factory,
        parse_south_australia_tourism,
        parse_ticketmaster_adelaide,
        parse_experience_adelaide,
        parse_moshtix_adelaide,
    )
except ModuleNotFoundError:
    # Works when importing:
    # from Scraper.scrape import ...
    from Scraper.config import SOURCES
    from Scraper.parsers import (
        parse_json_ld,
        parse_adelaide_oval,
        parse_adelaide_convention_centre,
        parse_adelaide_festival_centre,
        parse_hindley_st_music_hall,
        parse_adelaide_entertainment_centre,
        parse_coopers_stadium,
        parse_immersive_light_and_art,
        parse_adelaide_town_hall,
        parse_lion_arts_factory,
        parse_south_australia_tourism,
        parse_ticketmaster_adelaide,
        parse_experience_adelaide,
        parse_moshtix_adelaide,
    )


BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

EVENTS_FILE = os.path.join(
    BASE_DIR,
    "events.json"
)

BACKUP_FILE = os.path.join(
    BASE_DIR,
    "events.json.bak"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    )
}


def load_existing_events():

    if not os.path.exists(EVENTS_FILE):
        return []

    try:

        with open(
            EVENTS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(data, list):

            print(
                "WARNING: events.json does not contain a list."
            )

            return []

        return data

    except Exception as e:

        print(
            f"ERROR loading events.json: {e}"
        )

        return []


def save_events(events):

    # Create a backup before changing
    # the live database.

    if os.path.exists(EVENTS_FILE):

        try:

            shutil.copy2(
                EVENTS_FILE,
                BACKUP_FILE
            )

            print(
                f"Backup created: {BACKUP_FILE}"
            )

        except Exception as e:

            print(
                f"WARNING: Could not create backup: {e}"
            )

    temp_file = EVENTS_FILE + ".tmp"

    with open(
        temp_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            events,
            f,
            ensure_ascii=False,
            indent=2
        )

    os.replace(
        temp_file,
        EVENTS_FILE
    )

    print(
        f"Saved {len(events)} events."
    )


def clean_event(event, source_name):

    if not isinstance(event, dict):
        return None

    title = str(
        event.get("title", "")
    ).strip()

    venue = str(
        event.get("venue", "")
    ).strip()

    dt = str(
        event.get("datetime", "")
        or event.get("date", "")
    ).strip()

    link = str(
        event.get("link", "")
        or event.get("url", "")
    ).strip()

    image = str(
        event.get("image", "")
    ).strip()

    raw_category = event.get("category", "")

    # Preserve multiple categories from parsers.
    # Legacy single-string categories are converted to a one-item list.
    if isinstance(raw_category, (list, tuple, set)):
        category = []

        for value in raw_category:
            cleaned_category = str(value).strip()

            if (
                cleaned_category
                and cleaned_category not in category
            ):
                category.append(cleaned_category)

        if not category:
            category = ["Other"]

    else:
        cleaned_category = str(raw_category).strip()

        category = (
            [cleaned_category]
            if cleaned_category
            else ["Other"]
        )

    if not title:
        return None

    if not venue:
        venue = source_name

    end_dt = str(
        event.get("end_datetime", "")
        or event.get("end_date", "")
    ).strip()

    return {
        "title": title,
        "venue": venue,
        "datetime": dt,
        "end_datetime": end_dt,
        "category": category,
        "image": image,
        "link": link,
        "source": source_name,
    }


def event_key(event):

    return (
        str(
            event.get("title", "")
        ).lower().strip(),

        str(
            event.get("venue", "")
        ).lower().strip(),

        str(
            event.get("datetime", "")
        )[:10],
    )


def deduplicate_new_events(events):

    """
    Deduplicate ONLY newly scraped events.

    Existing events.json records are never
    globally deduplicated.
    """

    seen = set()
    result = []

    for event in events:

        key = event_key(event)

        if key in seen:
            continue

        seen.add(key)
        result.append(event)

    return result


# ------------------------------------------------------------
# Ticketmaster event-level filtering and source-aware matching
# ------------------------------------------------------------

def _venue_name(value):
    name = re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()
    aliases = {
        "hindley st music hall": "hindley street music hall",
        "immersive light and art ila": "immersive light and art",
        "98 port rd": "adelaide entertainment centre",
        "98 port road": "adelaide entertainment centre",
        "the gov": "governor hindmarsh hotel",
    }
    return aliases.get(name, name)


def _title_name(value):
    name = str(value).casefold().replace("&", " and ")
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return " ".join(name.split())


def _date(event):
    return str(event.get("datetime") or event.get("date") or "")[:10]


def _time(event):
    dt = str(event.get("datetime") or event.get("date") or "")
    match = re.search(r"T(\d{2}:\d{2})", dt)
    return match.group(1) if match and match.group(1) != "00:00" else None


def _date_within(event, official):
    date = _date(event)
    start = _date(official)
    end = str(official.get("end_datetime") or official.get("end_date") or "")[:10]
    return bool(date and start and start <= date <= (end or start))


def _similar_title(a, b):
    first, second = _title_name(a), _title_name(b)
    if not first or not second:
        return False
    if first == second:
        return True
    # Allow a short headliner title versus a longer official tour title,
    # but only with a meaningful, whole-word prefix.
    shorter, longer = sorted((first, second), key=len)
    if len(shorter) >= 9 and len(shorter.split()) >= 2 and longer.startswith(shorter + " "):
        return True
    return (len(first) >= 12 and len(second) >= 12
            and SequenceMatcher(None, first, second).ratio() >= 0.87)


def _same_event(ticket, official):
    if _venue_name(ticket.get("venue")) != _venue_name(official.get("venue")):
        return False
    if not _date_within(ticket, official):
        return False
    # Confirmed alternate ticketing titles at Hindley Street Music Hall.
    # Match only the same artist/show on the same date; never merge dates.
    ticket_title = _title_name(ticket.get("title"))
    official_title = _title_name(official.get("title"))
    known_same_show = (
        _venue_name(ticket.get("venue")) == "hindley street music hall"
        and (
            (ticket_title.startswith("dizzee rascal ")
             and official_title.startswith("dizzee rascal ")
             and "we want bass" in ticket_title
             and "we want bass" in official_title)
            or (ticket_title.startswith("swim ")
                and official_title.startswith("swim ")
                and "live solo show" in ticket_title
                and "live solo show" in official_title)
        )
    )
    if not known_same_show and not _similar_title(ticket.get("title"), official.get("title")):
        return False
    # A date-range official exhibition represents all its ticketed sessions.
    if str(official.get("end_datetime") or "")[:10] > _date(official):
        return True
    a, b = _time(ticket), _time(official)
    # Different explicit times may be distinct same-day performances.
    return not (a and b and a != b)


def _ticketmaster_consolidation(events):
    """Convert ticket options to events and omit a known VIP-only package."""
    result = []
    grand_final = []
    tennis = []
    for event in events:
        title = str(event.get("title", ""))
        venue = _venue_name(event.get("venue"))
        lower = title.casefold()
        if venue == "adelaide street circuit" and (
            "bp adelaide grand final" in lower or "bp adl gf" in lower
        ):
            grand_final.append(event)
            continue
        if venue == "adelaide street circuit" and "the jungle zone" in lower:
            continue
        if venue == "the drive" and "adelaide international 2027" in lower:
            tennis.append(event)
            continue
        result.append(event)
    if grand_final:
        exemplar = next((x for x in grand_final if "4-day" in x.get("title", "").casefold()), grand_final[0])
        event = dict(exemplar)
        event.update(title="bp Adelaide Grand Final", venue="Adelaide Street Circuit",
                     datetime="2026-11-26T00:00:00", end_datetime="2026-11-29T23:59:59",
                     category=["Sport"],
                     link="https://www.ticketmaster.com.au/AdelaideGrandFinal")
        result.append(event)
    if tennis:
        # Derive the observed span; do not invent dates beyond the API results.
        dates = sorted({_date(x) for x in tennis if _date(x)})
        if dates:
            event = dict(tennis[0])
            event.update(title="Adelaide International 2027", venue="The Drive",
                         datetime=dates[0] + "T00:00:00",
                         end_datetime=dates[-1] + "T23:59:59", category=["Sport"])
            result.append(event)
    return result, len(grand_final), len(tennis)


def filter_ticketmaster_events(all_events):
    """Prefer existing/updated venue records; keep separate dated shows."""
    official = [e for e in all_events if e.get("source") not in ("Ticketmaster Adelaide", "South Australia Tourism Commission")]
    tickets = [e for e in all_events if e.get("source") == "Ticketmaster Adelaide"]
    tickets, grand_count, tennis_count = _ticketmaster_consolidation(tickets)
    by_venue = {}
    for event in official:
        by_venue.setdefault(_venue_name(event.get("venue")), []).append(event)
    kept = []
    suppressed = 0
    for ticket in tickets:
        candidates = by_venue.get(_venue_name(ticket.get("venue")), [])
        if any(_same_event(ticket, other) for other in candidates):
            suppressed += 1
        else:
            kept.append(ticket)
    print(f"Ticketmaster: {suppressed} official-source overlaps excluded")
    print(f"Ticketmaster: {grand_count} Grand Final ticket options -> "
          f"{1 if grand_count else 0} event")
    print(f"Ticketmaster: {tennis_count} tennis sessions -> "
          f"{1 if tennis_count else 0} tournament")
    print(f"Ticketmaster: {len(kept)} listings retained after filtering")
    tourism = [e for e in all_events if e.get("source") == "South Australia Tourism Commission"]
    return official + kept + tourism


def fetch_page(url):

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True
        )

        response.raise_for_status()

        return BeautifulSoup(
            response.text,
            "lxml"
        )

    except Exception as e:

        raise RuntimeError(
            str(e)
        )


def scrape_source(source):

    name = source["name"]
    url = source["url"]

    if name == "Moshtix Adelaide CBD":
        return parse_moshtix_adelaide()

    # ----------------------------------------
    # Ticketmaster Adelaide (official API)
    # ----------------------------------------
    if name == "Ticketmaster Adelaide":
        return parse_ticketmaster_adelaide(os.environ.get("TICKETMASTER_API_KEY", ""))

    # ----------------------------------------
    # South Australia Tourism Commission
    # ----------------------------------------

    if name == "South Australia Tourism Commission":
        return parse_south_australia_tourism(None, url)

    # Experience Adelaide blocks automated HTTP access on some networks.
    # Only use the explicitly saved HTML snapshot when available.
    # If unavailable, preserve any previously collected records.
    if name == "Experience Adelaide":
        snapshot = os.path.join(BASE_DIR, "Experience Adelaide _ What's on in Adelaide.html")
        if not os.path.isfile(snapshot):
            raise RuntimeError("Saved HTML snapshot not found; HTTP 403 remains unresolved")
        with open(snapshot, "r", encoding="utf-8") as handle:
            soup = BeautifulSoup(handle.read(), "lxml")
        return parse_experience_adelaide(soup, url)

    # ----------------------------------------
    # Adelaide Oval
    # ----------------------------------------

    if name == "Adelaide Oval":

        soup = fetch_page(url)

        return parse_adelaide_oval(
            soup,
            url
        )

    # ----------------------------------------
    # Adelaide Convention Centre
    # ----------------------------------------

    if name == "Adelaide Convention Centre":

        soup = fetch_page(url)

        return parse_adelaide_convention_centre(
            soup,
            url
        )

    # ----------------------------------------
    # Adelaide Festival Centre
    # ----------------------------------------

    if name == "Adelaide Festival Centre":

        soup = fetch_page(url)

        return parse_adelaide_festival_centre(
            soup,
            url
        )

    # ----------------------------------------
    # Hindley Street Music Hall
    # ----------------------------------------

    if name == "Hindley St Music Hall":

        soup = fetch_page(url)

        return parse_hindley_st_music_hall(soup, url)

    # ----------------------------------------
    # Adelaide Entertainment Centre
    # ----------------------------------------

    if name == "Adelaide Entertainment Centre":

        soup = fetch_page(url)

        return parse_adelaide_entertainment_centre(
            soup,
            url
        )

    # ----------------------------------------
    # Coopers Stadium
    # ----------------------------------------

    if name == "Coopers Stadium":

        soup = fetch_page(url)

        return parse_coopers_stadium(soup, url)

    # ----------------------------------------
    # Immersive Light and Art (ILA)
    # ----------------------------------------

    if name == "Immersive Light and Art":
        soup = fetch_page("https://immersivelightandart.com.au/whats-on/")
        return parse_immersive_light_and_art(soup, "https://immersivelightandart.com.au/whats-on/")

    # ----------------------------------------
    # Adelaide Town Hall
    # ----------------------------------------

    if name == "Adelaide Town Hall":
        soup = fetch_page(url)
        return parse_adelaide_town_hall(soup, url)

    # ----------------------------------------
    # Lion Arts Factory
    # ----------------------------------------

    if name == "Lion Arts Factory":
        soup = fetch_page(url)
        return parse_lion_arts_factory(soup, url)

    # ----------------------------------------
    # Generic JSON-LD parser
    # ----------------------------------------

    soup = fetch_page(url)

    return parse_json_ld(
        soup,
        url
    )


def source_domains(source_name):
    """
    Return the official hostname(s) configured for a source.
    """
    domains = set()

    for source in list(SOURCES) + [{"name": "Moshtix Adelaide CBD", "url": "https://www.moshtix.com.au/v2/search"}]:
        if source.get("name") != source_name:
            continue

        hostname = urlparse(
            str(source.get("url", ""))
        ).hostname

        if hostname:
            hostname = hostname.lower()
            if hostname.startswith("www."):
                hostname = hostname[4:]
            domains.add(hostname)

    return domains


def event_belongs_to_source(event, source_name):
    """
    Identify an existing event's scraper source safely.

    New records carry an explicit `source` field. Older records may
    not, so fall back to their official event URL/domain, and finally
    to exact venue matching for legacy records.
    """
    wanted = source_name.strip().lower()

    explicit_source = str(
        event.get("source", "")
    ).strip().lower()

    if explicit_source == wanted:
        return True

    # Do not return False merely because an older record has a
    # different/missing source label. Its official URL may still
    # identify the correct scraper source.
    link = str(
        event.get("link", "")
        or event.get("url", "")
    ).strip()

    if link:
        try:
            hostname = (
                urlparse(link).hostname
                or ""
            ).lower()

            if hostname.startswith("www."):
                hostname = hostname[4:]

            for domain in source_domains(source_name):
                if (
                    hostname == domain
                    or hostname.endswith("." + domain)
                ):
                    return True

        except Exception:
            pass

    # Legacy fallback only.
    venue = str(
        event.get("venue", "")
    ).strip().lower()

    return venue == wanted


def source_event_count(
    existing_events,
    source_name
):
    return sum(
        1
        for event in existing_events
        if event_belongs_to_source(
            event,
            source_name
        )
    )

def source_is_safe_to_replace(
    existing_count,
    fresh_count
):

    """
    Protect the existing database from
    broken scrapers.

    Rules:

    - No existing records:
      accept fresh results.

    - Fewer than 10 existing records:
      accept fresh results.

    - 10+ existing records:
      require at least 50% of previous count.

    - Zero fresh events:
      never replace an existing source.
    """

    if existing_count == 0:
        return True

    if fresh_count == 0:
        return False

    if existing_count < 10:
        return True

    minimum_required = max(
        1,
        int(existing_count * 0.5)
    )

    return fresh_count >= minimum_required


def write_preview_report(existing_events, proposed_events):
    """Write a read-only-to-database comparison for human review."""
    from collections import defaultdict

    def identity(event):
        return event_key(event)

    def describe(event):
        return {
            "title": event.get("title", ""),
            "venue": event.get("venue", ""),
            "datetime": event.get("datetime", ""),
            "end_datetime": event.get("end_datetime", ""),
            "source": event.get("source", ""),
            "link": event.get("link", ""),
        }

    old_by_key = defaultdict(list)
    new_by_key = defaultdict(list)
    for event in existing_events:
        old_by_key[identity(event)].append(event)
    for event in proposed_events:
        new_by_key[identity(event)].append(event)

    added, removed, updated, unchanged = [], [], [], 0
    for key in sorted(set(old_by_key) | set(new_by_key)):
        old_items = old_by_key[key]
        new_items = new_by_key[key]
        common = min(len(old_items), len(new_items))
        for index in range(common):
            old, new = old_items[index], new_items[index]
            if old == new:
                unchanged += 1
            else:
                updated.append({"before": describe(old), "after": describe(new)})
        removed.extend(describe(event) for event in old_items[common:])
        added.extend(describe(event) for event in new_items[common:])

    # Audit possible Ticketmaster/official overlaps without deleting them.
    # This is intentionally review-only: separate shows must remain intact.
    official = [e for e in proposed_events if e.get("source") not in
                ("Ticketmaster Adelaide", "South Australia Tourism Commission")]
    tickets = [e for e in proposed_events if e.get("source") == "Ticketmaster Adelaide"]
    possible_overlaps = []
    for ticket in tickets:
        for venue_event in official:
            if _venue_name(ticket.get("venue")) != _venue_name(venue_event.get("venue")):
                continue
            if not _date_within(ticket, venue_event):
                continue
            ticket_time, official_time = _time(ticket), _time(venue_event)
            if ticket_time and official_time and ticket_time != official_time:
                continue
            a = _title_name(ticket.get("title"))
            b = _title_name(venue_event.get("title"))
            if not a or not b:
                continue
            words_a, words_b = set(a.split()), set(b.split())
            shared = words_a & words_b
            meaningful = {w for w in shared if len(w) >= 4 and w not in
                          {"tour", "live", "with", "show", "music", "2026", "2027", "adelaide"}}
            score = SequenceMatcher(None, a, b).ratio()
            if score >= 0.52 or len(meaningful) >= 2:
                possible_overlaps.append({
                    "ticketmaster": describe(ticket),
                    "official": describe(venue_event),
                    "title_similarity": round(score, 3),
                    "review_only": True,
                })

    report = {
        "note": "Exact title + venue + date comparison. Renamed or re-venued events may appear in both added and removed; review manually before saving.",
        "existing_total": len(existing_events),
        "proposed_total": len(proposed_events),
        "unchanged_count": unchanged,
        "updated_count": len(updated),
        "added_count": len(added),
        "removed_count": len(removed),
        "possible_ticketmaster_overlaps": possible_overlaps,
        "possible_ticketmaster_overlaps_count": len(possible_overlaps),
        "removed": removed,
        "added": added,
        "updated": updated,
    }
    path = os.path.join(BASE_DIR, "events-preview-report.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)

    print("\nPREVIEW REPORT (exact title/venue/date comparison)")
    print(f"Unchanged: {unchanged} | Updated: {len(updated)} | Added: {len(added)} | Removed: {len(removed)}")
    print("Renamed or re-venued events can appear as both added and removed.")
    print(f"Possible Ticketmaster overlaps to review: {len(possible_overlaps)}")
    print(f"Report saved to: {path}")
    print("events.json was NOT changed.")


def main():

    print("========================================")
    print(" Adelaide Events Scraper")
    print("========================================")
    print()

    existing_events = load_existing_events()

    print(
        f"Existing events: "
        f"{len(existing_events)}"
    )

    print()

    accepted_sources = {}
    all_new_events = []

    # ----------------------------------------
    # Scrape all configured sources
    # ----------------------------------------

    for source in list(SOURCES) + [{"name": "Moshtix Adelaide CBD", "url": "https://www.moshtix.com.au/v2/search"}]:

        name = source["name"]

        print(
            f"{name} -> ",
            end="",
            flush=True
        )

        try:

            fresh_events = scrape_source(
                source
            )

            if fresh_events is None:
                fresh_events = []

        except Exception as e:

            print(
                f"ERROR: {e}, "
                f"preserved existing"
            )

            continue

        cleaned_events = []

        for event in fresh_events:

            cleaned = clean_event(
                event,
                name
            )

            if cleaned:

                cleaned_events.append(
                    cleaned
                )

        # Deduplicate only newly scraped
        # records.

        cleaned_events = (
            deduplicate_new_events(
                cleaned_events
            )
        )

        existing_count = (
            source_event_count(
                existing_events,
                name
            )
        )

        fresh_count = len(
            cleaned_events
        )

        if fresh_count == 0:

            print(
                f"Found 0, "
                f"preserved existing "
                f"{existing_count}"
            )

            continue

        if source_is_safe_to_replace(
            existing_count,
            fresh_count
        ):

            accepted_sources[name] = True

            all_new_events.extend(
                cleaned_events
            )

            print(
                f"Found {fresh_count}; "
                f"existing {existing_count}, "
                f"fresh {fresh_count}, "
                f"ACCEPT"
            )

        else:

            print(
                f"Found {fresh_count}; "
                f"existing {existing_count}, "
                f"fresh {fresh_count}, "
                f"REJECTED - preserved existing"
            )

    # ----------------------------------------
    # Deduplicate newly scraped events only
    # ----------------------------------------

    all_new_events = (
        deduplicate_new_events(
            all_new_events
        )
    )

    print()

    print("----------------------------------------")

    print(
        f"New scraped events: "
        f"{len(all_new_events)}"
    )

    print()

    print("Accepted sources:")

    if accepted_sources:

        for name in accepted_sources:

            print(
                f"  + {name}"
            )

    else:

        print("  None")

    print()

    # ----------------------------------------
    # Build final database
    #
    # Existing events are NOT globally
    # deduplicated.
    # ----------------------------------------

    final_events = []

    removed_existing = 0

    for event in existing_events:

        replace_event = any(
            event_belongs_to_source(
                event,
                source_name
            )
            for source_name in accepted_sources
        )

        if replace_event:

            removed_existing += 1

            continue

        # Preserve existing record exactly.

        final_events.append(
            event
        )

    # Add newly scraped events.

    final_events.extend(
        all_new_events
    )

    # ----------------------------------------
    # Final exact-event deduplication
    # ----------------------------------------
    #
    # Some events can be discovered through more than one
    # configured source or can survive from older scraper
    # versions under a different source identity.
    #
    # Keep one record for each exact:
    # title + venue + calendar date.
    # ----------------------------------------

    before_final_dedup = len(final_events)

    # Prefer freshly scraped records when an old and fresh record
    # describe the same exact event. Fresh records contain the newest
    # source metadata, links and end dates.
    deduplicated_final_events = []
    final_seen = set()

    # Prefer official fresh records to Ticketmaster for identical keys.
    for event in sorted(all_new_events, key=lambda e: e.get("source") in ("Ticketmaster Adelaide", "Moshtix Adelaide CBD")):

        key = event_key(event)

        if key in final_seen:
            continue

        final_seen.add(key)
        deduplicated_final_events.append(
            event
        )

    # Then preserve non-duplicate existing records.
    for event in final_events:

        key = event_key(event)

        if key in final_seen:
            continue

        final_seen.add(key)
        deduplicated_final_events.append(
            event
        )

    # Moshtix is a ticketing aggregator: prefer official venue records.
    # Compare normalized title, venue, date, and non-conflicting times.
    moshtix = [e for e in deduplicated_final_events if e.get("source") == "Moshtix Adelaide CBD"]
    non_moshtix = [e for e in deduplicated_final_events if e.get("source") != "Moshtix Adelaide CBD"]
    official_for_moshtix = [e for e in non_moshtix if e.get("source") not in
                            ("Ticketmaster Adelaide", "South Australia Tourism Commission")]
    kept_moshtix = []
    skipped_moshtix = 0
    for candidate in moshtix:
        if any(_same_event(candidate, existing) for existing in official_for_moshtix):
            skipped_moshtix += 1
        else:
            kept_moshtix.append(candidate)
    print(f"Moshtix: {skipped_moshtix} official-source overlaps excluded")
    deduplicated_final_events = non_moshtix + kept_moshtix

    deduplicated_final_events = filter_ticketmaster_events(deduplicated_final_events)

    # Tourism is an aggregator. Compare it against EVERY non-Tourism
    # source, including any sources added in the future. Prefer the
    # venue/organiser listing where the evidence supports a match.
    # Keep distinct performances and avoid speculative title matches.
    import re
    from difflib import SequenceMatcher

    def comparable_title(value):
        value = str(value).casefold().replace("&", " and ")
        value = re.sub(r"\b(20\d{2})\b", " ", value)
        value = re.sub(r"[^a-z0-9]+", " ", value)
        return " ".join(value.split())

    def comparable_venue(value):
        value = str(value).casefold().replace("&", " and ")
        value = re.sub(r"[^a-z0-9]+", " ", value)
        value = " ".join(value.split())
        # Known Tourism street addresses and their official venue names.
        aliases = {
            "98 port road": "adelaide entertainment centre",
            "98 port rd": "adelaide entertainment centre",
            "58 grote street": "her majesty s theatre",
            "58 grote st": "her majesty s theatre",
            "festival drive": "adelaide festival centre precinct",
            "king william street": "king william street",
        }
        return aliases.get(value, value)

    def performance_time(event):
        value = str(event.get("datetime", ""))
        # Midnight from the Tourism feed often means 'time unspecified',
        # rather than an actual midnight performance.
        match = re.search(r"T(\d{2}):(\d{2})", value)
        if not match or match.group(0) == "T00:00":
            return None
        return match.group(1) + ":" + match.group(2)

    def same_performance(tourism_event, official_event):
        first = performance_time(tourism_event)
        second = performance_time(official_event)
        # If both sites specify different times, they may be separate
        # performances; do not silently discard either listing.
        return not (first and second and first != second)

    def tourism_matches_official(tourism_event, official_event):
        if str(tourism_event.get("datetime", ""))[:10] != str(
            official_event.get("datetime", "")
        )[:10]:
            return False
        if not same_performance(tourism_event, official_event):
            return False

        title = comparable_title(tourism_event.get("title", ""))
        other = comparable_title(official_event.get("title", ""))
        # Tourism may prepend the festival name to an individual show.
        # Compare the specific activity, never the festival name alone.
        festival_prefix = r"^ozasia festival(?: 20\d{2})? "
        if re.match(festival_prefix, title):
            activity = re.sub(festival_prefix, "", title).strip()
            # Only strip the prefix for a sufficiently distinctive activity.
            if len(activity) >= 12 and len(activity.split()) >= 2:
                title = activity
        if not title or not other:
            return False

        venue = comparable_venue(tourism_event.get("venue", ""))
        official_venue = comparable_venue(official_event.get("venue", ""))
        same_venue = bool(venue and official_venue and venue == official_venue)

        # Explicitly confirmed festival activity with different wording.
        if ("moon lantern" in title and "moon lantern" in other
                and "lucky dumpling market" in title
                and "lucky dumpling market" in other):
            return True

        similarity = SequenceMatcher(None, title, other).ratio()
        # When venues are demonstrably the same, allow minor title edits.
        if same_venue and (title == other or (
            len(title) >= 14 and len(other) >= 14 and similarity >= 0.88
        )):
            return True

        # Tourism often gives a street address instead of a venue name.
        # Require a near-exact title if the venue cannot be confirmed.
        if title == other and len(title) >= 12:
            return True
        if (len(title) >= 18 and len(other) >= 18
                and similarity >= 0.94):
            return True
        return False

    non_tourism = [
        e for e in deduplicated_final_events
        if e.get("source") != "South Australia Tourism Commission"
    ]
    tourism = [
        e for e in deduplicated_final_events
        if e.get("source") == "South Australia Tourism Commission"
    ]
    by_date = {}
    for event in non_tourism:
        by_date.setdefault(str(event.get("datetime", ""))[:10], []).append(event)

    kept_tourism = []
    tourism_duplicates = 0
    for event in tourism:
        same_day = by_date.get(str(event.get("datetime", ""))[:10], [])
        if any(tourism_matches_official(event, original) for original in same_day):
            tourism_duplicates += 1
        else:
            kept_tourism.append(event)

    final_events = non_tourism + kept_tourism

    # Experience Adelaide is an aggregator: prefer official venues and
    # existing Ticketmaster/tourism listings for the same named event.
    # Compare overlapping calendar ranges, not just the first day.
    def experience_identity(value):
        name = comparable_title(value)
        if name.startswith("ozasia festival "):
            name = re.sub(r"^ozasia festival(?: 20\\d{2})? ", "", name)
        if name.startswith("adelaide international"):
            name = re.sub(r"\\s+2027$", "", name)
        aliases = {"moon lantern at lucky dumpling market":
                   "moon lanterns at lucky dumpling market"}
        return aliases.get(name, name)

    def overlaps(a, b):
        a_start = _date(a)
        b_start = _date(b)
        a_end = str(a.get("end_datetime") or "")[:10] or a_start
        b_end = str(b.get("end_datetime") or "")[:10] or b_start
        return bool(a_start and b_start and a_start <= b_end and b_start <= a_end)

    def experience_same(a, b):
        first = experience_identity(a.get("title", ""))
        second = experience_identity(b.get("title", ""))
        if not first or not second or not overlaps(a, b):
            return False
        # Never collapse different named festival activities.
        if first != second and not (
            len(first) >= 18 and len(second) >= 18
            and SequenceMatcher(None, first, second).ratio() >= 0.94
        ):
            return False
        return same_performance(a, b)

    authoritative = [e for e in final_events
                     if e.get("source") != "Experience Adelaide"]
    experience = [e for e in final_events
                  if e.get("source") == "Experience Adelaide"]
    kept_experience = []
    skipped_experience = 0
    for event in experience:
        if any(experience_same(event, other)
               for other in authoritative + kept_experience):
            skipped_experience += 1
        else:
            kept_experience.append(event)
    final_events = authoritative + kept_experience
    print(f"Experience Adelaide overlaps excluded: {skipped_experience}")
    print(f"Tourism duplicates excluded: {tourism_duplicates}")

    final_duplicates_removed = (
        before_final_dedup
        - len(final_events)
    )

    print(
        f"Legacy/exact duplicates replaced by fresh records: "
        f"{final_duplicates_removed}"
    )

    # ----------------------------------------
    # Final safety check
    # ----------------------------------------

    # Safety is evaluated against the merged database BEFORE
    # intentional exact-duplicate removal. This prevents a valid
    # cleanup of duplicate records from being mistaken for data loss.
    safety_count = before_final_dedup

    minimum_safe_total = max(
        50,
        int(
            len(existing_events) * 0.5
        )
    )

    if safety_count < minimum_safe_total:

        print(
            "========================================"
        )

        print(
            " SAFETY STOP"
        )

        print(
            "========================================"
        )

        print(
            f"Merged event count before duplicate cleanup "
            f"would be {safety_count}."
        )

        print(
            f"Minimum safe count is "
            f"{minimum_safe_total}."
        )

        print()

        print(
            "events.json was NOT changed."
        )

        print()

        return

    # ----------------------------------------
    # Save final database
    # ----------------------------------------

    print(
        "----------------------------------------"
    )

    print(
        f"Existing events: "
        f"{len(existing_events)}"
    )

    print(
        f"Removed from accepted sources: "
        f"{removed_existing}"
    )

    print(
        f"Fresh events added: "
        f"{len(all_new_events)}"
    )

    print(
        f"Final events: "
        f"{len(final_events)}"
    )

    print()

    if "--preview-report" in sys.argv or "--preview" in sys.argv:
        write_preview_report(existing_events, final_events)
        print("DRY RUN: events.json was NOT changed.")
        return

    if "--dry-run" in sys.argv:
        print("DRY RUN: events.json was NOT changed.")
        return

    save_events(
        final_events
    )

    print()

    print(
        "Scrape complete."
    )


if __name__ == "__main__":
    allowed = {"--preview-report", "--preview", "--dry-run"}
    unknown = [arg for arg in sys.argv[1:] if arg not in allowed]
    if unknown:
        print(f"ERROR: Unknown option(s): {', '.join(unknown)}")
        print("Use --preview, --preview-report, or --dry-run.")
        sys.exit(2)
    main()