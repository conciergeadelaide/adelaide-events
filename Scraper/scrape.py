import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import SOURCES

from parsers import (
    parse_json_ld,
    parse_adelaide_festival_centre,
    parse_adelaide_oval,
    parse_adelaide_convention_centre
)


OUTPUT_FILE = (
    Path(__file__).resolve().parent.parent
    / "events.json"
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


def fetch_page(url):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30
        )

        response.raise_for_status()

        return response.text

    except requests.RequestException as error:

        print(f"Could not access {url}")
        print(f"Error: {error}")

        return None


def clean_event(event, source):

    if not event.get("url"):
        event["url"] = source["url"]

    if not event.get("venue"):
        event["venue"] = source["name"]

    if not event.get("location"):
        event["location"] = "Adelaide"

    return event


def event_key(event):

    title = (
        event.get("title", "")
        .lower()
        .strip()
    )

    venue = (
        event.get("venue", "")
        .lower()
        .strip()
    )

    date = event.get(
        "datetime",
        ""
    )[:10]

    return f"{title}|{venue}|{date}"


def remove_past_events(events):

    today = datetime.now().date()

    future_events = []

    for event in events:

        date_value = event.get(
            "datetime",
            ""
        )[:10]

        try:

            event_date = datetime.strptime(
                date_value,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            future_events.append(event)

            continue

        if event_date >= today:

            future_events.append(event)

    return future_events


def scrape_adelaide_festival_centre(source):

    base_url = source["url"].rstrip("/")

    all_events = []

    seen_urls = set()

    page_number = 1

    while True:

        if page_number == 1:

            page_url = base_url

        else:

            page_url = (
                f"{base_url}/p{page_number}"
            )

        print(
            f"\nAFC page {page_number}:"
        )

        print(page_url)

        html = fetch_page(page_url)

        if not html:

            print(
                "AFC page could not be accessed."
            )

            break

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        events = parse_adelaide_festival_centre(
            soup
        )

        print(
            f"Found {len(events)} AFC events"
        )

        if not events:
            break

        new_events = 0

        for event in events:

            event = clean_event(
                event,
                source
            )

            key = event_key(event)

            if key in seen_urls:
                continue

            seen_urls.add(key)

            all_events.append(event)

            new_events += 1

        if new_events == 0:
            break

        next_link = None

        for link in soup.find_all(
            "a",
            href=True
        ):

            text = link.get_text(
                " ",
                strip=True
            ).lower()

            if text == "next":

                next_link = urljoin(
                    page_url,
                    link["href"]
                )

                break

        if not next_link:
            break

        page_number += 1

        if page_number > 100:

            print(
                "AFC safety limit reached."
            )

            break

        time.sleep(1)

    return all_events


def scrape_source(source):

    print(
        "\n======================================"
    )

    print(
        f"Checking: {source['name']}"
    )

    print(source["url"])

    print(
        "======================================"
    )


    # ----------------------------------
    # Adelaide Festival Centre
    # ----------------------------------

    if source["name"] == "Adelaide Festival Centre":

        events = scrape_adelaide_festival_centre(
            source
        )

        print(
            f"\nTotal AFC events collected: "
            f"{len(events)}"
        )

        return events


    # ----------------------------------
    # Adelaide Oval
    # ----------------------------------

    if source["name"] == "Adelaide Oval":

        html = fetch_page(
            source["url"]
        )

        if not html:
            return None

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        events = parse_adelaide_oval(
            soup
        )

        cleaned_events = []

        for event in events:

            event = clean_event(
                event,
                source
            )

            if (
                event.get("title")
                and event.get("datetime")
            ):

                cleaned_events.append(
                    event
                )

        print(
            "\nTotal Adelaide Oval events "
            f"collected: {len(cleaned_events)}"
        )

        return cleaned_events


    # ----------------------------------
    # Adelaide Convention Centre
    # ----------------------------------

    if (
        source["name"]
        == "Adelaide Convention Centre"
    ):

        html = fetch_page(
            source["url"]
        )

        if not html:

            return None

        soup = BeautifulSoup(
            html,
            "lxml"
        )

        events = parse_adelaide_convention_centre(
            soup
        )

        cleaned_events = []

        for event in events:

            event = clean_event(
                event,
                source
            )

            if (
                event.get("title")
                and event.get("datetime")
            ):

                cleaned_events.append(
                    event
                )

        print(
            "\nTotal Adelaide Convention Centre "
            f"events collected: {len(cleaned_events)}"
        )

        return cleaned_events


    # ----------------------------------
    # Generic JSON-LD parser
    # ----------------------------------

    html = fetch_page(
        source["url"]
    )

    if not html:

        return None

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    events = parse_json_ld(
        soup
    )

    cleaned_events = []

    for event in events:

        event = clean_event(
            event,
            source
        )

        if (
            event.get("title")
            and event.get("datetime")
        ):

            cleaned_events.append(
                event
            )

    print(
        f"Found {len(cleaned_events)} events"
    )

    return cleaned_events


def load_existing_events():

    if not OUTPUT_FILE.exists():

        return []

    try:

        with open(
            OUTPUT_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            data = json.load(file)

        if isinstance(data, list):

            return data

    except Exception as error:

        print(
            "Could not read existing "
            f"events.json: {error}"
        )

    return []


def save_events(events):

    events.sort(
        key=lambda event: event.get(
            "datetime",
            ""
        )
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            events,
            file,
            indent=4,
            ensure_ascii=False
        )


def main():

    print(
        "======================================"
    )

    print(
        " Adelaide Events Scraper"
    )

    print(
        "======================================"
    )


    existing_events = load_existing_events()

    print(
        f"Existing events: "
        f"{len(existing_events)}"
    )


    all_events = []

    seen = set()

    successful_sources = 0


    for source in SOURCES:

        events = scrape_source(
            source
        )

        # If a source completely fails,
        # protect existing events.

        if events is None:

            print(
                "Source failed — "
                "existing events are protected."
            )

            continue


        successful_sources += 1


        for event in events:

            key = event_key(
                event
            )

            if key in seen:
                continue

            seen.add(key)

            all_events.append(
                event
            )


        time.sleep(1)


    # ----------------------------------
    # Safety check
    # ----------------------------------

    if successful_sources == 0:

        print(
            "\nNo sources were successfully "
            "checked."
        )

        print(
            "Existing events.json has "
            "NOT been changed."
        )

        return


    # ----------------------------------
    # Preserve existing events that
    # weren't replaced by successful
    # scraper sources.
    # ----------------------------------

    merged = []


    for event in existing_events:

        key = event_key(
            event
        )

        if key in seen:

            continue

        seen.add(key)

        merged.append(
            event
        )


    merged.extend(
        all_events
    )


    # ----------------------------------
    # Safety check
    # ----------------------------------

    if not merged:

        print(
            "\nNo events available."
        )

        print(
            "Existing events.json has "
            "NOT been changed."
        )

        return


    # ----------------------------------
    # Remove events before today
    # ----------------------------------

    merged = remove_past_events(
        merged
    )


    # ----------------------------------
    # Save
    # ----------------------------------

    save_events(
        merged
    )


    print(
        "\n======================================"
    )

    print(
        f"New scraped events: "
        f"{len(all_events)}"
    )

    print(
        f"Final event count: "
        f"{len(merged)}"
    )

    print(
        f"Saved to: {OUTPUT_FILE}"
    )

    print(
        "======================================"
    )


if __name__ == "__main__":

    main()