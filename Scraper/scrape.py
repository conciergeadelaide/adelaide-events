import json
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

    # ----------------------------------------
    # South Australia Tourism Commission
    # ----------------------------------------

    if name == "South Australia Tourism Commission":
        return parse_south_australia_tourism(None, url)

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

    for source in SOURCES:
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

    for source in SOURCES:

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

    # Fresh records first.
    for event in all_new_events:

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

    save_events(
        final_events
    )

    print()

    print(
        "Scrape complete."
    )


if __name__ == "__main__":
    main()