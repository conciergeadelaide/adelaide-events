import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


LISTING_URL = (
    "https://www.adelaideentertainmentcentre.com.au/events/"
)

BASE_URL = (
    "https://www.adelaideentertainmentcentre.com.au"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def clean_text(text):
    return " ".join(
        (text or "").replace("\xa0", " ").split()
    )


def get_soup(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return BeautifulSoup(
        response.text,
        "lxml"
    )


def discover_event_links():

    soup = get_soup(LISTING_URL)

    links = []

    for a in soup.find_all("a", href=True):

        href = a.get("href", "").strip()

        if not href:
            continue

        url = urljoin(
            LISTING_URL,
            href
        )

        if not url.startswith(
            BASE_URL + "/events/"
        ):
            continue

        if url.rstrip("/") == LISTING_URL.rstrip("/"):
            continue

        if url not in links:
            links.append(url)

    return links


def extract_title(soup):

    h1 = soup.find("h1")

    if h1:

        title = clean_text(
            h1.get_text(
                " ",
                strip=True
            )
        )

        if title:
            return title

    meta = soup.find(
        "meta",
        property="og:title"
    )

    if meta:

        return clean_text(
            meta.get(
                "content",
                ""
            )
        )

    return ""


def extract_image(soup):

    backgrounds = soup.find_all(
        attrs={
            "data-background-image": True
        }
    )

    for element in backgrounds:

        image = element.get(
            "data-background-image",
            ""
        ).strip()

        if not image:
            continue

        lower = image.lower()

        if any(
            word in lower
            for word in [
                "getting-here",
                "eat-and-drink",
                "accessibility",
                "faq",
                "logo",
                "icon"
            ]
        ):
            continue

        return urljoin(
            BASE_URL,
            image
        )

    return ""


def parse_datetime(
    day,
    month,
    year,
    time_text=""
):

    day = str(day).strip()
    month = str(month).strip()
    year = str(year).strip()
    time_text = clean_text(time_text)

    if time_text:

        datetime_text = (
            day +
            " " +
            month +
            " " +
            year +
            " " +
            time_text
        )

        formats = [
            "%d %B %Y %I:%M%p",
            "%d %B %Y %I%p",
            "%d %b %Y %I:%M%p",
            "%d %b %Y %I%p"
        ]

    else:

        datetime_text = (
            day +
            " " +
            month +
            " " +
            year
        )

        formats = [
            "%d %B %Y",
            "%d %b %Y"
        ]

    for fmt in formats:

        try:

            parsed = datetime.strptime(
                datetime_text,
                fmt
            )

            return parsed.isoformat()

        except ValueError:
            pass

    return ""


def find_when_block(soup):

    when_heading = soup.find(
        string=lambda text:
        text
        and clean_text(text).lower() == "when"
    )

    if not when_heading:
        return None

    heading = when_heading.parent

    if not heading:
        return None

    container = heading.parent

    if not container:
        return None

    return container


def extract_authoritative_date(soup):

    container = find_when_block(soup)

    if not container:
        return None

    date_element = container.find(
        class_=lambda value:
        value
        and "content-block--event-date"
        in (
            " ".join(value)
            if isinstance(value, list)
            else value
        )
    )

    if not date_element:
        return None

    date_text = clean_text(
        date_element.get_text(
            " ",
            strip=True
        )
    )

    pattern = re.compile(
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|"
        r"Monday|Tuesday|Wednesday|Thursday|Friday|"
        r"Saturday|Sunday),?\s+"
        r"(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|"
        r"Nov|Dec|January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+(\d{4})",
        re.IGNORECASE
    )

    match = pattern.search(date_text)

    if not match:
        return None

    venue = "Adelaide Entertainment Centre"

    lower = date_text.lower()

    if "theatre" in lower:

        venue = (
            "Adelaide Entertainment Centre Theatre"
        )

    elif "arena" in lower:

        venue = (
            "Adelaide Entertainment Centre Arena"
        )

    return {
        "day": match.group(1),
        "month": match.group(2),
        "year": match.group(3),
        "venue": venue,
        "raw_date": date_text,
        "container": container
    }


def extract_header_time(soup):

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    full_pattern = re.compile(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
        r"Saturday|Sunday),?\s+"
        r"\d{1,2}\s+"
        r"(?:January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+"
        r"\d{4}\s*[–—-]\s*"
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        re.IGNORECASE
    )

    match = full_pattern.search(text)

    if match:
        return clean_text(
            match.group(1)
        )


    short_pattern = re.compile(
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|"
        r"Monday|Tuesday|Wednesday|Thursday|Friday|"
        r"Saturday|Sunday),?\s+"
        r"\d{1,2}\s+"
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|"
        r"Nov|Dec)\s+"
        r"\d{4}\s*[|–—-]\s*"
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        re.IGNORECASE
    )

    match = short_pattern.search(text)

    if match:
        return clean_text(
            match.group(1)
        )

    return ""


def extract_start_time_from_when(container):

    if not container:
        return ""

    paragraphs = container.find_all("p")

    preferred_labels = [
        "match start",
        "show start",
        "show starts",
        "performance start",
        "performance starts",
        "event start",
        "event starts",
        "concert start",
        "concert starts"
    ]

    for paragraph in paragraphs:

        text = clean_text(
            paragraph.get_text(
                " ",
                strip=True
            )
        )

        lower = text.lower()

        for label in preferred_labels:

            pattern = re.compile(
                r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))"
                r"\s*[–—-]\s*"
                + re.escape(label),
                re.IGNORECASE
            )

            match = pattern.search(text)

            if match:

                return clean_text(
                    match.group(1)
                )

    return ""


def extract_date_and_venue(soup):

    authoritative = (
        extract_authoritative_date(soup)
    )

    if authoritative:

        # The "When" block is trusted for the
        # actual day/month/year and venue.
        #
        # First try to obtain an explicit
        # Match Start / Show Start time from
        # the same block.

        time_text = (
            extract_start_time_from_when(
                authoritative["container"]
            )
        )

        # If there is no explicit start label,
        # use the main event heading's time.
        #
        # Importantly, only the TIME is taken
        # from the heading. The YEAR always
        # comes from the authoritative When
        # block.

        if not time_text:

            time_text = (
                extract_header_time(soup)
            )

        event_datetime = parse_datetime(
            authoritative["day"],
            authoritative["month"],
            authoritative["year"],
            time_text
        )

        return (
            event_datetime,
            authoritative["venue"],
            authoritative["raw_date"]
        )


    # -----------------------------------
    # FALLBACK
    #
    # Used only if a page does not contain
    # the normal "When" event-details block.
    # -----------------------------------

    text = clean_text(
        soup.get_text(
            " ",
            strip=True
        )
    )

    full_month_pattern = re.compile(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|"
        r"Saturday|Sunday),?\s+"
        r"(\d{1,2})\s+"
        r"(January|February|March|April|May|June|July|"
        r"August|September|October|November|December)\s+"
        r"(\d{4})"
        r"(?:\s*[–—-]\s*"
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)))?",
        re.IGNORECASE
    )

    match = full_month_pattern.search(text)

    if match:

        event_datetime = parse_datetime(
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4) or ""
        )

        venue = extract_venue_near_match(
            text,
            match
        )

        return (
            event_datetime,
            venue,
            match.group(0)
        )


    short_month_pattern = re.compile(
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|"
        r"Monday|Tuesday|Wednesday|Thursday|Friday|"
        r"Saturday|Sunday),?\s+"
        r"(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|"
        r"Nov|Dec)\s+"
        r"(\d{4})"
        r"(?:\s*[|–—-]\s*"
        r"(\d{1,2}(?::\d{2})?\s*(?:am|pm)))?",
        re.IGNORECASE
    )

    match = short_month_pattern.search(text)

    if match:

        event_datetime = parse_datetime(
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4) or ""
        )

        venue = extract_venue_near_match(
            text,
            match
        )

        return (
            event_datetime,
            venue,
            match.group(0)
        )

    return "", "", ""


def extract_venue_near_match(
    text,
    match
):

    nearby = text[
        match.start():
        match.end() + 250
    ].lower()

    if "theatre" in nearby:

        return (
            "Adelaide Entertainment Centre Theatre"
        )

    if "arena" in nearby:

        return (
            "Adelaide Entertainment Centre Arena"
        )

    return "Adelaide Entertainment Centre"


def guess_category(title):

    lower = title.lower()

    sport_words = [
        "36ers",
        "basketball",
        "darts",
        "wrestling",
        "mega mania"
    ]

    family_words = [
        "wiggles",
        "disney",
        "family"
    ]

    comedy_words = [
        "comedy",
        "comedian",
        "gabriel iglesias",
        "paul smith",
        "aaron chen",
        "morgan jay"
    ]

    if any(
        word in lower
        for word in sport_words
    ):
        return "Sport"

    if any(
        word in lower
        for word in family_words
    ):
        return "Family"

    if any(
        word in lower
        for word in comedy_words
    ):
        return "Comedy"

    return "Music"


def is_cancelled(title):

    lower = title.lower()

    return (
        "cancelled" in lower
        or "canceled" in lower
    )


def scrape_event(url):

    soup = get_soup(url)

    title = extract_title(soup)

    if is_cancelled(title):
        return None

    event_datetime, venue, raw_date = (
        extract_date_and_venue(soup)
    )

    image = extract_image(soup)

    category = guess_category(title)

    return {
        "title": title,
        "datetime": event_datetime,
        "venue": venue,
        "category": category,
        "image": image,
        "url": url,
        "raw_date": raw_date
    }


def main():

    print(
        "========================================"
    )

    print(
        " Adelaide Entertainment Centre Test"
    )

    print(
        "========================================"
    )

    print()

    print(
        "Finding event links..."
    )

    links = discover_event_links()

    print(
        "Event links found:",
        len(links)
    )

    print()


    events = []

    cancelled = []


    for number, url in enumerate(
        links,
        start=1
    ):

        try:

            event = scrape_event(url)

            if event is None:

                cancelled.append(url)

                print(
                    str(number) +
                    ". CANCELLED - SKIPPED"
                )

                print(
                    "   URL:",
                    url
                )

                print()

                continue

            events.append(event)

            print(
                str(number) +
                ". " +
                event["title"]
            )

            print(
                "   Date:",
                event["datetime"]
                or "NOT FOUND"
            )

            print(
                "   Venue:",
                event["venue"]
                or "NOT FOUND"
            )

            print(
                "   Category:",
                event["category"]
            )

            print(
                "   Image:",
                "YES"
                if event["image"]
                else "NO"
            )

            print(
                "   URL:",
                event["url"]
            )

            print()

        except Exception as exc:

            print(
                str(number) +
                ". ERROR"
            )

            print(
                "   URL:",
                url
            )

            print(
                "   Error:",
                exc
            )

            print()


    print(
        "========================================"
    )

    print(
        " SUMMARY"
    )

    print(
        "========================================"
    )

    print(
        "Links:",
        len(links)
    )

    print(
        "Active events processed:",
        len(events)
    )

    print(
        "Cancelled skipped:",
        len(cancelled)
    )

    print(
        "Dates found:",
        sum(
            1
            for event in events
            if event["datetime"]
        )
    )

    print(
        "Images found:",
        sum(
            1
            for event in events
            if event["image"]
        )
    )

    print()


    missing_dates = [
        event
        for event in events
        if not event["datetime"]
    ]

    if missing_dates:

        print(
            "EVENTS WITH NO DATE:"
        )

        for event in missing_dates:

            print(
                "-",
                event["title"],
                "|",
                event["url"]
            )

    else:

        print(
            "SUCCESS: All active events have dates."
        )


    # -----------------------------------
    # Special verification
    # -----------------------------------

    print()

    print(
        "DATE VERIFICATION:"
    )

    for event in events:

        if (
            "south-east-melbourne-phoenix-8"
            in event["url"]
        ):

            print(
                "Phoenix game:",
                event["datetime"]
            )


if __name__ == "__main__":
    main()