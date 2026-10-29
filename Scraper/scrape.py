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
    from humanitix import scrape_humanitix
except ModuleNotFoundError:
    from Scraper.humanitix import scrape_humanitix

try:
    # Works when running:
    # python Scraper\scrape.py
    from config import SOURCES
    from parsers import (
        parse_json_ld,
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
        parse_allevents_victoria_square,
        parse_allevents_adelaide_and_surrounds,
    )
except ModuleNotFoundError:
    # Works when importing:
    # from Scraper.scrape import ...
    from Scraper.config import SOURCES
    from Scraper.parsers import (
        parse_json_ld,
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
        parse_allevents_victoria_square,
        parse_allevents_adelaide_and_surrounds,
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


def save_events(events):
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
    "adel ent cent - theatre": "Adelaide Entertainment Centre",
    "lucky dumpling market, elder park": "Elder Park",
    "ellis park - tampawardli - city west": "Ellis Park",
}

# Specific cancelled event IDs, not a blanket title-based ban. This avoids
# accidentally removing unrelated future performances with similar names.
CANCELLED_EVENT_IDS = {
    "3300029954876416",  # Secret Garden in Adelaide
    "200030161153327",   # Secret Garden Live in Hindmarsh 2026
}


def standardise_venue(event):
    venue = str(event.get("venue") or "").strip()
    canonical = VENUE_ALIASES.get(venue.casefold())
    if canonical and canonical != venue:
        event["venue"] = canonical
        return True
    return False


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

    # ASO may schedule multiple distinct performances on the same date.
    session_key = (str(event.get("datetime", ""))
                   if event.get("source") == "Adelaide Symphony Orchestra"
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

    if name == "Humanitix Nineteen Ten":
        return scrape_humanitix(host_only=True)

    if name == "Humanitix Adelaide and Regions":
        return scrape_humanitix(host_only=False)

    if name == "The Gov":
        return parse_the_gov()

    if name == "Morphettville Racecourse":
        return parse_morphettville_racecourse(fetch_page("https://morphettville.com.au/"), "https://morphettville.com.au/")

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

    for source in list(SOURCES) + [{"name": "Moshtix Adelaide CBD", "url": "https://www.moshtix.com.au/v2/search"}, {"name": "Humanitix Nineteen Ten", "url": "https://events.humanitix.com/host/nineteentenadl"}, {"name": "Humanitix Adelaide and Regions", "url": "https://humanitix.com/au/events/au--sa--adelaide"}]:
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

    if source_name == "Thebarton Theatre" and explicit_source:
        return False

    # Humanitix sources share the same event URL domain. Never classify
    # a Nineteen Ten host event as a general-directory event (or vice versa).
    if source_name.startswith("Humanitix "):
        return False

    if source_name.startswith("AllEvents ") and explicit_source:
        return explicit_source == wanted

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
        {"name": "Carrick Hill", "url": "https://www.carrickhill.sa.gov.au/visit/whats-on"},
        {"name": "Jetty Road Glenelg", "url": "https://www.jettyroadglenelg.com.au/whats-on"},
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
        print(f"SINGLE-SOURCE TEST: {matches[0]['name']}")
        print("Only this source will be fetched. events.json will not be changed.\n")

    # Optional quick mode: skip generic sites that returned zero events
    # in the last verified full run. Skipped sources retain their records.
    # Run without --quick regularly to discover new events at these sites.
    if "--quick" in sys.argv and only_source is None:
        known_empty_generic_sources = {
            "Nineteen Ten",
            "Adelaide Repertory Theatre",
            "Adelaide Botanic Gardens",
            "Adelaide Cemetery Tours",
            "Trinity Sessions", "Morphettville Racecourse",
            "Holden Street Theatres",
            "Baroque Hall",
            "MOD.", "SAMSTAG Museum",
            "Kerry Packer Civic Gallery",
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
        print("\n----------------------------------------")
        print(f"Source tested: {configured_sources[0]['name']}")
        print(f"New records collected: {len(all_new_events)}")
        print(f"Source accepted: {bool(accepted_sources)}")
        print(f"Existing events retained: {len(existing_events)}")
        print("SINGLE-SOURCE TEST COMPLETE: events.json was NOT changed.")
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
            already_refreshed = bool(url_key and url_key in current_urls)
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

    kept_tourism = []
    tourism_duplicates = 0
    for event in tourism:
        same_day = by_date.get(str(event.get("datetime", ""))[:10], [])
        if any(tourism_matches_official(event, original) or
               museum_tourism_match(event, original) for original in same_day):
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
        "victoria square / tartanyangga",
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
