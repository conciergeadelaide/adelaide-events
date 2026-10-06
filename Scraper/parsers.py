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


def categorise_event(title, text=""):
    combined = f"{title} {text}".lower()
    categories = []

    def add(category):
        if category not in categories:
            categories.append(category)

    rules = [
        ("Sport", ["bbl", "wbbl", "sheffield shield", "odi", "cricket", "basketball", "36ers", "football", "afl", "soccer", "rugby", "wrestling", "darts", "tennis", "sport"]),
        ("Food & Beverage", ["food", "wine", "beer", "dining", "dinner", "lunch", "brunch", "tasting", "culinary", "restaurant", "chef", "beverage", "cocktail", "dumpling", "market"]),
        ("Expos", ["expo", "exhibition fair", "trade show", "trade fair"]),
        ("Talks & Conferences", ["conference", "convention", "seminar", "symposium", "keynote", "lecture", "talk", "speaker", "forum", "words", "writing"]),
        ("Community", ["community", "parade", "public rosary", "rosary for peace", "neighbourhood", "neighborhood", "community day", "civic celebration"]),
        ("Comedy", ["comedy", "comedian", "stand-up", "stand up"]),
        ("Family", ["kids", "children", "family", "families", "the wiggles", "disney", "dinosaur", "toddler", "cinderella", "green sheep", "dog man"]),
        ("Festival", ["festival", "fest"]),
        ("Workshop", ["workshop", "masterclass", "class", "puppet making", "creative writing"]),
        ("Theatre", ["theatre", "theater", "play", "musical", "opera", "ballet", "dance", "magic", "magician", "illusion", "illusionist", "circus", "acrobat", "acrobatic", "burlesque", "cabaret", "physical theatre"]),
        ("Music", ["concert", "music", "orchestra", "symphony", "choir", "band", "singer", "tour"]),
        ("Arts & Culture", ["art", "gallery", "museum", "exhibition", "cultural", "culture", "cinema", "guided tour"]),
    ]

    for category, keywords in rules:
        if any(keyword in combined for keyword in keywords):
            add(category)

    if not categories:
        add("Other")

    return categories


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
                    "category": categorise_event(title),
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
    """Parse Adelaide Oval What's On cards."""

    events = []
    seen_urls = set()
    today = datetime.now()

    def parse_card_datetime(value):
        if not value:
            return ""

        value = " ".join(str(value).replace("\xa0", " ").split())

        match = re.search(
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?"
            r",?\s*(\d{1,2})\s+"
            r"(January|February|March|April|May|June|July|August|September|October|November|December)"
            r"(?:,?\s+(20\d{2}))?"
            r"(?:,?\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)))?",
            value,
            re.I,
        )

        if not match:
            return ""

        day = int(match.group(1))
        month = MONTHS[match.group(2).lower()]
        explicit_year = match.group(3)
        time_text = (match.group(4) or "").replace(" ", "").lower()

        if explicit_year:
            year = int(explicit_year)
        else:
            year = today.year

            # Adelaide Oval's listing omits the year. It is an upcoming-events
            # page, so a month/day already passed this year belongs to next year.
            try:
                candidate = datetime(year, month, day)
                today_date = datetime(today.year, today.month, today.day)
                if candidate < today_date:
                    year += 1
            except ValueError:
                return ""

        hour = 0
        minute = 0

        if time_text:
            for fmt in ("%I:%M%p", "%I%p"):
                try:
                    parsed_time = datetime.strptime(time_text, fmt)
                    hour = parsed_time.hour
                    minute = parsed_time.minute
                    break
                except ValueError:
                    continue

        try:
            return datetime(
                year,
                month,
                day,
                hour,
                minute,
            ).isoformat()
        except ValueError:
            return ""

    def parse_short_card_date(element, start_datetime):
        if not element or not start_datetime:
            return ""

        text = " ".join(element.stripped_strings).strip()

        match = re.search(
            r"\b(\d{1,2})\s+"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b",
            text,
            re.I,
        )

        if not match:
            return ""

        short_months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4,
            "may": 5, "jun": 6, "jul": 7, "aug": 8,
            "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
        }

        start = datetime.fromisoformat(start_datetime)
        day = int(match.group(1))
        month = short_months[match.group(2).lower()]
        year = start.year

        # A range may cross New Year.
        if (month, day) < (start.month, start.day):
            year += 1

        try:
            return datetime(year, month, day, 23, 59, 59).isoformat()
        except ValueError:
            return ""

    for link in soup.find_all("a", href=True):
        href = normalise_url(link.get("href"), source_url)

        if not href or "/events/" not in href.lower():
            continue

        clean_href = href.split("#", 1)[0].split("?", 1)[0]

        if clean_href.lower() in seen_urls:
            continue

        title_element = link.select_one("h5.card-title")
        date_element = link.select_one(
            'strong.card-meta[itemprop="startDate"]'
        )

        if not title_element or not date_element:
            continue

        title = " ".join(title_element.stripped_strings).strip()
        date_text = (
            date_element.get("content")
            or date_element.get_text(" ", strip=True)
        )
        date = parse_card_datetime(date_text)

        if not title or not date:
            continue

        end_date = ""
        end_element = link.select_one(".multiday-end-date-card")

        if end_element:
            end_date = parse_short_card_date(end_element, date)

            # Do not create an end date when the card's "end" value is not
            # actually later than the start date.
            if end_date:
                try:
                    if datetime.fromisoformat(end_date).date() <= datetime.fromisoformat(date).date():
                        end_date = ""
                except ValueError:
                    end_date = ""

        image = ""
        image_element = link.select_one(".card-image")

        if image_element:
            style = str(image_element.get("style", ""))
            image_match = re.search(
                r"background-image\s*:\s*url\(['\"]?([^'\")]+)",
                style,
                re.I,
            )
            if image_match:
                image = normalise_url(
                    image_match.group(1).strip(),
                    source_url,
                )

        lower_title = title.lower()

        sport_keywords = [
            "bbl",
            "wbbl",
            "sheffield shield",
            "odi",
            "test",
            "cricket",
            "strikers",
            "football",
            "afl",
            "soccer",
            "rugby",
        ]

        category = (
            ["Sport"]
            if any(keyword in lower_title for keyword in sport_keywords)
            else ["Music"]
        )

        seen_urls.add(clean_href.lower())

        events.append(
            {
                "title": title,
                "venue": "Adelaide Oval",
                "date": date,
                "end_date": end_date,
                "category": category,
                "image": image,
                "url": clean_href,
            }
        )

    print(
        f"\nTotal Adelaide Oval events collected: "
        f"{len(events)}"
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

        # ACC category rules.
        # Keep known current events deterministic, then use the normal
        # title-based category helper for future events.
        lower_title = title.lower()

        if "michelin guide restaurant ceremony" in lower_title:
            category = ["Food & Beverage"]
        elif "starlit christmas" in lower_title:
            category = ["Food & Beverage"]
        elif "phil hoffmann travel expo" in lower_title:
            category = ["Expos"]
        elif "interstellar live" in lower_title:
            category = ["Music"]
        else:
            category = categorise_event(title)

        events.append({
            "title": title,
            "venue": "Adelaide Convention Centre",
            "date": date,
            "end_date": end_date,
            "category": category,
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

    def afc_category(card, title=""):
        labels = []

        for element in card.find_all(attrs={"aria-label": True}):
            label = " ".join(str(element.get("aria-label", "")).split()).strip()
            if label:
                labels.append(label)

        joined = f"{title} {' '.join(labels)}".lower()
        categories = []

        def add(category):
            if category not in categories:
                categories.append(category)

        rules = [
            ("Theatre", ["theatre", "opera", "ballet", "dance", "cabaret", "magic", "magician", "illusion", "illusionist", "circus", "acrobat", "acrobatic", "burlesque", "physical theatre", "musical", "play"]),
            ("Music", ["music", "concert", "orchestra", "choir"]),
            ("Comedy", ["comedy"]),
            ("Family", ["kids", "families", "family", "children", "dinosaur", "toddler", "cinderella", "green sheep", "dog man"]),
            ("Workshop", ["workshop", "learning", "creative writing", "puppet making"]),
            ("Festival", ["festival"]),
            ("Food & Beverage", ["food", "dumpling", "market", "dining", "restaurant"]),
            ("Talks & Conferences", ["talk", "speaker", "lecture", "words", "writing", "conversation", "an evening with"]),
            ("Arts & Culture", ["art", "cinema", "cultural", "culture", "guided tour", "gallery", "museum"]),
        ]

        for category, keywords in rules:
            if any(keyword in joined for keyword in keywords):
                add(category)

        lower_title = title.lower()

        if "moon lanterns" in lower_title:
            add("Family")
            add("Festival")
            add("Arts & Culture")

        if "lucky dumpling market" in lower_title:
            add("Family")
            add("Festival")
            add("Food & Beverage")

        if "weekend of words" in lower_title:
            add("Festival")
            add("Talks & Conferences")

        if "dog man the musical" in lower_title:
            add("Theatre")
            add("Family")

        if "the nutcracker" in lower_title or "storytime ballet" in lower_title:
            add("Theatre")
            add("Family")

        if title.strip().lower() == "cinderella":
            add("Theatre")
            add("Family")

        if "her majesty's theatre guided tour" in lower_title:
            categories = ["Arts & Culture"]

        # These are theatrical productions. Do not add Music merely
        # because the title/labels contain "musical", "choir", etc.
        if "dog man the musical" in lower_title:
            categories = ["Theatre", "Family"]

        if "the heartbreak choir" in lower_title:
            categories = ["Theatre"]

        if "the book of mormon" in lower_title:
            categories = ["Theatre"]

        if not categories:
            add("Other")

        return categories


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
                    "category": afc_category(card, title),
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



# ============================================================
# ADELAIDE ENTERTAINMENT CENTRE
# ============================================================

def parse_adelaide_entertainment_centre(soup, source_url):
    """Parse active Adelaide Entertainment Centre event pages."""

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0.0.0 Safari/537.36"
        )
    })

    def clean_text(value):
        return " ".join(str(value or "").replace("\xa0", " ").split())

    def parse_event_datetime(day, month, year, time_text=""):
        value = f"{day} {month} {year}"
        time_text = clean_text(time_text)
        if time_text:
            value += f" {time_text}"
            formats = [
                "%d %B %Y %I:%M%p", "%d %B %Y %I%p",
                "%d %b %Y %I:%M%p", "%d %b %Y %I%p",
            ]
        else:
            formats = ["%d %B %Y", "%d %b %Y"]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt).isoformat()
            except ValueError:
                pass
        return ""

    def find_when_block(event_soup):
        when_text = event_soup.find(
            string=lambda value: value and clean_text(value).lower() == "when"
        )
        if not when_text or not when_text.parent or not when_text.parent.parent:
            return None
        return when_text.parent.parent

    def authoritative_date(event_soup):
        container = find_when_block(event_soup)
        if not container:
            return None

        date_element = container.find(
            class_=lambda value: value and "content-block--event-date" in (
                " ".join(value) if isinstance(value, list) else value
            )
        )
        if not date_element:
            return None

        date_text = clean_text(date_element.get_text(" ", strip=True))
        match = re.search(
            r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+"
            r"(\d{1,2})\s+"
            r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+"
            r"(\d{4})",
            date_text,
            re.I,
        )
        if not match:
            return None

        lower = date_text.lower()
        if "theatre" in lower:
            venue = "Adelaide Entertainment Centre Theatre"
        elif "arena" in lower:
            venue = "Adelaide Entertainment Centre Arena"
        else:
            venue = "Adelaide Entertainment Centre"

        return {
            "day": match.group(1),
            "month": match.group(2),
            "year": match.group(3),
            "venue": "Adelaide Entertainment Centre",
            "container": container,
        }

    def header_time(event_soup):
        text = clean_text(event_soup.get_text(" ", strip=True))
        patterns = [
            r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*[–—-]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
            r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}\s*[|–—-]\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return clean_text(match.group(1))
        return ""

    def labelled_start_time(container):
        if not container:
            return ""
        labels = [
            "match start", "show start", "show starts", "performance start",
            "performance starts", "event start", "event starts",
            "concert start", "concert starts",
        ]
        for paragraph in container.find_all("p"):
            text = clean_text(paragraph.get_text(" ", strip=True))
            for label in labels:
                match = re.search(
                    r"(\d{1,2}(?::\d{2})?\s*(?:am|pm))\s*[–—-]\s*" + re.escape(label),
                    text,
                    re.I,
                )
                if match:
                    return clean_text(match.group(1))
        return ""

    def event_image(event_soup, event_url):
        for element in event_soup.find_all(attrs={"data-background-image": True}):
            candidate = str(element.get("data-background-image", "")).strip()
            lower = candidate.lower()
            if not candidate:
                continue
            if any(word in lower for word in [
                "getting-here", "eat-and-drink", "accessibility", "faq", "logo", "icon"
            ]):
                continue
            return normalise_url(candidate, event_url)
        return ""

    def category_for(title):
        lower = title.lower()
        categories = []

        def add(category):
            if category not in categories:
                categories.append(category)

        if "david the medium" in lower:
            add("Other")

        if any(word in lower for word in ["36ers", "basketball", "darts", "wrestling", "mega mania"]):
            add("Sport")

        if any(word in lower for word in ["wiggles", "disney", "family"]):
            add("Family")

        if any(word in lower for word in [
            "comedy", "comedian", "gabriel iglesias", "paul smith",
            "aaron chen", "morgan jay"
        ]):
            add("Comedy")

        if any(word in lower for word in [
            "magic", "magician", "illusion", "illusionist",
            "circus", "acrobat", "acrobatic", "burlesque",
            "cabaret", "physical theatre"
        ]):
            add("Theatre")

        if not categories:
            add("Music")

        return categories


    event_urls = []
    seen_urls = set()
    base_url = source_url.rstrip("/").lower()

    for link in soup.find_all("a", href=True):
        href = normalise_url(link.get("href"), source_url)
        clean_href = href.split("#", 1)[0].split("?", 1)[0].rstrip("/")
        lower_href = clean_href.lower()
        if "adelaideentertainmentcentre.com.au/events/" not in lower_href:
            continue
        if lower_href == base_url:
            continue
        if lower_href in seen_urls:
            continue
        seen_urls.add(lower_href)
        event_urls.append(clean_href + "/")

    events = []

    for event_url in event_urls:
        try:
            response = session.get(event_url, timeout=30)
            response.raise_for_status()
            event_soup = BeautifulSoup(response.text, "lxml")
        except Exception as exc:
            print(f"    AEC event page ERROR: {event_url} -> {exc}")
            continue

        heading = event_soup.find("h1")
        title = clean_text(heading.get_text(" ", strip=True)) if heading else ""
        if not title:
            continue
        if "cancelled" in title.lower() or "canceled" in title.lower():
            continue

        auth = authoritative_date(event_soup)
        if not auth:
            continue

        time_text = labelled_start_time(auth["container"]) or header_time(event_soup)
        date = parse_event_datetime(auth["day"], auth["month"], auth["year"], time_text)
        if not date:
            continue

        events.append({
            "title": title,
            "venue": auth["venue"],
            "date": date,
            "end_date": "",
            "category": category_for(title),
            "image": event_image(event_soup, event_url),
            "url": event_url,
        })

    print(f"\nTotal Adelaide Entertainment Centre events collected: {len(events)}")
    return events
