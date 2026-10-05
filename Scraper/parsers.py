import json
import re
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


# ============================================================
# COMMON HELPERS
# ============================================================

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def normalise_url(url, source_url):
    if not url:
        return ""

    return urljoin(source_url, url)


def parse_date_text(text):
    if not text:
        return ""

    text = " ".join(str(text).split())

    # ISO
    match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)

    if match:
        try:
            return datetime(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            ).strftime("%Y-%m-%dT00:00:00")
        except Exception:
            pass

    # DD Month YYYY
    match = re.search(
        r"\b(\d{1,2})\s+"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(20\d{2})\b",
        text,
        re.I,
    )

    if match:
        try:
            return datetime(
                int(match.group(3)),
                MONTHS[match.group(2).lower()],
                int(match.group(1)),
            ).strftime("%Y-%m-%dT00:00:00")
        except Exception:
            pass

    # Month DD YYYY
    match = re.search(
        r"\b"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),?\s+(20\d{2})\b",
        text,
        re.I,
    )

    if match:
        try:
            return datetime(
                int(match.group(3)),
                MONTHS[match.group(1).lower()],
                int(match.group(2)),
            ).strftime("%Y-%m-%dT00:00:00")
        except Exception:
            pass

    # AFC-style dates with apostrophe years, e.g. 16 Oct '26,
    # 9–13 Sept '26, 26 Sept–4 Oct '26. For ranges, use the
    # first/start date.
    short_months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
    }

    afc = re.search(
        r"\b(\d{1,2})\s*(?:[–—-]\s*\d{1,2}\s*)?"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
        r"(?:\s*[–—-]\s*\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec))?"
        r"\s*[’'](\d{2})\b",
        text,
        re.I,
    )
    if afc:
        try:
            return datetime(
                2000 + int(afc.group(3)),
                short_months[afc.group(2).lower()],
                int(afc.group(1)),
            ).strftime("%Y-%m-%dT00:00:00")
        except Exception:
            pass

    # DD Mon YYYY
    short_months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "sept": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }

    match = re.search(
        r"\b(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
        r"\s+(20\d{2})\b",
        text,
        re.I,
    )

    if match:
        try:
            return datetime(
                int(match.group(3)),
                short_months[match.group(2).lower()],
                int(match.group(1)),
            ).strftime("%Y-%m-%dT00:00:00")
        except Exception:
            pass

    return ""


def get_image(element, source_url):
    if not element:
        return ""

    img = element.find("img")

    if img:
        value = (
            img.get("src")
            or img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("data-original")
            or ""
        )

        if value:
            return normalise_url(value, source_url)

    source = element.find("source")

    if source:
        value = (
            source.get("src")
            or source.get("data-src")
            or ""
        )

        if value:
            return normalise_url(value, source_url)

    return ""


# ============================================================
# GENERIC JSON-LD
# ============================================================

def parse_json_ld(soup, source_url):
    events = []

    for script in soup.find_all(
        "script",
        type="application/ld+json",
    ):
        try:
            raw = script.string or script.get_text()
            data = json.loads(raw)
        except Exception:
            continue

        if isinstance(data, dict):
            if "@graph" in data:
                items = data["@graph"]
            else:
                items = [data]

        elif isinstance(data, list):
            items = data

        else:
            continue

        for item in items:
            if not isinstance(item, dict):
                continue

            item_type = item.get("@type", "")

            if isinstance(item_type, list):
                is_event = "Event" in item_type
            else:
                is_event = item_type == "Event"

            if not is_event:
                continue

            title = str(
                item.get("name", "")
            ).strip()

            if not title:
                continue

            date = item.get("startDate", "")

            if isinstance(date, str):
                parsed_date = parse_date_text(date)

                if not parsed_date:
                    parsed_date = date
            else:
                parsed_date = ""

            location = item.get("location", "")

            venue = ""

            if isinstance(location, dict):
                venue = str(
                    location.get("name")
                    or ""
                ).strip()

            elif isinstance(location, list):
                names = []

                for loc in location:
                    if isinstance(loc, dict):
                        name = loc.get("name")

                        if name:
                            names.append(str(name))

                venue = ", ".join(names)

            elif location:
                venue = str(location).strip()

            image = item.get("image", "")

            if isinstance(image, list):
                image = image[0] if image else ""

            url = (
                item.get("url")
                or source_url
            )

            events.append(
                {
                    "title": title,
                    "venue": venue,
                    "date": parsed_date,
                    "end_date": "",
                    "category": "Other",
                    "image": normalise_url(
                        image,
                        source_url,
                    ),
                    "url": normalise_url(
                        url,
                        source_url,
                    ),
                }
            )

    return events


# ============================================================
# ADELAIDE OVAL
# ============================================================

def parse_adelaide_oval(soup, source_url):
    events = []
    seen = set()

    for link in soup.find_all("a", href=True):
        href = normalise_url(
            link.get("href"),
            source_url,
        )

        text = " ".join(
            link.stripped_strings
        ).strip()

        if not text:
            continue

        lower = text.lower()

        if not any(
            keyword in lower
            for keyword in [
                "sheffield shield",
                "bbl",
                "wbbl",
                "odi",
                "test",
                "robbie williams",
                "concert",
            ]
        ):
            continue

        parent = link

        for _ in range(10):
            if parent.parent:
                parent = parent.parent

        block = " ".join(
            parent.stripped_strings
        )

        date = parse_date_text(block)

        if not date:
            continue

        key = (
            text.lower(),
            date,
        )

        if key in seen:
            continue

        seen.add(key)

        events.append(
            {
                "title": text,
                "venue": "Adelaide Oval",
                "date": date,
                "end_date": "",
                "category": "Sport & Entertainment",
                "image": get_image(
                    parent,
                    source_url,
                ),
                "url": href,
            }
        )

    return events


# ============================================================
# ADELAIDE CONVENTION CENTRE
# ============================================================

def parse_adelaide_convention_centre(soup, source_url):
    """Parse only genuine ACC event pages and read their clean metadata."""

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    })

    events = []
    event_urls = []
    seen_urls = set()
    base_events_url = source_url.rstrip("/").lower()

    for link in soup.find_all("a", href=True):
        href = normalise_url(link.get("href"), source_url)
        if not href:
            continue

        clean_href = href.split("#", 1)[0].split("?", 1)[0].rstrip("/")
        lower_href = clean_href.lower()

        if "adelaidecc.com.au/events/" not in lower_href:
            continue
        if lower_href == base_events_url:
            continue
        if lower_href in seen_urls:
            continue

        seen_urls.add(lower_href)
        event_urls.append(clean_href + "/")

    for event_url in event_urls:
        try:
            response = session.get(event_url, timeout=30)
            response.raise_for_status()
            event_soup = BeautifulSoup(response.text, "lxml")
        except Exception as exc:
            print(f"    ACC event page ERROR: {event_url} -> {exc}")
            continue

        heading = event_soup.find("h1")
        title = " ".join(heading.stripped_strings).strip() if heading else ""

        if not title:
            og_title = event_soup.find("meta", attrs={"property": "og:title"})
            if og_title:
                title = str(og_title.get("content", "")).strip()

        if not title:
            continue

        structured = parse_json_ld(event_soup, event_url)
        structured_event = structured[0] if structured else None

        date = ""
        end_date = ""
        image = ""

        if structured_event:
            date = str(structured_event.get("date", "")).strip()
            end_date = str(structured_event.get("end_date", "")).strip()
            image = str(structured_event.get("image", "")).strip()

        if not date:
            page_text = " ".join(event_soup.stripped_strings)
            date = parse_date_text(page_text)

        if not date:
            continue

        # ACC loads the current event artwork lazily as a background image.
        # The first data-background-image on the individual event page is the
        # current event hero; later background images can be related events.
        hero = event_soup.find(attrs={"data-background-image": True})
        if hero:
            candidate = str(hero.get("data-background-image", "")).strip()
            lower_candidate = candidate.lower()

            if (
                candidate
                and "logo" not in lower_candidate
                and "favicon" not in lower_candidate
                and "avmc-logo" not in lower_candidate
            ):
                image = normalise_url(candidate, event_url)

        # Fall back to social metadata only if no event hero was found.
        if not image:
            for attr_name, attr_value in [
                ("property", "og:image"),
                ("name", "twitter:image"),
            ]:
                meta = event_soup.find("meta", attrs={attr_name: attr_value})
                if not meta:
                    continue

                candidate = str(meta.get("content", "")).strip()
                lower_candidate = candidate.lower()

                if (
                    candidate
                    and "logo" not in lower_candidate
                    and "favicon" not in lower_candidate
                    and "avmc-logo" not in lower_candidate
                ):
                    image = normalise_url(candidate, event_url)
                    break

        if (
            not image
            or "logo" in image.lower()
            or "favicon" in image.lower()
            or "avmc-logo" in image.lower()
        ):
            image = ""

        events.append({
            "title": title,
            "venue": "Adelaide Convention Centre",
            "date": date,
            "end_date": end_date,
            "category": "Other",
            "image": image,
            "url": event_url,
        })

    return events


# ============================================================
# ADELAIDE FESTIVAL CENTRE
# ============================================================

def parse_adelaide_festival_centre(
    soup,
    source_url,
):
    """
    Parse Adelaide Festival Centre What's On cards directly.
    """

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            )
        }
    )

    events = []
    seen_urls = set()
    seen_page_signatures = set()

    def afc_datetime(value):
        if not value:
            return ""

        value = str(value).strip()

        match = re.fullmatch(r"(\d{2})-(\d{2})-(\d{2})", value)
        if match:
            try:
                return datetime(
                    2000 + int(match.group(1)),
                    int(match.group(2)),
                    int(match.group(3)),
                ).strftime("%Y-%m-%dT00:00:00")
            except ValueError:
                return ""

        return parse_date_text(value)

    def afc_image(card, page_url):
        img = card.find("img")
        if not img:
            return ""

        srcset = img.get("data-srcset") or img.get("srcset") or ""

        if srcset:
            first = srcset.split(",")[0].strip()
            if first:
                image_url = first.split()[0]
                if image_url and not image_url.startswith("data:"):
                    return normalise_url(image_url, page_url)

        value = (
            img.get("data-src")
            or img.get("data-lazy-src")
            or img.get("data-original")
            or img.get("src")
            or ""
        )

        if value and not value.startswith("data:"):
            return normalise_url(value, page_url)

        return ""

    def afc_category(card):
        labels = []

        for element in card.find_all(attrs={"aria-label": True}):
            label = " ".join(
                str(element.get("aria-label", "")).split()
            ).strip()
            if label:
                labels.append(label)

        joined = " ".join(labels).lower()

        if any(x in joined for x in ["music", "concert", "cabaret"]):
            return "Music"
        if any(x in joined for x in ["theatre", "opera", "ballet", "dance"]):
            return "Theatre"
        if "comedy" in joined:
            return "Comedy"
        if any(x in joined for x in ["kids", "families", "family"]):
            return "Family"
        if any(x in joined for x in ["workshop", "learning"]):
            return "Workshop"
        if "festival" in joined:
            return "Festival"

        return "Other"

    def parse_cards(page_soup, page_url):
        page_events = []

        cards = page_soup.select("article.card")

        if not cards:
            cards = page_soup.find_all(
                "article",
                attrs={"data-related": "shows"},
            )

        for card in cards:
            heading = card.select_one("h3.card__heading")
            link = card.select_one("a.card__link[href]")

            if not heading or not link:
                continue

            title = " ".join(heading.stripped_strings).strip()
            href = normalise_url(link.get("href"), page_url)

            if not title or not href or "/whats-on/" not in href.lower():
                continue

            # Gift vouchers are products, not events.
            if "gift voucher" in title.lower():
                continue

            times = card.find_all("time")

            if not times:
                continue

            start_date = afc_datetime(
                times[0].get("datetime")
                or times[0].get_text(" ", strip=True)
            )

            if not start_date:
                continue

            end_date = ""

            if len(times) > 1:
                end_date = afc_datetime(
                    times[-1].get("datetime")
                    or times[-1].get_text(" ", strip=True)
                )
                if end_date == start_date:
                    end_date = ""

            venue = ""
            for paragraph in card.find_all("p"):
                candidate = " ".join(paragraph.stripped_strings).strip()
                if candidate:
                    venue = candidate

            if not venue:
                venue = "Adelaide Festival Centre"

            page_events.append(
                {
                    "title": title,
                    "venue": venue,
                    "date": start_date,
                    "end_date": end_date,
                    "category": afc_category(card),
                    "image": afc_image(card, page_url),
                    "url": href,
                }
            )

        return page_events

    def add_page(page_events):
        added = 0

        for event in page_events:
            key = event["url"].lower()

            if key in seen_urls:
                continue

            seen_urls.add(key)
            events.append(event)
            added += 1

        return added

    # Fetch page 1 with the same session used for paginated pages.
    # AFC can return different first-page markup to the initial caller.
    try:
        first_response = session.get(source_url, timeout=30)
        first_response.raise_for_status()
        first_soup = BeautifulSoup(first_response.text, "lxml")
    except Exception:
        # Fall back to the soup supplied by scrape.py if the fresh request fails.
        first_soup = soup

    first_page_events = parse_cards(first_soup, source_url)

    first_signature = tuple(
        sorted(event["url"].lower() for event in first_page_events)
    )

    if first_signature:
        seen_page_signatures.add(first_signature)

    added = add_page(first_page_events)

    print(
        f"    AFC page 1: "
        f"{len(first_page_events)} found, "
        f"{added} new"
    )

    for page_number in range(2, 51):
        page_url = f"{source_url.rstrip('/')}/p{page_number}"

        try:
            response = session.get(page_url, timeout=30)
            response.raise_for_status()
            page_soup = BeautifulSoup(response.text, "lxml")

        except Exception as exc:
            print(
                f"    AFC page {page_number}: "
                f"ERROR {exc}"
            )
            break

        page_events = parse_cards(page_soup, page_url)

        if not page_events:
            print(
                f"    AFC page {page_number}: "
                f"0 events - stopping"
            )
            break

        signature = tuple(
            sorted(event["url"].lower() for event in page_events)
        )

        if signature in seen_page_signatures:
            print(
                f"    AFC page {page_number}: "
                f"repeated page detected - stopping"
            )
            break

        seen_page_signatures.add(signature)

        added = add_page(page_events)

        print(
            f"    AFC page {page_number}: "
            f"{len(page_events)} found, "
            f"{added} new"
        )

        if added == 0:
            break

    print(
        f"\nTotal Adelaide Festival Centre "
        f"events collected: {len(events)}"
    )

    return events

