import json
import re
import sys
from difflib import SequenceMatcher
from datetime import datetime
import os
import shutil
import time
from email.utils import parsedate_to_datetime
from datetime import timezone
import requests
from urllib.parse import urlparse

from bs4 import BeautifulSoup

try:
    from humanitix import scrape_humanitix
except ModuleNotFoundError:
    from Scraper.humanitix import scrape_humanitix

try:
    # Works when running:
    # python Scraper\scrape.py
    from config import SOURCES
    from parsers import (
        parse_json_ld,
        parse_a_day_on_the_green,
        parse_adelaide_showground,
        parse_adelaide_zoo,
        parse_ace_gallery,
        parse_fever_candlelight,
        parse_adelaide_central_market,
        parse_david_roche_gallery,
        parse_the_drive,
        parse_adelaide_symphony_orchestra,
        parse_state_opera_south_australia,
        parse_government_house,
        parse_nexus_arts,
        parse_dom_polski_centre,
        parse_kings_of_comedy,
        parse_adelaide_repertory_theatre,
        parse_state_theatre_company,
        parse_south_australian_museum,
        parse_art_gallery_south_australia,
        STATE_THEATRE_OFFICIAL_IMAGES,
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
        parse_thebarton_theatre,
        parse_experience_adelaide,
        parse_moshtix_adelaide,
        parse_the_gov,
        parse_norwood_concert_hall,
        parse_trinity_sessions,
        parse_morphettville_racecourse,
        parse_gilles_at_the_grounds,
        parse_unibar_adelaide,
        parse_arkaba_hotel,
        parse_rhino_room,
        parse_jive,
        parse_national_trust_sa,
        parse_carrick_hill,
        parse_jetty_road_glenelg,
        parse_oztix_adelaide_city,
        parse_plant_4_bowden,
        parse_plant_3_bowden,
        parse_mod_museum,
        parse_samstag_museum,
        parse_kerry_packer_civic_gallery,
        parse_the_district_skycity,
        parse_allevents_victoria_square,
        parse_allevents_adelaide_and_surrounds,
        parse_national_wine_centre,
        parse_adelaide_fringe,
        parse_adelaide_festival,
        parse_illuminate_adelaide,
        parse_adelaide_botanic_gardens,
        parse_moonlight_cinema_adelaide,
        parse_adelaide_gaol,
        parse_play_and_go_major_events,
        parse_army_museum_south_australia,
        parse_migration_museum_adelaide,
        parse_south_australian_maritime_museum,
        parse_south_australian_aviation_museum,
        parse_national_railway_museum,
        parse_sala_festival,
    )
except ModuleNotFoundError:
    # Works when importing:
    # from Scraper.scrape import ...
    from Scraper.config import SOURCES
    from Scraper.parsers import (
        parse_json_ld,
        parse_a_day_on_the_green,
        parse_adelaide_showground,
        parse_adelaide_zoo,
        parse_ace_gallery,
        parse_fever_candlelight,
        parse_adelaide_central_market,
        parse_david_roche_gallery,
        parse_the_drive,
        parse_adelaide_symphony_orchestra,
        parse_state_opera_south_australia,
        parse_government_house,
        parse_nexus_arts,
        parse_dom_polski_centre,
        parse_kings_of_comedy,
        parse_adelaide_repertory_theatre,
        parse_state_theatre_company,
        parse_south_australian_museum,
        parse_art_gallery_south_australia,
        STATE_THEATRE_OFFICIAL_IMAGES,
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
        parse_thebarton_theatre,
        parse_experience_adelaide,
        parse_moshtix_adelaide,
        parse_the_gov,
        parse_norwood_concert_hall,
        parse_trinity_sessions,
        parse_morphettville_racecourse,
        parse_gilles_at_the_grounds,
        parse_unibar_adelaide,
        parse_arkaba_hotel,
        parse_rhino_room,
        parse_jive,
        parse_national_trust_sa,
        parse_carrick_hill,
        parse_jetty_road_glenelg,
        parse_oztix_adelaide_city,
        parse_plant_4_bowden,
        parse_plant_3_bowden,
        parse_mod_museum,
        parse_samstag_museum,
        parse_kerry_packer_civic_gallery,
        parse_the_district_skycity,
        parse_allevents_victoria_square,
        parse_allevents_adelaide_and_surrounds,
        parse_national_wine_centre,
        parse_adelaide_fringe,
        parse_adelaide_festival,
        parse_illuminate_adelaide,
        parse_adelaide_botanic_gardens,
        parse_moonlight_cinema_adelaide,
        parse_adelaide_gaol,
        parse_play_and_go_major_events,
        parse_army_museum_south_australia,
        parse_migration_museum_adelaide,
        parse_south_australian_maritime_museum,
        parse_south_australian_aviation_museum,
        parse_national_railway_museum,
        parse_sala_festival,
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


# Curated, event-specific category corrections. Applied at save time so they
# also correct records retained when a source cannot be refreshed.
# Booking URLs are matched by host and path (query strings are ignored).
COMEDY_BOOKING_PATHS = {
    ("ti.to", "/cypriot-smurf/adelaide"),
    ("events.humanitix.com", "/do-you-know-who-i-am-by-daniel-fernandes"),
    ("lewspears.com", "/products/spears-in-the-city-friday-27-november-8-30pm-adelaide"),
    ("www.eventbrite.com.au", "/e/steve-hofstetter-at-rhino-room-adelaide-tickets-1985565084618"),
    ("events.humanitix.com", "/drew-lynch-adelaide"),
    ("events.humanitix.com", "/josh-wolf-touring-hard"),
    ("events.humanitix.com", "/barry-castagnola-the-last-of-the-barrys"),
}

# Distinctive show/performer titles also cover aggregator records linking to
# a different ticketing page. Avoid broad words such as "tour" or "Adelaide".
COMEDY_TITLE_PATTERNS = (
    r"\bcypriot\s+smurf\b",
    r"\bdaniel\s+fernandes\b",
    r"\bspears\s+in\s+the\s+city\b",
    r"\bsteve\s+hofstetter\b",
    r"\bdrew\s+lynch\b",
    r"\bjosh\s+wolf\b",
    r"\bbarry\s+castagnola\b",
)


def correct_comedy_category(event):
    """Force only the seven identified stand-up shows into Comedy."""
    title = str(event.get("title") or "")
    link = str(event.get("link") or event.get("url") or "")
    parsed = urlparse(link)
    host = (parsed.hostname or "").casefold()
    path = parsed.path.rstrip("/").casefold()
    known_link = (host, path) in COMEDY_BOOKING_PATHS
    known_title = any(re.search(pattern, title, re.I) for pattern in COMEDY_TITLE_PATTERNS)
    if known_link or known_title:
        event["category"] = ["Comedy"]
        return True
    return False


def correct_verified_event_dates(event):
    """Exact event-specific correction; do not truncate genuine long seasons."""
    if str(event.get("title") or "").strip().casefold() == "glam, gin & drag bingo at prohibition liquor co.":
        event["datetime"] = "2026-11-07T16:00:00"
        event["end_datetime"] = "2026-11-07T18:30:00"
        return True
    return False


def apply_verified_recurring_sessions(events):
    """Expand ONLY dates explicitly confirmed in recurring_sessions.json.

    No inferred weekly/monthly dates, and no alteration of unverified listings.
    The manifest is a curated list of individual occurrences, not a date span.
    """
    manifest_path = os.path.join(BASE_DIR, "recurring_sessions.json")
    if not os.path.isfile(manifest_path):
        return events
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    # Additional official recurrence rules are generated only within a rolling
    # 120-day window, rather than treating a season as one continuous event.
    rules_path = os.path.join(BASE_DIR, "recurring_rules.json")
    rules = {}
    if os.path.isfile(rules_path):
        with open(rules_path, encoding="utf-8") as handle:
            rules = json.load(handle)
    # Official National Trust SA schedules. These defaults supplement the
    # existing recurring_rules.json without replacing its other entries.
    # The 2026 listing end dates cap the generated occurrences.
    verified_heritage_rules = {
        "https://www.nationaltrust.org.au/event/beaumont-house-open-day": {
            "start": "2026-02-01", "end": "2026-12-06",
            "frequency": "nth_weekday", "weekday": 6, "nth": 1,
            "months": list(range(2, 13)),
            "start_time": "14:00:00", "end_time": "16:30:00"
        },
        "https://www.nationaltrust.org.au/event/watchman-house": {
            "start": "2026-02-07", "end": "2026-12-05",
            "frequency": "nth_weekday", "weekday": 5, "nth": 1,
            "months": list(range(2, 13)),
            "start_time": "00:00:00", "end_time": ""
        }
    }
    for heritage_url, heritage_rule in verified_heritage_rules.items():
        rules.setdefault(heritage_url, heritage_rule)
    from datetime import date, timedelta
    today = date.today()
    horizon = today + timedelta(days=120)

    def rule_dates(rule):
        first = max(today, date.fromisoformat(rule["start"]))
        last = min(horizon, date.fromisoformat(rule["end"]))
        excluded = set(rule.get("exclude", []))
        dates = []
        day = first
        while day <= last:
            freq = rule["frequency"]
            match = (freq == "daily"
                     or (freq == "weekly" and day.weekday() == rule["weekday"])
                     or (freq == "last_weekday" and day.weekday() == rule["weekday"]
                         and (day + timedelta(days=7)).month != day.month)
                     or (freq == "nth_weekday" and day.weekday() == rule["weekday"]
                         and (day.day - 1) // 7 + 1 == rule["nth"]
                         and day.month in rule.get("months", list(range(1, 13)))))
            if match and day.isoformat() not in excluded:
                dates.append(day.isoformat())
            day += timedelta(days=1)
        return dates

    # Group by exact listing URL before expansion. On subsequent runs, the
    # existing database already contains one record per occurrence; expanding
    # each of those records would multiply the same dates many times.
    from collections import defaultdict
    grouped = defaultdict(list)
    passthrough = []
    for event in events:
        url = str(event.get("link") or event.get("url") or "").split("?", 1)[0].rstrip("/")
        if url in rules or url in manifest:
            grouped[url].append(event)
        else:
            passthrough.append(event)

    output = list(passthrough)
    generated = 0
    for url, existing in grouped.items():
        rule = rules.get(url)
        record = manifest.get(url)
        if rule is not None:
            record = {"dates": rule_dates(rule),
                      "start_time": rule["start_time"],
                      "end_time": rule.get("end_time", "")}
        if not record or not record.get("dates"):
            # Do not resurrect a broad, outdated date span when the rule ends.
            # Preserve already dated future occurrences, if any.
            for event in existing:
                start = str(event.get("datetime") or "")[:10]
                end = str(event.get("end_datetime") or "")[:10]
                if start >= today.isoformat() and (not end or end == start):
                    output.append(event)
            continue

        # Prefer the source's original season listing as the template, if
        # present, rather than an already-expanded dated session.
        def template_quality(event):
            start = str(event.get("datetime") or "")[:10]
            end = str(event.get("end_datetime") or "")[:10]
            return (int(bool(end and end > start)),
                    int(bool(event.get("image"))),
                    len(str(event.get("title") or "")))
        template = max(existing, key=template_quality)
        for day in sorted(set(record["dates"])):
            try:
                datetime.strptime(day, "%Y-%m-%d")
                start_time = record["start_time"]
                end_time = record.get("end_time")
                datetime.strptime(start_time, "%H:%M:%S")
                if end_time:
                    datetime.strptime(end_time, "%H:%M:%S")
            except (ValueError, TypeError, KeyError):
                raise ValueError("Invalid verified recurring session for " + url)
            occurrence = template.copy()
            occurrence["datetime"] = day + "T" + start_time
            occurrence["end_datetime"] = day + "T" + end_time if end_time else ""
            output.append(occurrence)
            generated += 1

    seen = set()
    unique = []
    for event in output:
        key = (str(event.get("title", "")).casefold(),
               str(event.get("venue", "")).casefold(),
               str(event.get("datetime", "")),
               str(event.get("link") or event.get("url") or "").split("?", 1)[0])
        if key not in seen:
            seen.add(key)
            unique.append(event)
    print(f"Verified recurring sessions generated: {generated} from {len(grouped)} listings")
    return unique


# Local, dependable artwork for the recurring District trivia sessions.
# The asset is hosted in this project's own GitHub Pages root, avoiding
# third-party hotlink restrictions and image URLs that change over time.
DISTRICT_TRIVIA_IMAGE = (
    "https://conciergeadelaide.github.io/adelaide-events/quizmeisters-trivia.svg"
)


def apply_district_trivia_image(events):
    updated = 0
    for event in events:
        if (str(event.get("source") or "") == "The District at SkyCity"
                and str(event.get("title") or "").strip().casefold()
                == "quizmeisters trivia at the district"
                and "district" in str(event.get("venue") or "").casefold()):
            if event.get("image") != DISTRICT_TRIVIA_IMAGE:
                event["image"] = DISTRICT_TRIVIA_IMAGE
                updated += 1
    print(f"District QuizMeisters: {updated} event images set to local artwork")
    return events


def repair_missing_event_images(events):
    """Assign local generic artwork to missing or non-HTTP image values.

    Preserve valid absolute HTTP(S) image URLs; replace relative paths and data URIs.
    Files are hosted in this GitHub Pages repository.
    """
    artwork = {
        "State Theatre Company South Australia": "state-theatre-event.svg",
        "Play & Go Adelaide Major Events": "adelaide-major-events.svg",
    }
    counts = {name: 0 for name in artwork}
    for event in events:
        source = str(event.get("source") or "")
        if source in artwork and not str(event.get("image") or "").strip().lower().startswith(("https://", "http://")):
            event["image"] = (
                "https://conciergeadelaide.github.io/adelaide-events/"
                + artwork[source]
            )
            counts[source] += 1
    for source, count in counts.items():
        print(f"Local fallback artwork: {source}: {count} missing images repaired")
    return events


# Targeted correction for a confirmed broken Moshtix event image (HTTP 404).
# Only the exact event with the bad directory URL is changed.
MOSHTIX_LISA_HILL_IMAGE = (
    "https://conciergeadelaide.github.io/adelaide-events/moshtix-big-room.svg"
)


def repair_confirmed_broken_moshtix_image(events):
    repaired = 0
    for event in events:
        if (str(event.get("source") or "") == "Moshtix Adelaide CBD"
                and str(event.get("title") or "").strip().casefold()
                == "big room w/ lisa hill (18+)"
                and str(event.get("link") or event.get("url") or "").split("?", 1)[0]
                == "https://www.moshtix.com.au/v2/event/big-room-w-lisa-hill-18/201022"
                and str(event.get("image") or "").strip().rstrip("/")
                == "https://www.moshtix.com.au/uploads"):
            event["image"] = MOSHTIX_LISA_HILL_IMAGE
            repaired += 1
    print(f"Moshtix BIG ROOM: {repaired} confirmed broken image(s) repaired")
    return events


def save_events(events):
    events = apply_verified_recurring_sessions(events)
    events = repair_missing_event_images(events)
    events = apply_district_trivia_image(events)
    events = repair_confirmed_broken_moshtix_image(events)
    verified_date_fixes = sum(correct_verified_event_dates(event) for event in events)
    if verified_date_fixes:
        print(f"Verified event date corrections applied: {verified_date_fixes}")
    # Keep a separate archive of past events from earlier successful runs.
    # Do not change the current events.json merge/deduplication rules.
    from datetime import date
    archive_file = os.path.join(BASE_DIR, "historical_events.json")
    today_key = date.today().isoformat()
    def is_past(record):
        end = str(record.get("end_datetime") or record.get("end_date") or record.get("datetime") or record.get("date") or "")[:10]
        return bool(end and end < today_key)
    def archive_key(record):
        return tuple(str(record.get(k) or "").strip().casefold() for k in ("title", "venue", "datetime", "link"))
    archived = []
    for file_path in (archive_file, EVENTS_FILE):
        if os.path.isfile(file_path):
            try:
                with open(file_path, encoding="utf-8") as source:
                    records = json.load(source)
                if isinstance(records, list):
                    archived.extend(r for r in records if isinstance(r, dict) and is_past(r))
            except (OSError, ValueError) as exc:
                print(f"WARNING: Cannot read history from {file_path}: {exc}")
    archived.extend(r for r in events if isinstance(r, dict) and is_past(r))
    unique_archive = {archive_key(record): record for record in archived}
    if unique_archive:
        tmp_archive = archive_file + ".tmp"
        with open(tmp_archive, "w", encoding="utf-8") as output:
            json.dump(list(unique_archive.values()), output, ensure_ascii=False, indent=2)
        os.replace(tmp_archive, archive_file)
        print(f"Historical archive: {len(unique_archive)} past events retained.")

    from festival_tags import assign_festivals
    events = [assign_festivals(event) for event in events]
    comedy_corrections = sum(correct_comedy_category(event) for event in events)
    print(f"Comedy category corrections applied: {comedy_corrections}")


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


# Venue aliases are applied to both newly scraped and retained records.
# This keeps the public Venue filter consistent across future runs.
VENUE_ALIASES = {
    "adelaide showground - old brick dairy": "Adelaide Showground",
    "adelaide showground": "Adelaide Showground",
    "botanic park": "Botanic Park / Tainmuntilla",
    "botanic park / tainmuntilla": "Botanic Park / Tainmuntilla",
    "elder park, adelaide": "Elder Park",
    "elder park": "Elder Park",
    "festival plaza, adelaide": "Festival Plaza",
    "festival plaza": "Festival Plaza",
    "ila | immersive light and art": "Immersive Light and Art (ILA)",
    "immersive light and art (ila)": "Immersive Light and Art (ILA)",
    "mclaren vale institute hall": "McLaren Vale Institute Hall",
    "mclaren vale institute hall": "McLaren Vale Institute Hall",
    "national wine centre of australia": "National Wine Centre",
    "national wine centre": "National Wine Centre",
    "rhino room, adelaide": "Rhino Room",
    "rhino room": "Rhino Room",
    "victoria square": "Victoria Square / Tarntanyangga",
    "victoria square / tartanyangga": "Victoria Square / Tarntanyangga",
    "victoria square / tarntanyangga": "Victoria Square / Tarntanyangga",

    "adel ent cent - theatre": "Adelaide Entertainment Centre",
    "lucky dumpling market, elder park": "Elder Park",
    "ellis park - tampawardli - city west": "Ellis Park",
    "the ed castle hotel": "The Ed Castle",
    "149 hindley": "DIV-DE",
    "st peter's cathedral": "St Peter's Cathedral",
    "ukaria cultural centre": "UKARIA Cultural Centre",
}

# Specific cancelled event IDs, not a blanket title-based ban. This avoids
# accidentally removing unrelated future performances with similar names.
CANCELLED_EVENT_IDS = {
    "3300029954876416",  # Secret Garden in Adelaide
    "200030161153327",   # Secret Garden Live in Hindmarsh 2026
}


def standardise_venue(event):
    venue = str(event.get("venue") or "").strip()
    canonical = "" if venue.casefold() == "family friendly events & shows" else VENUE_ALIASES.get(venue.casefold())
    if canonical is not None and canonical != venue:
        event["venue"] = canonical
        return True
    return False



# Conservative, exact-title corrections identified in the November audit.
# Never infer a time or remove a performance from these corrections.
AUDITED_CATEGORY_OVERRIDES = {
    "a perfect circle": "Music",
    "spacey jane": "Music",
    "queens of the stone age 2026": "Music",
    "women’s australian open": "Sport",
    "women's australian open": "Sport",
    "adelaide international": "Sport",
    "womadelaide": "Festival",
    "adelaide national pharmacies christmas pageant": "Community",
    "adelaide carols by candlelight": "Music",
    "santa’s wonderland": "Family",
    "santa's wonderland": "Family",
    "bp adelaide grand final": "Sport",
    "shrek rave": "Club/Party",
    "five nights at freddy’s rave!": "Club/Party",
    "five nights at freddy's rave!": "Club/Party",
    "new years eve celebration dinner": "Food & Beverage",
    "adelaide town hall christmas concert": "Music",
    "sunday at the cedars - monthly talks series": "Talks & Conferences",
}

# Only exact, visually confirmed corruption patterns; no blanket encoding
# conversion because that can damage legitimate accented names.
AUDITED_TEXT_REPLACEMENTS = {
    "BohÃ¨me": "Bohème",
    "BrontÃ«": "Brontë",
    "FormalÂ®": "Formal®",
}


def apply_audited_data_corrections(event):
    """Apply reversible, narrowly scoped display-data fixes in memory."""
    changes = []
    title = str(event.get("title") or "")
    fixed_title = title
    for bad, good in AUDITED_TEXT_REPLACEMENTS.items():
        fixed_title = fixed_title.replace(bad, good)
    if fixed_title != title:
        event["title"] = fixed_title
        changes.append("title encoding")
    category = event.get("category") or []
    if isinstance(category, str):
        category = [category]
    if not category or all(str(c).strip().casefold() in ("", "other") for c in category):
        corrected = AUDITED_CATEGORY_OVERRIDES.get(fixed_title.strip().casefold())
        if corrected:
            event["category"] = [corrected]
            changes.append("category")
    return changes



def remove_verified_festival_cross_source_duplicates(events):
    """Remove a small, independently verifiable set of festival co-listings.

    Require exact normalised title, venue, first date and final date.  Only
    compare known source pairs.  Keep separately timed performances and never
    combine distinct dates.  The original venue/organiser URL is retained.
    """
    from collections import defaultdict

    def norm(value):
        return " ".join(re.sub(r"[^a-z0-9]+", " ",
                               str(value or "").casefold()).split())

    def time_of(event):
        found = re.search(r"T(\d{2}:\d{2})", str(event.get("datetime") or ""))
        return found.group(1) if found and found.group(1) != "00:00" else None

    # (source to keep, source to discard), only for verified co-publishers.
    source_pairs = {
        ("Adelaide Festival", "Adelaide Festival Centre"),
        ("Hindley St Music Hall", "Adelaide Festival"),
        ("Immersive Light and Art", "Adelaide Festival"),
        ("Art Gallery of South Australia", "Adelaide Festival"),
        ("Adelaide Festival", "Play & Go Adelaide Major Events"),
    }
    groups = defaultdict(list)
    for index, event in enumerate(events):
        key = (norm(event.get("title")), norm(event.get("venue")),
               str(event.get("datetime") or "")[:10],
               str(event.get("end_datetime") or "")[:10])
        if key[0] and key[1] and key[2]:
            groups[key].append((index, event))

    removed = set()
    audit = []
    for key, group in groups.items():
        for index, event in group:
            if index in removed:
                continue
            for keep_index, keeper in group:
                if keep_index == index or keep_index in removed:
                    continue
                if (str(keeper.get("source") or ""),
                    str(event.get("source") or "")) not in source_pairs:
                    continue
                # If both have explicit but different times, they are separate
                # performances, regardless of matching event/venue/date.
                first_time, second_time = time_of(keeper), time_of(event)
                if first_time and second_time and first_time != second_time:
                    continue
                # Never discard a confirmed time in favour of an unknown one.
                if second_time and not first_time:
                    continue
                # A matched source pair, title, venue and date range makes
                # this a verified festival co-listing rather than a guess.
                removed.add(index)
                audit.append((event.get("title"), event.get("source"),
                              keeper.get("source")))
                break

    print(f"Festival co-listings: {len(removed)} verified duplicates excluded")
    for title, dropped, kept in audit:
        print(f"  DEDUP: {title} | removed {dropped} | kept {kept}")
    return [event for index, event in enumerate(events) if index not in removed]

def remove_verified_showground_aggregator_duplicates(events):
    """Prefer the official Santa's Wonderland listing over its date-only copy.

    The rule is deliberately limited to one named event, venue, calendar day
    and two sources. Other events and separately timed sessions are untouched.
    """
    def canonical_title(value):
        return " ".join(re.sub(r"[^a-z0-9]+", " ",
                               str(value or "").casefold()).split())

    official_dates = {
        str(event.get("datetime") or "")[:10]
        for event in events
        if event.get("source") == "Adelaide Showground"
        and str(event.get("venue") or "").strip().casefold() == "adelaide showground"
        and canonical_title(event.get("title")) == "santa s wonderland"
        and re.search(r"T(?!00:00)\d{2}:\d{2}", str(event.get("datetime") or ""))
    }
    filtered = []
    removed = 0
    for event in events:
        is_duplicate = (
            event.get("source") == "Play & Go Adelaide Major Events"
            and str(event.get("venue") or "").strip().casefold() == "adelaide showground"
            and canonical_title(event.get("title")) == "santa s wonderland"
            and str(event.get("datetime") or "")[:10] in official_dates
            and str(event.get("datetime") or "")[11:16] in ("", "00:00")
        )
        if is_duplicate:
            removed += 1
        else:
            filtered.append(event)
    print(f"Showground: {removed} date-only Santa's Wonderland aggregator duplicates excluded")
    return filtered


def consolidate_verified_cross_source_duplicates(events):
    """Only merge high-confidence cross-source copies of one performance.

    Same title, verified venue, date AND explicit start time are required.
    Unknown/midnight start times are not sufficient to merge performances.
    Preserve richer ticketing data and log both sides of every removal.
    """
    from collections import defaultdict
    from urllib.parse import urlparse

    def normalised(value):
        value = str(value or "").casefold().replace("&", " and ")
        return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())

    def time_value(event):
        match = re.search(r"T(\d{2}:\d{2})", str(event.get("datetime") or ""))
        if not match or match.group(1) == "00:00":
            return None
        return match.group(1)

    def reliable_end(event):
        start = str(event.get("datetime") or "")
        end = str(event.get("end_datetime") or "")
        try:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            return bool(end_dt > start_dt and (end_dt - start_dt).days <= 366)
        except (ValueError, TypeError):
            return False

    def quality(event):
        source = str(event.get("source") or "")
        link = str(event.get("link") or event.get("url") or "")
        host = (urlparse(link).hostname or "").lower()
        # A source label is not proof of ownership. A Ticketmaster-labelled
        # Moshtix URL should not beat a richer original Moshtix record.
        source_owns_link = (
            ("moshtix" in source.lower() and "moshtix.com.au" in host)
            or ("ticketmaster" in source.lower() and "ticketmaster.com.au" in host)
        )
        official = not any(x in source.lower() for x in (
            "ticketmaster", "moshtix", "humanitix", "allevents",
            "play & go", "experience adelaide", "tourism commission"))
        return (int(reliable_end(event)), int(bool(event.get("image"))),
                int(official), int(source_owns_link), int(bool(link)))

    groups = defaultdict(list)
    for index, event in enumerate(events):
        key = (normalised(event.get("title")),
               normalised(event.get("venue")),
               str(event.get("datetime") or "")[:10])
        groups[key].append((index, event))

    retained = []
    audit = []
    for group in groups.values():
        chosen = []
        for index, event in sorted(group, key=lambda pair: quality(pair[1]), reverse=True):
            start = time_value(event)
            duplicate_of = None
            for _, previous in chosen:
                if previous.get("source") == event.get("source"):
                    continue
                # An unknown start time may represent a different session.
                if not start or not time_value(previous) or start != time_value(previous):
                    continue
                duplicate_of = previous
                break
            if duplicate_of is None:
                chosen.append((index, event))
            else:
                audit.append({
                    "removed": {k: event.get(k, "") for k in
                                ("title", "venue", "datetime", "end_datetime", "source", "link")},
                    "kept": {k: duplicate_of.get(k, "") for k in
                             ("title", "venue", "datetime", "end_datetime", "source", "link")},
                    "reason": "same title, venue, date and confirmed start time",
                })
        retained.extend(chosen)
    retained.sort(key=lambda pair: pair[0])
    return [event for _, event in retained], audit


def restore_richer_existing_event_details(events, existing_events):
    """Repair information lost when an earlier exact-key merge chose a sparse copy.

    Match only same date plus same ticket URL or same title and canonical venue.
    Keep the original event record if it is strictly richer, rather than
    fabricating end times. Never borrow an end time from a different session.
    """
    from collections import defaultdict
    from urllib.parse import urlparse

    def clean(value):
        return " ".join(re.sub(r"[^a-z0-9]+", " ",
                               str(value or "").casefold()).split())

    def canonical_venue(value):
        raw = str(value or "").strip()
        return clean(VENUE_ALIASES.get(raw.casefold(), raw))

    def url_key(event):
        raw = str(event.get("link") or event.get("url") or "").strip()
        parsed = urlparse(raw)
        return ((parsed.hostname or "").lower().removeprefix("www.")
                + parsed.path.rstrip("/").lower()) if parsed.hostname else ""

    def valid_end(event):
        """Reject malformed or demonstrably impossible end dates, not seasons.

        Midnight/date-only starts commonly describe an exhibition, series or
        recurring listing. A long range is not a performance duration.
        """
        try:
            start_raw = str(event.get("datetime") or "")
            end_raw = str(event.get("end_datetime") or "")
            start = datetime.fromisoformat(start_raw)
            end = datetime.fromisoformat(end_raw)
            if end <= start:
                return False
            # Date-only / midnight records are date ranges, not timed gigs.
            if len(start_raw) <= 10 or start.time().strftime("%H:%M") == "00:00":
                return (end - start).days <= 3650
            # Preserve genuine production runs, tours and festivals even when
            # the first performance has a specific start time.
            categories = event.get("category") or []
            if isinstance(categories, str):
                categories = [categories]
            category_text = " ".join(map(str, categories)).casefold()
            source = str(event.get("source") or "").casefold()
            title = str(event.get("title") or "").casefold()
            # Long-running listings can have a real opening time while their
            # end_datetime denotes the last scheduled occurrence, not the
            # end of a single session. Keep these verified source ranges.
            # Do not treat a concert's "Album Tour" as a recurring tour.
            recurring_title = any(term in title for term in (
                "garden tour", "guided tour", "cultural garden tours",
                "plant sale", "drag bingo", "bachata by the beach",
                "unwined uncovered", "social clay session",
                "mindful clay", "studio tour", "studio tours",
                "playgroup", "weekly class", "exhibition",
                "guided walk", "open days",
            ))
            recurring_source = (
                "south australia tourism commission" in source
                or "adelaide botanic gardens" in source
                or "art gallery of south australia" in source
            )
            recurring_category = any(term in category_text for term in (
                "exhibition", "workshop", "community",
            ))
            run_listing = (
                "adelaide festival" in source
                or "festival" in category_text
                or recurring_title
                or (recurring_source and recurring_category)
            )
            max_days = 3650 if run_listing else 366
            return (end - start).total_seconds() <= max_days * 86400
        except (ValueError, TypeError, OverflowError):
            return False

    by_url = defaultdict(list)
    by_identity = defaultdict(list)
    for old in existing_events:
        date = str(old.get("datetime") or "")[:10]
        if not date:
            continue
        url = url_key(old)
        if url:
            by_url[(url, date)].append(old)
        by_identity[(clean(old.get("title")), canonical_venue(old.get("venue")), date)].append(old)

    repairs = []
    invalid_ends = []
    for event in events:
        date = str(event.get("datetime") or "")[:10]
        url = url_key(event)
        identity = (clean(event.get("title")), canonical_venue(event.get("venue")), date)
        candidates = list(by_identity.get(identity, []))
        if url:
            candidates.extend(by_url.get((url, date), []))
        # Do not transfer details across two explicitly different showtimes.
        fresh_time = str(event.get("datetime") or "")[11:16]
        candidates = [old for old in candidates
                      if (not fresh_time or fresh_time == "00:00"
                          or str(old.get("datetime") or "")[11:16] in ("", "00:00", fresh_time))]
        current_valid = valid_end(event)
        richer = [old for old in candidates if valid_end(old)]
        if not current_valid and richer:
            # Retain the entire source record only for an exact session match.
            # Otherwise, transfer the valid end date only.
            chosen = max(richer, key=lambda old: (
                int(bool(old.get("image"))),
                int(url_key(old) == url),
                int(clean(old.get("title")) == identity[0])))
            before = {k: event.get(k, "") for k in
                      ("title", "venue", "datetime", "end_datetime", "source", "link")}
            same_session = str(chosen.get("datetime") or "")[:16] == str(event.get("datetime") or "")[:16]
            if same_session:
                event.update({k: v for k, v in chosen.items()
                              if k not in ("venue",)})
            else:
                event["end_datetime"] = chosen["end_datetime"]
            repairs.append({"before": before,
                            "after": {k: event.get(k, "") for k in before},
                            "reason": "restored verified existing end time"})
        # A Moshtix-owned booking link must not retain an aggregator label.
        # This also fixes records whose old end date was genuinely invalid.
        if url and url.startswith("moshtix.com.au/") and str(event.get("source") or "") == "Ticketmaster Adelaide":
            before_source = event.get("source", "")
            event["source"] = "Moshtix Adelaide CBD"
            repairs.append({
                "before": {"title": event.get("title", ""), "source": before_source,
                           "end_datetime": event.get("end_datetime", "")},
                "after": {"title": event.get("title", ""), "source": event["source"],
                          "end_datetime": event.get("end_datetime", "")},
                "reason": "corrected Moshtix booking-link ownership",
            })
        if event.get("end_datetime") and not valid_end(event):
            invalid_ends.append({"title": event.get("title", ""),
                                 "datetime": event.get("datetime", ""),
                                 "invalid_end": event.get("end_datetime", "")})
            event["end_datetime"] = ""
    return repairs, invalid_ends


# Batch 7: Confirmed cancelled booking URLs, scoped to the exact booking ID.
# Do not use performer-name or substring matching: another performance may be valid.
CONFIRMED_CANCELLED_BOOKINGS = {
    ("moshtix.com.au", "/v2/event/ru-pretty-enuff-australian-tour-26/195437"),
}


def is_confirmed_cancelled_booking(event):
    """Match a verified cancelled booking by its exact canonical host and path."""
    link = str(event.get("link") or event.get("url") or "").strip()
    parsed = urlparse(link)
    host = (parsed.hostname or "").casefold().removeprefix("www.")
    path = parsed.path.rstrip("/").casefold()
    return (host, path) in CONFIRMED_CANCELLED_BOOKINGS


def is_cancelled_secret_garden(event):
    link = str(event.get("link") or event.get("url") or "")
    parsed = urlparse(link)
    hostname = (parsed.hostname or "").lower()
    if hostname not in ("allevents.in", "www.allevents.in"):
        return False
    event_id = parsed.path.rstrip("/").split("/")[-1]
    return event_id in CANCELLED_EVENT_IDS


def is_explicitly_cancelled(event):
    """Exclude listings whose titles explicitly announce cancellation.

    Only a leading status marker is considered; ordinary titles containing
    the word 'cancelled' elsewhere are not automatically discarded.
    """
    title = str(event.get("title") or "").strip()
    return bool(re.match(
        r"^(?:\[\s*cancelled\s*\]|cancelled\s*(?:[|:—–-]|$))",
        title, flags=re.IGNORECASE
    ))


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

    cleaned_record = {
        "title": title,
        "venue": venue,
        "datetime": dt,
        "end_datetime": end_dt,
        "category": category,
        "image": image,
        "link": link,
        "source": source_name,
    }
    # Preserve verified door-opening metadata separately from the event start.
    # Only Hindley Street Music Hall currently supplies this field.
    if source_name == "Hindley St Music Hall":
        doors_open = str(event.get("doors_open") or "").strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", doors_open):
            try:
                doors_dt = datetime.fromisoformat(doors_open)
                if doors_dt.strftime("%Y-%m-%d") == dt[:10]:
                    cleaned_record["doors_open"] = doors_open
            except ValueError:
                pass
    correct_verified_event_dates(cleaned_record)
    return cleaned_record


def event_key(event):

    # ASO may schedule multiple distinct performances on the same date.
    session_key = (str(event.get("datetime", ""))
                   if event.get("source") in ("Adelaide Symphony Orchestra", "Adelaide Festival")
                   else str(event.get("datetime", ""))[:10])
    return (
        str(
            event.get("title", "")
        ).lower().strip(),

        str(
            event.get("venue", "")
        ).lower().strip(),

        session_key,
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
        "rhino room adl": "rhino room",
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
    # Identical Moshtix booking IDs establish the same event even when the
    # listing includes extra support acts. Different dates remain distinct.
    def moshtix_booking_id(event):
        url = str(event.get("link") or event.get("url") or "")
        parsed = urlparse(url)
        if "moshtix.com.au" not in (parsed.hostname or "").lower():
            return ""
        match = re.search(r"/v2/event/[^/?]+/(\d+)(?:/|$)", parsed.path, re.I)
        return match.group(1) if match else ""
    ticket_id = moshtix_booking_id(ticket)
    if ticket_id and ticket_id == moshtix_booking_id(official):
        return True
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
        # The official Showground calls this "Froth & Fury Fest", while
        # Ticketmaster lists "Froth and Fury Fest 2027". Treat these as the
        # same festival ONLY when the venue and event date also match.
        # Do not suppress a Ticketmaster record if the official source failed
        # to produce its corresponding event on this run.
        def same_showground_festival(official_event):
            if official_event.get("source") != "Adelaide Showground":
                return False
            if _date(ticket) != _date(official_event) or not _date(ticket):
                return False
            def festival_name(value):
                normalized = _title_name(value)
                normalized = re.sub(r"\b20\d{2}\b", "", normalized)
                return " ".join(normalized.split())
            return (festival_name(ticket.get("title")) == "froth and fury fest"
                    and festival_name(official_event.get("title")) == "froth and fury fest")

        if any(_same_event(ticket, other) or same_showground_festival(other)
               for other in candidates):
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


def classify_source_failure(exc):
    """Make HTTP failures understandable without changing preservation rules."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status is None:
        match = re.search(r"\b(403|429|500|502|503|504)\b", str(exc))
        status = int(match.group(1)) if match else None
    if status == 403:
        return "HTTP 403 (access denied; no automatic retry)"
    if status == 429:
        return "HTTP 429 (rate limited; existing records retained)"
    if status in (500, 502, 503, 504):
        return f"HTTP {status} (server unavailable)"
    return "source error"


def limited_retry_after(exc):
    """Retry at most once, only when server explicitly requests a short wait."""
    response = getattr(exc, "response", None)
    status = getattr(response, "status_code", None)
    if status is None and re.search(r"\b429\b", str(exc)):
        status = 429
    if status != 429:
        return None
    header = (getattr(response, "headers", {}) or {}).get("Retry-After")
    if not header:
        return None
    try:
        seconds = float(header)
    except (TypeError, ValueError):
        try:
            dt = parsedate_to_datetime(header)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            seconds = (dt - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            return None
    if 0 <= seconds <= 10:
        return max(1.0, seconds)
    return None


def scrape_with_bounded_retry(source):
    """Avoid repeated requests when a site is limiting automated traffic."""
    try:
        return scrape_source(source)
    except requests.exceptions.HTTPError as exc:
        # Only Plant 3 is retried. Other sources keep their existing behavior.
        if source["name"] != "Plant 3 Bowden":
            raise
        wait = limited_retry_after(exc)
        if wait is None:
            raise
        print(f"HTTP 429; respecting Retry-After ({wait:g}s); one retry -> ", end="", flush=True)
        time.sleep(wait)
        return scrape_source(source)


def scrape_source(source):

    name = source["name"]
    url = source["url"]

    if name == "Humanitix Nineteen Ten":
        return scrape_humanitix(host_only=True)

    if name == "Humanitix Adelaide and Regions":
        return scrape_humanitix(host_only=False)

    if name == "The Gov":
        return parse_the_gov()

    if name == "Morphettville Racecourse":
        return parse_morphettville_racecourse(fetch_page("https://morphettville.com.au/"), "https://morphettville.com.au/")

    if name == "Plant 4 Bowden":
        return parse_plant_4_bowden()

    if name == "Plant 3 Bowden":
        return parse_plant_3_bowden()

    if name == "MOD.":
        return parse_mod_museum()

    if name == "The District at SkyCity":
        return parse_the_district_skycity()

    if name == "Kerry Packer Civic Gallery":
        return parse_kerry_packer_civic_gallery()

    if name == "SAMSTAG Museum":
        # The previous unisa.edu.au address has a broken certificate.
        # Use the museum's current official domain without disabling TLS.
        return parse_samstag_museum()

    if name == "Oztix Adelaide City":
        return parse_oztix_adelaide_city()

    if name == "Jetty Road Glenelg":
        listing_url = "https://www.jettyroadglenelg.com.au/whats-on"
        pages = [fetch_page(listing_url)]
        # Page two is linked by the official listing. If temporarily unavailable,
        # still use the first page without inventing any records.
        try:
            pages.append(fetch_page(listing_url + "/p2"))
        except Exception as exc:
            print(f"    Jetty Road page 2 unavailable: {exc}")
        return parse_jetty_road_glenelg(pages, listing_url)

    if name == "Carrick Hill":
        listing_url = "https://www.carrickhill.sa.gov.au/visit/whats-on"
        return parse_carrick_hill(fetch_page(listing_url), listing_url)

    if name == "National Trust SA":
        listing_url = "https://www.nationaltrust.org.au/explore/?content=event&state=sa"
        return parse_national_trust_sa(fetch_page(listing_url), listing_url)

    if name == "Jive":
        return parse_jive(fetch_page(url), url)

    if name == "Rhino Room":
        return parse_rhino_room(fetch_page(url), url)

    if name == "Arkaba Hotel":
        return parse_arkaba_hotel(fetch_page(url), url)

    if name == "UniBar Adelaide":
        return parse_unibar_adelaide(fetch_page("https://www.unibaradl.com.au/"), "https://www.unibaradl.com.au/")

    if name == "Gilles at the Grounds":
        return parse_gilles_at_the_grounds(fetch_page("https://gillesatthegrounds.com.au/"), "https://gillesatthegrounds.com.au/")

    if name == "Trinity Sessions":
        return parse_trinity_sessions(fetch_page(url), url)

    if name == "Norwood Concert Hall":
        return parse_norwood_concert_hall(fetch_page(url), url)

    if name == "Moshtix Adelaide CBD":
        return parse_moshtix_adelaide()

    if name == "AllEvents Adelaide and Surrounds":
        return parse_allevents_adelaide_and_surrounds(fetch_page(url), url)

    if name == "AllEvents Victoria Square":
        return parse_allevents_victoria_square(fetch_page(url), url)

    # ----------------------------------------
    # Ticketmaster Adelaide (official API)
    # ----------------------------------------
    if name == "Ticketmaster Adelaide":
        return parse_ticketmaster_adelaide(os.environ.get("TICKETMASTER_API_KEY", ""))

    # ----------------------------------------
    # Thebarton Theatre (official links + verified Ticketmaster metadata)
    # ----------------------------------------
    if name == "Thebarton Theatre":
        return parse_thebarton_theatre(
            fetch_page(url), url,
            os.environ.get("TICKETMASTER_API_KEY", "")
        )

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

    if name == "David Roche Foundation":
        return parse_david_roche_gallery(fetch_page("https://www.rochegallery.com.au/events/calendar/"), url)

    if name == "Adelaide Central Market":
        return parse_adelaide_central_market(fetch_page(url), url)

    if name == "Fever Candlelight Adelaide":
        return parse_fever_candlelight(fetch_page(url), url)

    if name == "ACE Gallery":
        return parse_ace_gallery(fetch_page("https://ace.gallery/"), url)

    if name == "Kings of Comedy":
        return parse_kings_of_comedy(fetch_page(url), url)

    if name == "Adelaide Repertory Theatre":
        return parse_adelaide_repertory_theatre(fetch_page(url), url)

    if name == "Art Gallery of South Australia":
        return parse_art_gallery_south_australia(fetch_page(url), url)

    if name == "South Australian Museum":
        museum_url = "https://whatson.samuseum.sa.gov.au/"
        return parse_south_australian_museum(fetch_page(museum_url), museum_url)

    if name == "State Theatre Company South Australia":
        snapshot = os.path.join(os.path.dirname(__file__), 'state_theatre_upcoming.html')
        if not os.path.isfile(snapshot):
            raise RuntimeError('State Theatre saved HTML missing: Scraper/state_theatre_upcoming.html')
        print('    State Theatre: using saved browser HTML snapshot (not live)')
        with open(snapshot, 'r', encoding='utf-8') as handle:
            soup = BeautifulSoup(handle.read(), 'lxml')
        return parse_state_theatre_company(soup, url)

    if name == "Dom Polski Centre":
        return parse_dom_polski_centre(fetch_page(url), url)

    if name == "Nexus Arts":
        return parse_nexus_arts(fetch_page(url), url)

    if name == "Government House":
        return parse_government_house(fetch_page(url), url)

    if name == "Adelaide Zoo":
        return parse_adelaide_zoo(fetch_page(url), url)

    if name == "National Wine Centre":
        return parse_national_wine_centre(fetch_page(url), url)

    if name == "Adelaide Fringe":
        return parse_adelaide_fringe(fetch_page(url), url)

    if name == "Adelaide Festival":
        return parse_adelaide_festival(fetch_page(url), url)

    if name == "SALA Festival":
        return parse_sala_festival(fetch_page(url), url)

    if name == "National Railway Museum":
        return parse_national_railway_museum(fetch_page(url), url)

    if name == "South Australian Aviation Museum":
        return parse_south_australian_aviation_museum(fetch_page(url), url)

    if name == "South Australian Maritime Museum":
        return parse_south_australian_maritime_museum(fetch_page(url), url)

    if name == "Migration Museum Adelaide":
        return parse_migration_museum_adelaide(fetch_page(url), url)

    if name == "Army Museum of South Australia":
        return parse_army_museum_south_australia(fetch_page(url), url)

    if name == "Play & Go Adelaide Major Events":
        return parse_play_and_go_major_events(fetch_page(url), url)

    if name == "Adelaide Gaol":
        return parse_adelaide_gaol(fetch_page(url), url)

    if name == "Moonlight Cinema Adelaide":
        return parse_moonlight_cinema_adelaide(fetch_page(url), url)

    if name == "Adelaide Botanic Gardens":
        return parse_adelaide_botanic_gardens(fetch_page(url), url)

    if name == "Illuminate Adelaide":
        return parse_illuminate_adelaide(fetch_page(url), url)

    if name == "Adelaide Showground":
        return parse_adelaide_showground(fetch_page(url), url)

    if name == "A Day on the Green":
        return parse_a_day_on_the_green(fetch_page(url), url)

    if name == "State Opera South Australia":
        return parse_state_opera_south_australia(fetch_page(url), url)

    if name == "Adelaide Symphony Orchestra":
        return parse_adelaide_symphony_orchestra(fetch_page(url), url)

    # The Drive: use current /whatson, not the stale /events archive.
    if name == "The Drive":
        current_url = "https://www.thedriveadelaide.com.au/whatson"
        return parse_the_drive(fetch_page(current_url), current_url)

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



# ------------------------------------------------------------
# Thebarton Theatre official-poster enrichment
# ------------------------------------------------------------

THEBARTON_HOMEPAGE = "https://thebartontheatre.com.au/"
TICKETMASTER_EVENT_ID = re.compile(r"/event/([A-Za-z0-9]+)", re.I)
WORDPRESS_THUMBNAIL = re.compile(r"-\d+x\d+(?=\.[A-Za-z0-9]+(?:$|\?))")


def ticketmaster_event_id(link):
    """Extract the stable Ticketmaster event ID from either URL format."""
    match = TICKETMASTER_EVENT_ID.search(str(link or ""))
    return match.group(1).upper() if match else ""


def thebarton_official_posters():
    """Return verified official poster URLs keyed by Ticketmaster event ID.

    The theatre's gallery can link to events at OTHER venues, so this function
    deliberately discovers images only. It does not invent event metadata.
    """
    try:
        soup = fetch_page(THEBARTON_HOMEPAGE)
    except Exception as exc:
        print(f"Thebarton posters: homepage unavailable ({exc}); keeping existing images")
        return {}

    from concurrent.futures import ThreadPoolExecutor, as_completed
    from urllib.parse import urljoin, urlparse

    # Collect all gallery candidates. Some IDs have both a landscape banner
    # and a portrait/square event poster; prefer the latter when available.
    candidates = {}
    for anchor in soup.find_all("a", href=True):
        event_id = ticketmaster_event_id(anchor.get("href"))
        if not event_id:
            continue
        for img in anchor.find_all("img"):
            for attribute in ("data-full-image", "data-src", "src"):
                raw = str(img.get(attribute) or "").strip()
                if not raw or raw.startswith("data:"):
                    continue
                image_url = urljoin(THEBARTON_HOMEPAGE, raw)
                parsed = urlparse(image_url)
                if (parsed.hostname or "").lower() not in (
                    "thebartontheatre.com.au", "www.thebartontheatre.com.au"
                ) or not parsed.path.startswith("/wp-content/uploads/"):
                    continue
                original = WORDPRESS_THUMBNAIL.sub("", image_url)
                # Deduplicate URLs while preserving the gallery's ordering.
                group = candidates.setdefault(event_id, [])
                if original not in group:
                    group.append(original)

    def image_priority(url):
        filename = urlparse(url).path.lower()
        # A wide 'banner' image is less suitable for vertically styled cards.
        return ("banner" in filename or "1680x638" in filename,)

    def verify_poster(item):
        event_id, image_urls = item
        for image_url in sorted(image_urls, key=image_priority):
            try:
                with requests.Session() as session:
                    session.headers.update(HEADERS)
                    response = session.head(image_url, timeout=12, allow_redirects=True)
                    if response.status_code in (403, 405):
                        response.close()
                        response = session.get(image_url, timeout=12, stream=True)
                    try:
                        content_type = response.headers.get("Content-Type", "").lower()
                        if response.ok and content_type.startswith("image/"):
                            return event_id, image_url
                    finally:
                        response.close()
            except requests.RequestException:
                continue
        return event_id, None

    verified = {}
    if candidates:
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(verify_poster, item)
                       for item in candidates.items()]
            for future in as_completed(futures):
                event_id, image_url = future.result()
                if image_url:
                    verified[event_id] = image_url

    print(f"Thebarton posters: {len(candidates)} linked, {len(verified)} verified originals")
    return verified


def enrich_thebarton_images(events):
    """Match official images by Ticketmaster ID across ALL venue records.

    No event is created, removed, re-venued or re-dated by poster discovery.
    This avoids duplicating the theatre website's links to Norwood shows.
    """
    targets = {}
    for event in events:
        event_id = ticketmaster_event_id(event.get("link") or event.get("url"))
        if event_id:
            targets.setdefault(event_id, []).append(event)

    if not targets:
        print("Thebarton posters: no Ticketmaster-linked events to enrich")
        return

    posters = thebarton_official_posters()
    updated = 0
    matched_ids = set()
    for event_id, official_image in posters.items():
        for event in targets.get(event_id, []):
            matched_ids.add(event_id)
            if event.get("image") != official_image:
                event["image"] = official_image
                updated += 1

    unmatched = sorted(set(posters) - matched_ids)
    print(f"Thebarton posters: {updated} images updated; "
          f"{len(matched_ids)} event IDs matched across all venues")
    if unmatched:
        print("Thebarton posters: unmatched Ticketmaster IDs "
              "(not added without verified date/venue): " + ", ".join(unmatched))


def source_domains(source_name):
    """
    Return the official hostname(s) configured for a source.
    """
    domains = set()

    for source in list(SOURCES) + [{"name": "The District at SkyCity", "url": "https://skycityadelaide.com.au/eat-and-drink/the-district/whats-on/"}, {"name": "Moshtix Adelaide CBD", "url": "https://www.moshtix.com.au/v2/search"}, {"name": "Humanitix Nineteen Ten", "url": "https://events.humanitix.com/host/nineteentenadl"}, {"name": "Humanitix Adelaide and Regions", "url": "https://humanitix.com/au/events/au--sa--adelaide"}]:
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
    """Identify source ownership without claiming another source's events.

    The explicit `source` field is authoritative. In particular, an ASO,
    Adelaide Festival, or Humanitix event at Adelaide Town Hall belongs to
    its own source, even when the venue or event URL mentions Town Hall.
    Only source-less legacy records may use URL and venue fallbacks.
    """
    wanted = source_name.strip().casefold()
    explicit_source = str(event.get("source") or "").strip().casefold()

    if explicit_source:
        return explicit_source == wanted

    # Humanitix's two feeds share a domain; source-less records cannot be
    # attributed reliably to either feed.
    if source_name.startswith("Humanitix "):
        return False

    # AllEvents regional feeds also overlap; do not guess ownership.
    if source_name.startswith("AllEvents "):
        return False

    link = str(event.get("link") or event.get("url") or "").strip()
    if link:
        try:
            hostname = (urlparse(link).hostname or "").casefold()
            if hostname.startswith("www."):
                hostname = hostname[4:]
            for domain in source_domains(source_name):
                if hostname == domain or hostname.endswith("." + domain):
                    return True
        except (ValueError, TypeError):
            pass

    # Only undetermined legacy records can fall back to venue equality.
    venue = str(event.get("venue") or "").strip().casefold()
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

    # Review-only warnings; never infer cancellations or delete sessions.
    from datetime import date
    today_key = date.today().isoformat()
    proposed_urls = defaultdict(list)
    def review_url(event):
        parsed = urlparse(str(event.get("link") or event.get("url") or ""))
        return ((parsed.hostname or "").casefold().removeprefix("www.")
                + parsed.path.rstrip("/").casefold()) if parsed.hostname else ""
    for event in proposed_events:
        url_key = review_url(event)
        if url_key:
            proposed_urls[url_key].append(event)
    review_flags = []
    for old in existing_events:
        last_day = str(old.get("end_datetime") or old.get("datetime") or "")[:10]
        if not last_day or last_day < today_key or identity(old) in new_by_key:
            continue
        matches = proposed_urls.get(review_url(old), []) if review_url(old) else []
        same_date = [new for new in matches if str(new.get("datetime") or "")[:10]
                     == str(old.get("datetime") or "")[:10]]
        if same_date:
            review_flags.append({"reason": "Upcoming event changed title/venue",
                                 "before": describe(old),
                                 "possible_replacements": [describe(new) for new in same_date]})
        elif not matches:
            review_flags.append({"reason": "Upcoming/ongoing event absent from proposed data",
                                 "before": describe(old)})
    # This known source discrepancy should not silently pass as zero flags.
    for event in proposed_events:
        title = str(event.get("title") or "").casefold()
        venue = str(event.get("venue") or "").casefold()
        if "meg carlin" in title and "loft" in title and "queens theatre" in venue:
            review_flags.append({
                "reason": "Event title names The Loft, but listing venue is The Queens Theatre; confirm with organiser",
                "proposed": describe(event),
            })
    repeated_records = [{"reason": "Repeated title/venue/date; review times and links",
                         "records": [describe(event) for event in records]}
                        for records in new_by_key.values() if len(records) > 1]
    holiday_review = [describe(event) for event in proposed_events
                      if str(event.get("datetime") or "")[:10] == "2026-12-25"
                      and "plant 4 bowden" in str(event.get("venue") or "").casefold()]
    report = {
        "review_flags": review_flags,
        "review_flags_count": len(review_flags),
        "repeated_records": repeated_records,
        "repeated_records_count": len(repeated_records),
        "holiday_sessions_to_verify": holiday_review,
        "holiday_sessions_to_verify_count": len(holiday_review),
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
    print(f"Upcoming event review flags: {len(review_flags)}")
    print(f"Repeated event groups: {len(repeated_records)}")
    print(f"Plant 4 Christmas Day sessions to verify: {len(holiday_review)}")
    print(f"Report saved to: {path}")
    print("events.json was NOT changed.")


def main(only_source=None):

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

    # Single-source test mode: never write events.json or run global cleanup.
    configured_sources = list(SOURCES) + [
        {"name": "The District at SkyCity", "url": "https://skycityadelaide.com.au/eat-and-drink/the-district/whats-on/"},
        {"name": "Carrick Hill", "url": "https://www.carrickhill.sa.gov.au/visit/whats-on"},
        {"name": "Jetty Road Glenelg", "url": "https://www.jettyroadglenelg.com.au/whats-on"},
        {"name": "Plant 4 Bowden", "url": "https://www.plant4bowden.com.au/whats-on"},
        {"name": "Plant 3 Bowden", "url": "https://bowdenbrewing.com/blogs/whats-on"},
        {"name": "Oztix Adelaide City", "url": "https://www.oztix.com.au/search/?states%5B0%5D=SA"},
        {"name": "Moshtix Adelaide CBD", "url": "https://www.moshtix.com.au/v2/search"},
        {"name": "Humanitix Nineteen Ten", "url": "https://events.humanitix.com/host/nineteentenadl"},
        {"name": "Humanitix Adelaide and Regions", "url": "https://humanitix.com/au/events/au--sa--adelaide"},
    ]
    if only_source is not None:
        matches = [s for s in configured_sources
                   if s["name"].casefold() == only_source.strip().casefold()]
        if not matches:
            print(f"ERROR: Unknown source: {only_source}")
            print("Available sources:")
            for s in configured_sources:
                print("  " + s["name"])
            return
        configured_sources = matches
        print(f"SINGLE-SOURCE MODE: {matches[0]['name']}")
        print("Only this source will be fetched.\n")

    # Optional quick mode: skip generic sites that returned zero events
    # in the last verified full run. Skipped sources retain their records.
    # Run without --quick regularly to discover new events at these sites.
    if "--quick" in sys.argv and only_source is None:
        known_empty_generic_sources = {
            "Nineteen Ten",
            "Adelaide Repertory Theatre",
            "Adelaide Cemetery Tours",
            "Trinity Sessions", "Morphettville Racecourse",
            "Holden Street Theatres",
            "Baroque Hall",
        }
        skipped = [s["name"] for s in configured_sources
                   if s["name"] in known_empty_generic_sources]
        configured_sources = [s for s in configured_sources
                              if s["name"] not in known_empty_generic_sources]
        print(f"QUICK MODE: skipping {len(skipped)} previously empty/error sources.")
        print("Their existing events are preserved; use a normal full run to recheck them.\\n")

    for source in configured_sources:

        name = source["name"]

        print(
            f"{name} -> ",
            end="",
            flush=True
        )

        try:

            fresh_events = scrape_with_bounded_retry(
                source
            )

            if fresh_events is None:
                fresh_events = []

        except Exception as e:

            print(
                f"{classify_source_failure(e)}: {e}; "
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
                standardise_venue(cleaned)
                if is_cancelled_secret_garden(cleaned):
                    continue

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

    if only_source is not None:
        # A single-source update must not invoke global cleanup or reprocess
        # other sources. Preserve their records unchanged.
        source_name = configured_sources[0]["name"]
        print("\n----------------------------------------")
        print(f"Source tested: {source_name}")
        print(f"New records collected: {len(all_new_events)}")
        print(f"Source accepted: {bool(accepted_sources)}")
        print(f"Existing events retained: {len(existing_events)}")

        if not accepted_sources:
            print("Source not accepted; events.json was NOT changed.")
            return

        # --preview and --dry-run are always non-writing, including with --only.
        dry_run = any(flag in sys.argv for flag in
                      ("--preview", "--preview-report", "--dry-run"))
        retained = [event for event in existing_events
                    if not event_belongs_to_source(event, source_name)]
        removed = len(existing_events) - len(retained)

        # Protect records belonging to other sources from being replaced by
        # a same-title, same-venue, same-date record from this source.
        other_keys = {event_key(event) for event in retained}
        added = []
        fresh_seen = set()
        for event in all_new_events:
            key = event_key(event)
            if key in other_keys or key in fresh_seen:
                continue
            fresh_seen.add(key)
            added.append(event)

        # Do not silently lose upcoming records missing from a partially
        # complete listing. Preserve them unless a matching URL or event key
        # was refreshed. This mirrors the full-run safeguard.
        from datetime import date
        today_key = date.today().isoformat()
        fresh_keys = {event_key(event) for event in added}
        def url_identity(event):
            parsed = urlparse(str(event.get("link") or event.get("url") or ""))
            return ((parsed.hostname or "").lower().removeprefix("www.")
                    + parsed.path.rstrip("/").lower()) if parsed.hostname else ""
        fresh_urls = {url_identity(event) for event in added}
        fresh_urls.discard("")
        preserved = []
        for old in existing_events:
            if not event_belongs_to_source(old, source_name):
                continue
            last_day = str(old.get("end_datetime") or old.get("datetime") or "")[:10]
            if not last_day or last_day < today_key:
                continue
            if event_key(old) in fresh_keys or url_identity(old) in fresh_urls:
                continue
            if event_key(old) in other_keys:
                continue
            preserved.append(old)
            other_keys.add(event_key(old))

        proposed = retained + added + preserved
        print(f"Replaced old source records: {removed}")
        print(f"New source records added: {len(added)}")
        print(f"Unmatched upcoming source records preserved: {len(preserved)}")
        print(f"Proposed total events: {len(proposed)}")
        if dry_run:
            if "--preview-report" in sys.argv or "--preview" in sys.argv:
                write_preview_report(existing_events, proposed)
            print("SINGLE-SOURCE PREVIEW COMPLETE: events.json was NOT changed.")
            return
        save_events(proposed)
        print("SINGLE-SOURCE UPDATE COMPLETE.")
        return

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

    # Preserve previously verified The Drive start times when the official
    # listing supplies only a date. First prefer the same official event URL;
    # otherwise accept one unambiguous same-title/date/venue match. This also
    # supports earlier runs that already replaced Ticketmaster records.
    def _drive_title(value):
        title = str(value or "").casefold().replace("&", " and ")
        title = re.sub(r"\b20\d{2}\b", " ", title)
        title = re.sub(r"[^a-z0-9]+", " ", title)
        return " ".join(title.split())

    drive_times_recovered = 0
    for fresh in all_new_events:
        if fresh.get("source") != "The Drive":
            continue
        fresh_dt = str(fresh.get("datetime") or "")
        if not fresh_dt.endswith("T00:00:00"):
            continue
        fresh_title = _drive_title(fresh.get("title"))
        fresh_link = str(fresh.get("link") or "").rstrip("/").casefold()
        candidates = []
        for old in existing_events:
            if old.get("source") not in ("The Drive", "Ticketmaster Adelaide"):
                continue
            if _venue_name(old.get("venue")) != _venue_name(fresh.get("venue")):
                continue
            old_dt = str(old.get("datetime") or "")
            if old_dt[:10] != fresh_dt[:10] or len(old_dt) < 19:
                continue
            if old_dt[11:19] == "00:00:00":
                continue
            old_title = _drive_title(old.get("title"))
            if not fresh_title or not old_title:
                continue
            if not (fresh_title == old_title or
                    (min(len(fresh_title), len(old_title)) >= 9 and
                     (fresh_title in old_title or old_title in fresh_title))):
                continue
            old_link = str(old.get("link") or "").rstrip("/").casefold()
            exact_link = bool(fresh_link and old_link == fresh_link)
            candidates.append((exact_link, old_dt))
        exact = {dt for same_link, dt in candidates if same_link}
        times = exact if exact else {dt for _, dt in candidates}
        # Never guess when different confirmed times conflict.
        if len(times) == 1:
            fresh["datetime"] = times.pop()
            drive_times_recovered += 1
    if drive_times_recovered:
        print(f"The Drive: preserved {drive_times_recovered} previously "
              "verified start times")

    # Restore Hindley start times only from unambiguous, previously verified
    # records for the same venue, calendar date and event identity.
    # An unknown midnight placeholder is never treated as a verified time.
    hindley_times_recovered = 0
    def _hindley_identity(value):
        return " ".join(re.sub(r"[^a-z0-9]+", " ",
                               str(value or "").casefold().replace("&", " and ")).split())

    known_hindley = list(existing_events) + list(all_new_events)
    for fresh in all_new_events:
        if fresh.get("source") != "Hindley St Music Hall":
            continue
        start = str(fresh.get("datetime") or "")
        if not start.endswith("T00:00:00"):
            continue
        fresh_name = _hindley_identity(fresh.get("title"))
        fresh_url = str(fresh.get("link") or "").split("?", 1)[0].rstrip("/").casefold()
        candidates = set()
        for known in known_hindley:
            if known is fresh or _venue_name(known.get("venue")) != "hindley street music hall":
                continue
            known_start = str(known.get("datetime") or "")
            if known_start[:10] != start[:10] or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", known_start):
                continue
            if known_start[11:] == "00:00:00":
                continue
            known_name = _hindley_identity(known.get("title"))
            known_url = str(known.get("link") or "").split("?", 1)[0].rstrip("/").casefold()
            # Require identical titles or identical event URLs. Do not borrow
            # times from similar-looking concerts or a different performance.
            if ((fresh_name and fresh_name == known_name)
                    or (fresh_url and fresh_url == known_url)):
                candidates.add(known_start)
        if len(candidates) == 1:
            fresh["datetime"] = candidates.pop()
            hindley_times_recovered += 1
    if hindley_times_recovered:
        print(f"Hindley Street Music Hall: recovered {hindley_times_recovered} "
              "verified start times from matching records")

    # Add newly scraped events.

    final_events.extend(
        all_new_events
    )

    # ----------------------------------------
    # Preserve unmatched upcoming/ongoing records
    # ----------------------------------------
    # An accepted scraper can miss individual events even when its total
    # count is healthy (for example, directory pagination changes).
    # Keep such records for manual review rather than silently deleting
    # them. A later run can still replace them when matching data returns.
    # Past events are not restored. Matching URLs or exact identities
    # indicate a refreshed or re-venued event, not a missing one.
    from datetime import date

    today = date.today().isoformat()

    def _is_upcoming_or_ongoing(event):
        start = str(event.get("datetime") or event.get("date") or "")[:10]
        end = str(event.get("end_datetime") or event.get("end_date") or "")[:10]
        last_day = end if end >= start else start
        return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_day)
                    and last_day >= today)

    def _event_url_identity(event):
        raw = str(event.get("link") or event.get("url") or "").strip()
        if not raw:
            return ""
        parsed = urlparse(raw)
        hostname = (parsed.hostname or "").lower().removeprefix("www.")
        path = parsed.path.rstrip("/").lower()
        return hostname + path if hostname and path else ""

    # Compare against both new and already-retained records, so a
    # source change or venue correction does not restore an old copy.
    current_keys = {event_key(e) for e in final_events}
    current_urls = {_event_url_identity(e) for e in final_events}
    current_urls.discard("")
    # Humanitix recurring bookings can have several independently dated
    # sessions under ONE URL. A refreshed session on one date must not
    # suppress an older, still-upcoming session on another date.
    current_humanitix_sessions = {
        (_event_url_identity(e), _date(e))
        for e in final_events
        if str(e.get("source", "")).startswith("Humanitix ")
        and _event_url_identity(e) and _date(e)
    }
    preserved_missing = []
    for old_event in existing_events:
        if not any(event_belongs_to_source(old_event, source)
                   for source in accepted_sources):
            continue
        if not _is_upcoming_or_ongoing(old_event):
            continue
        key = event_key(old_event)
        url_key = _event_url_identity(old_event)
        is_humanitix = str(old_event.get("source", "")).startswith("Humanitix ")
        if is_humanitix:
            # Match recurring sessions by booking URL AND calendar date.
            # Different dates are different events even with the same URL.
            already_refreshed = bool(
                url_key and (url_key, _date(old_event)) in current_humanitix_sessions
            )
        else:
            already_refreshed = bool(url_key and any(
                _event_url_identity(e) == url_key and _date(e) == _date(old_event)
                for e in final_events
            ))
        if key in current_keys or already_refreshed:
            continue
        final_events.append(old_event)
        preserved_missing.append(old_event)
        current_keys.add(key)
        if url_key:
            current_urls.add(url_key)
            if is_humanitix:
                current_humanitix_sessions.add((url_key, _date(old_event)))

    if preserved_missing:
        print(f"Preserved {len(preserved_missing)} unmatched future/ongoing "
              "events from accepted sources (review for cancellations).")
        for event in preserved_missing:
            print("  PRESERVED: " + str(event.get("title", ""))
                  + " | " + str(event.get("datetime", ""))[:10])

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
    for event in sorted(all_new_events, key=lambda e: e.get("source") in ("Ticketmaster Adelaide", "Moshtix Adelaide CBD", "AllEvents Adelaide and Surrounds")):

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

    # ASO performs at many venues. Prefer the orchestra's own listing over
    # another source for the SAME performance, never over another session.
    aso_events = [e for e in deduplicated_final_events
                  if e.get("source") == "Adelaide Symphony Orchestra"]
    other_events = [e for e in deduplicated_final_events
                    if e.get("source") != "Adelaide Symphony Orchestra"]
    aso_overlaps = 0
    if aso_events:
        retained = []
        for candidate in other_events:
            if any(_same_event(candidate, aso) for aso in aso_events):
                aso_overlaps += 1
            else:
                retained.append(candidate)
        deduplicated_final_events = aso_events + retained
    print(f"ASO: {aso_overlaps} same-performance cross-source overlaps excluded")

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
    # re and SequenceMatcher are imported at module level.

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

    # Museum-specific aliases: the official site may add "Exhibition" or a
    # year to the title, while SATC may list a street or "Various locations".
    # Require the same start date AND one of these distinctive event identities;
    # never use a loose match for other Museum events or festival activities.
    def museum_tourism_match(tourism_event, official_event):
        if official_event.get("source") != "South Australian Museum":
            return False
        if _date(tourism_event) != _date(official_event):
            return False
        a = comparable_title(tourism_event.get("title", ""))
        b = comparable_title(official_event.get("title", ""))
        identities = (
            "australian geographic nature photographer of the year",
            "on the terrace",
        )
        for identity in identities:
            if a == identity and (b == identity or b.startswith(identity + " ")):
                return True
        return False

    # Preserve SATC's published times when the official Museum listing
    # supplies only midnight placeholders. Do not alter a known official time.
    museum_times_recovered = 0
    for official in non_tourism:
        if official.get("source") != "South Australian Museum":
            continue
        matches = [t for t in tourism if museum_tourism_match(t, official)]
        if len(matches) != 1:
            continue
        satc = matches[0]
        official_start = str(official.get("datetime") or "")
        satc_start = str(satc.get("datetime") or "")
        if official_start.endswith("T00:00:00") and _time(satc):
            official["datetime"] = satc_start
            museum_times_recovered += 1
        official_end = str(official.get("end_datetime") or "")
        satc_end = str(satc.get("end_datetime") or "")
        if satc_end and _time(satc if not satc_end else {"datetime": satc_end}):
            if not official_end:
                # Same-day events may have no end_date in the Museum feed.
                official["end_datetime"] = satc_end
            elif official_end[:10] == satc_end[:10] and official_end.endswith("T23:59:59"):
                official["end_datetime"] = satc_end
    if museum_times_recovered:
        print(f"Museum: recovered {museum_times_recovered} SATC start times")

    # AGSA exhibitions can start months before today's scrape. SATC often
    # uses the true opening date, while other sources may use a different
    # venue label. For these ONLY, compare the named exhibition and its
    # overlapping date range instead of requiring equal opening dates.
    agsa_exhibitions = [e for e in non_tourism
                        if e.get("source") == "Art Gallery of South Australia"
                        and str(e.get("end_datetime") or "")[:10] > _date(e)]

    def same_agsa_exhibition(tourism_event, official_event):
        a = comparable_title(tourism_event.get("title", ""))
        b = comparable_title(official_event.get("title", ""))
        if not a or a != b or len(a) < 12:
            return False
        a_start = _date(tourism_event)
        b_start = _date(official_event)
        a_end = str(tourism_event.get("end_datetime") or "")[:10] or a_start
        b_end = str(official_event.get("end_datetime") or "")[:10] or b_start
        return bool(a_start and b_start and a_start <= b_end and b_start <= a_end)

    kept_tourism = []
    tourism_duplicates = 0
    for event in tourism:
        same_day = by_date.get(str(event.get("datetime", ""))[:10], [])
        if (any(tourism_matches_official(event, original) or
                museum_tourism_match(event, original) for original in same_day)
                or any(same_agsa_exhibition(event, original)
                       for original in agsa_exhibitions)):
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

    # AllEvents is an aggregator: retain official and previously curated
    # records where the same Victoria Square event is already listed.
    # Compare date, distinctive title and known times. Do not merge
    # different named activities at a festival.
    square_events = [e for e in final_events
                     if e.get("source") == "AllEvents Victoria Square"]
    other_events = [e for e in final_events
                    if e.get("source") != "AllEvents Victoria Square"]
    kept_square = []
    skipped_square = 0
    for candidate in square_events:
        title = comparable_title(candidate.get("title", ""))
        same_day = [e for e in other_events + kept_square
                    if overlaps(candidate, e)]
        duplicate = any(
            (title == comparable_title(other.get("title", ""))
             or (len(title) >= 18
                 and len(comparable_title(other.get("title", ""))) >= 18
                 and SequenceMatcher(None, title,
                     comparable_title(other.get("title", ""))).ratio() >= 0.94))
            and same_performance(candidate, other)
            for other in same_day
        )
        if duplicate:
            skipped_square += 1
        else:
            kept_square.append(candidate)
    final_events = other_events + kept_square
    print(f"AllEvents Victoria Square overlaps excluded: {skipped_square}")

    # Broad AllEvents is an aggregator. Prefer EVERY other source, including
    # other ticket platforms and previously curated events. Different dates,
    # venues or verified session times must remain separate.
    broad_source = "AllEvents Adelaide and Surrounds"
    broad_events = [e for e in final_events if e.get("source") == broad_source]
    other_events = [e for e in final_events if e.get("source") != broad_source]
    kept_broad = []
    broad_overlaps = 0
    for candidate in broad_events:
        title = comparable_title(candidate.get("title", ""))
        duplicate = False
        for other in other_events + kept_broad:
            if not overlaps(candidate, other):
                continue
            other_title = comparable_title(other.get("title", ""))
            if not (title == other_title or
                    (len(title) >= 18 and len(other_title) >= 18 and
                     SequenceMatcher(None, title, other_title).ratio() >= 0.94)):
                continue
            if (_venue_name(candidate.get("venue")) == _venue_name(other.get("venue"))
                    and same_performance(candidate, other)):
                duplicate = True
                break
        if duplicate:
            broad_overlaps += 1
        else:
            kept_broad.append(candidate)
    final_events = other_events + kept_broad
    print(f"AllEvents Adelaide and Surrounds overlaps excluded: {broad_overlaps}")

    # Humanitix is an event platform, not a venue authority. Prefer existing
    # venue/official entries for the same performance, date and venue.
    humanitix_sources = {"Humanitix Nineteen Ten", "Humanitix Adelaide and Regions"}
    humanitix_events = [e for e in final_events if e.get("source") in humanitix_sources]
    non_humanitix = [e for e in final_events if e.get("source") not in humanitix_sources]
    retained_humanitix = []
    humanitix_overlaps = 0
    for candidate in humanitix_events:
        candidate_title = comparable_title(candidate.get("title", ""))
        duplicate = False
        for other in non_humanitix + retained_humanitix:
            if not overlaps(candidate, other):
                continue
            if _venue_name(candidate.get("venue")) != _venue_name(other.get("venue")):
                continue
            other_title = comparable_title(other.get("title", ""))
            if candidate_title == other_title or (
                len(candidate_title) >= 18 and len(other_title) >= 18
                and SequenceMatcher(None, candidate_title, other_title).ratio() >= 0.94
            ):
                if same_performance(candidate, other):
                    duplicate = True
                    break
        if duplicate:
            humanitix_overlaps += 1
        else:
            retained_humanitix.append(candidate)
    final_events = non_humanitix + retained_humanitix
    print(f"Humanitix overlaps excluded: {humanitix_overlaps}")

    # Standardise Victoria Square venue labels across every source,
    # including older imported records with alternate spelling/case.
    victoria_aliases = {
        "victoria square / tarntanyangga",
        "victoria square / tartntanyangga",
        "victoria square / tarntanyangga",
    }
    venue_names_normalised = 0
    for event in final_events:
        current_venue = str(event.get("venue", "")).strip()
        if current_venue.casefold() in victoria_aliases:
            if current_venue != "Victoria Square / Tarntanyangga":
                event["venue"] = "Victoria Square / Tarntanyangga"
                venue_names_normalised += 1
    print(f"Victoria Square venue names standardised: {venue_names_normalised}")

    # Canonical Rhino Room label for all sources, including legacy records.
    rhino_renamed = 0
    for event in final_events:
        if str(event.get("venue", "")).strip().casefold() == "rhino room, adl":
            event["venue"] = "Rhino Room"
            rhino_renamed += 1
    print(f"Rhino Room venue names standardised: {rhino_renamed}")

    # Apply venue aliases to every record, including preserved old events.
    # Do this after matching so the source-specific duplicate rules stay intact.
    venue_updates = sum(standardise_venue(event) for event in final_events)
    print(f"Additional venue names standardised: {venue_updates}")

    # Apply only audited, deterministic corrections to fresh AND retained data.
    # The existing --preview mode reports changes without writing events.json.
    corrected_titles = 0
    corrected_categories = 0
    for event in final_events:
        corrections = apply_audited_data_corrections(event)
        corrected_titles += int("title encoding" in corrections)
        corrected_categories += int("category" in corrections)
    print(f"Audited title encoding fixes: {corrected_titles}")
    print(f"Audited category fixes: {corrected_categories}")

    # Suppress the two specifically identified cancelled Secret Garden listings,
    # including old records restored by the unmatched-event safety logic.
    cancelled_count = len(final_events)
    final_events = [event for event in final_events
                    if not is_cancelled_secret_garden(event)]
    print(f"Cancelled Secret Garden listings excluded: {cancelled_count - len(final_events)}")

    # Remove explicitly cancelled listings, including older records restored
    # by the preservation safeguard. This is source-independent and applies
    # to both fresh and retained events.
    explicitly_cancelled = sum(is_explicitly_cancelled(e) for e in final_events)
    final_events = [e for e in final_events if not is_explicitly_cancelled(e)]
    print(f"Explicitly cancelled listings excluded: {explicitly_cancelled}")

    # Batch 7: exclude only independently confirmed cancelled booking IDs.
    # Apply after preservation/merge so a retained old record cannot reappear.
    confirmed_cancelled = sum(is_confirmed_cancelled_booking(e) for e in final_events)
    final_events = [e for e in final_events if not is_confirmed_cancelled_booking(e)]
    print(f"Confirmed cancelled booking URLs excluded: {confirmed_cancelled}")

    # Permanently exclude unreliable AllEvents records, including legacy preserved ones.
    def _is_allevents(event):
        from urllib.parse import urlparse
        source = str(event.get("source", "")).lower()
        link = str(event.get("link") or event.get("url") or "")
        host = (urlparse(link).hostname or "").lower()
        return "allevents" in source or host == "allevents.in" or host.endswith(".allevents.in")
    removed_allevents = sum(_is_allevents(e) for e in final_events)
    final_events = [e for e in final_events if not _is_allevents(e)]
    print(f"AllEvents records excluded permanently: {removed_allevents}")

    # Use the official production portraits saved from the State Theatre 2027 season.
    # Keep images in this repository so GitHub Pages does not depend on hotlinks.
    for event in final_events:
        if event.get("source") == "State Theatre Company South Australia":
            official_image = STATE_THEATRE_OFFICIAL_IMAGES.get(event.get("title", ""))
            if official_image:
                event["image"] = official_image

    # Match official Thebarton posters by Ticketmaster ID after final deduplication.
    enrich_thebarton_images(final_events)
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

    # Repair information lost in earlier source-priority / exact-key passes.
    # This must happen AFTER venue normalisation and before the final audit.
    restored_details, invalid_end_dates = restore_richer_existing_event_details(
        final_events, existing_events
    )
    print(f"Richer existing event details restored: {len(restored_details)}")
    print(f"Invalid event end dates cleared: {len(invalid_end_dates)}")
    if "--preview" in sys.argv or "--preview-report" in sys.argv:
        repair_path = os.path.join(BASE_DIR, "event-detail-review.json")
        with open(repair_path, "w", encoding="utf-8") as output:
            json.dump({"repairs": restored_details,
                       "invalid_end_dates": invalid_end_dates},
                      output, indent=2, ensure_ascii=False)
        print(f"Event detail decisions saved to: {repair_path}")

    # One last cross-source pass after venue aliases have been standardised.
    # Only exact title/venue/date matches qualify; different timed shows survive.
    final_events, verified_overlap_audit = consolidate_verified_cross_source_duplicates(
        final_events
    )
    print(f"Verified cross-source duplicates excluded: {len(verified_overlap_audit)}")
    if "--preview" in sys.argv or "--preview-report" in sys.argv:
        audit_path = os.path.join(BASE_DIR, "duplicate-review.json")
        with open(audit_path, "w", encoding="utf-8") as output:
            json.dump(verified_overlap_audit, output, indent=2, ensure_ascii=False)
        print(f"Duplicate decisions saved to: {audit_path}")

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

    # Remove only byte-for-byte-equivalent event listings, not other
    # performances on the same day or different ticket links.
    unique_events = []
    exact_seen = set()
    for event in final_events:
        fingerprint = (
            str(event.get("title") or "").strip().casefold(),
            str(event.get("venue") or "").strip().casefold(),
            str(event.get("datetime") or ""),
            str(event.get("end_datetime") or ""),
            str(event.get("link") or "").strip(),
        )
        if fingerprint in exact_seen:
            continue
        exact_seen.add(fingerprint)
        unique_events.append(event)
    if len(unique_events) != len(final_events):
        print(f"Removed {len(final_events) - len(unique_events)} identical listings "
              "(same title, venue, start, end and link).")
    final_events = unique_events

    # Targeted, non-destructive retention of independently verified listings.
    # The Arkaba scraper can omit tomorrow's separately bookable Melbourne Cup
    # functions even while returning other current events. Keep their old
    # records until the date passes; do not invent any replacement listings.
    arkaba_cup_links = {
        "melbourne-cup-downstairs-2",
        "melbourne-cup-sportys-2",
        "melbourne-cup-top-of-the-ark",
    }
    from datetime import date as _date_class
    if _date_class.today().isoformat() <= "2026-11-03":
        retained_cup = 0
        for old in existing_events:
            if old.get("source") != "Arkaba Hotel" or str(old.get("datetime", ""))[:10] != "2026-11-03":
                continue
            link = str(old.get("link") or "")
            if not any(token in link for token in arkaba_cup_links):
                continue
            if any(str(e.get("link") or "") == link and str(e.get("datetime") or "")[:10] == "2026-11-03" for e in final_events):
                continue
            final_events.append(old.copy())
            retained_cup += 1
        print(f"Arkaba Melbourne Cup verified listings retained: {retained_cup}")

    # The Market's scraper sometimes replaces the specific workshop title
    # with a generic parent-series title. Restore only exact URL/date matches.
    seafood_titles = {
        "the-art-of-seafood-fish-for-the-table": "The Art of Seafood: Fish for the Table",
        "the-art-of-seafood-christmas-from-the-sea": "The Art of Seafood: Christmas from the Sea",
    }
    restored_seafood = 0
    for event in final_events:
        if event.get("source") != "Adelaide Central Market":
            continue
        link = str(event.get("link") or "")
        for slug, title in seafood_titles.items():
            if slug in link and event.get("title") != title:
                event["title"] = title
                restored_seafood += 1
                break
    print(f"Specific Art of Seafood workshop titles restored: {restored_seafood}")

    # Prefer the confirmed Showground start time to a date-only Play & Go copy.
    final_events = remove_verified_showground_aggregator_duplicates(final_events)

    # Apply verified co-listing rules to the stored database as well.
    final_events = remove_verified_festival_cross_source_duplicates(final_events)

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
    # Parse --only NAME and --only=NAME without treating the source name
    # as an unknown command-line option.
    allowed = {"--preview-report", "--preview", "--dry-run", "--quick"}
    args = sys.argv[1:]
    only_source = None
    unknown = []
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--only":
            if only_source is not None or index + 1 >= len(args) or args[index + 1].startswith("--"):
                print("ERROR: --only requires exactly one source name.")
                sys.exit(2)
            only_source = args[index + 1]
            index += 2
            continue
        if arg.startswith("--only="):
            if only_source is not None or not arg[len("--only="):].strip():
                print("ERROR: --only requires exactly one source name.")
                sys.exit(2)
            only_source = arg[len("--only="):]
            index += 1
            continue
        if arg not in allowed:
            unknown.append(arg)
        index += 1
    if unknown:
        print(f"ERROR: Unknown option(s): {', '.join(unknown)}")
        print("Use --preview, --preview-report, --dry-run, --quick, or --only SOURCE_NAME.")
        sys.exit(2)
    main(only_source=only_source)
