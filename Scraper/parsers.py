import json
import re
from datetime import datetime, timedelta
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

            # Adelaide Oval often omits the year. A recently started event
            # can remain listed for days after its start, so do NOT move it
            # into next year merely because its date was a few days ago.
            # Dates much further in the past are treated as next-year listings.
            # This is an inference; explicit years always take precedence.
            try:
                candidate = datetime(year, month, day)
                today_date = datetime(today.year, today.month, today.day)
                if candidate < today_date - timedelta(days=45):
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
# HINDLEY STREET MUSIC HALL
# ============================================================

def parse_hindley_st_music_hall(soup, source_url):
    """Collect the official Hindley Street Music Hall event calendar.

    The homepage only contains featured events. The venue's search API
    provides the complete calendar when culture and venue ID are supplied.
    Fail rather than returning a partial list, so scrape.py can preserve
    existing records instead of replacing them with incomplete data.
    """
    api_url = "https://www.hindleymusichall.com.au/__api/search/events"
    venue_id = "1368725"
    page_size = 100
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
        "Referer": "https://www.hindleymusichall.com.au/whats-on",
        "Accept": "application/json",
    })

    events = []
    seen = set()
    total = None
    image_cache = {}

    def image_is_available(candidate):
        """Check the response is an image, not an error page."""
        if not candidate or not candidate.startswith(("https://", "http://")):
            return False
        if candidate in image_cache:
            return image_cache[candidate]
        try:
            with session.get(
                candidate,
                timeout=10,
                stream=True,
                headers={"Accept": "image/avif,image/webp,image/*,*/*;q=0.8"},
            ) as result:
                content_type = result.headers.get("Content-Type", "").lower()
                valid = result.status_code == 200 and content_type.startswith("image/")
        except requests.RequestException:
            valid = False
        image_cache[candidate] = valid
        return valid

    def find_event_page_image(event_url, title):
        """Prefer the image whose alt text names this specific event.

        Do not fall back to site branding, logos or unrelated event artwork.
        Full-width artwork is often usable when thumbnail variants are not.
        """
        try:
            page_response = session.get(event_url, timeout=12)
            page_response.raise_for_status()
            page_soup = BeautifulSoup(page_response.text, "lxml")
        except requests.RequestException:
            return ""

        def words(value):
            return set(re.findall(r"[a-z0-9]+", str(value).lower())) - {
                "the", "and", "with", "live", "tour", "at", "in", "on", "of",
                "a", "an", "to", "ft", "featuring",
            }

        title_words = words(title)
        candidates = []
        for tag in page_soup.find_all("img"):
            alt_words = words(tag.get("alt", ""))
            if not title_words or not alt_words:
                continue
            # Strong name overlap guards against unrelated promotional artwork.
            if len(title_words & alt_words) < min(2, len(title_words)):
                continue
            for key in ("src", "data-src", "data-lazy-src"):
                if tag.get(key):
                    candidates.append(normalise_url(tag[key], event_url))

        for candidate in candidates:
            lower = candidate.lower()
            if any(word in lower for word in (
                "favicon", "logo", "brandmark", "icon", "placeholder",
            )):
                continue
            # Preserve the event page's full-size image URL. Some CDN
            # variants cannot be verified reliably by Python requests even
            # though they load in a browser.
            return candidate
        return ""

    for page in range(1, 21):
        params = {
            "culture": "en-AU",
            "VenueIds": venue_id,
            "PageSize": page_size,
            "Page": page,
        }
        response = session.get(api_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data.get("hasError"):
            raise RuntimeError("Hindley calendar API reported an error")

        documents = data.get("documents")
        if not isinstance(documents, list):
            raise ValueError("Hindley calendar API returned no documents list")
        if total is None:
            total = int(data.get("total", 0))
            if total == 0:
                raise ValueError("Hindley calendar API reported zero events")

        for item in documents:
            if not isinstance(item, dict):
                continue
            venue = item.get("venue") or {}
            if str(venue.get("id", "")) != venue_id:
                continue

            title = " ".join(str(item.get("name") or "").split())
            raw_date = str(item.get("eventDate") or "")
            date_part = raw_date[:10]
            if not title or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", date_part):
                continue
            try:
                datetime.strptime(date_part, "%Y-%m-%d")
            except ValueError:
                continue

            # eventDate is the local calendar date. Do not convert the UTC
            # timestamp, which could shift an Adelaide event to another day.
            time_text = str(item.get("showTime") or "").strip()
            time_match = re.fullmatch(r"(\d{1,2}):(\d{2})", time_text)
            if time_match and int(time_match.group(1)) < 24 and int(time_match.group(2)) < 60:
                clock = f"{int(time_match.group(1)):02d}:{time_match.group(2)}:00"
            else:
                clock = "00:00:00"
            date = f"{date_part}T{clock}"

            raw_end = str(item.get("eventDateTo") or "")[:10]
            end_date = ""
            if re.fullmatch(r"20\d{2}-\d{2}-\d{2}", raw_end) and raw_end > date_part:
                end_date = f"{raw_end}T23:59:59"

            event_url = normalise_url(item.get("url"), source_url)
            if not event_url:
                continue
            image = normalise_url(item.get("image"), source_url)
            # The event page often has a full-size poster with the event's
            # title as alt text. Prefer it to broken API thumbnails.
            alternate = find_event_page_image(event_url, title)
            if alternate:
                if alternate != image:
                    print(f"    Using event artwork: {title}")
                image = alternate
            elif any(word in image.lower() for word in (
                "favicon", "logo", "brandmark", "icon", "placeholder",
            )) or not image_is_available(image):
                print(f"    No verified event artwork: {title}")
                image = ""
            key = (str(item.get("id") or ""), date_part)
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "title": title,
                "venue": "Hindley Street Music Hall",
                "date": date,
                "end_date": end_date,
                "category": ["Music"],
                "image": image,
                "url": event_url,
            })

        print(f"    Hindley API page {page}: {len(documents)} returned")
        if len(events) >= total:
            break
        if not documents:
            break

    # Never silently replace the existing source with an incomplete response.
    if len(events) < total:
        raise RuntimeError(
            f"Hindley calendar incomplete: collected {len(events)} of {total} events"
        )

    print(f"\nTotal Hindley Street Music Hall events collected: {len(events)}")
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


# ============================================================
# COOPERS STADIUM
# ============================================================

def parse_coopers_stadium(soup, source_url):
    """Read Coopers Stadium's official events listing and event detail pages.

    Only accept dated links to individual events. If the site's layout changes,
    return no events so scrape.py preserves previously collected records.
    """
    from urllib.parse import urlparse

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"
        )
    })
    events = []
    seen = set()
    hostname = (urlparse(source_url).hostname or "").removeprefix("www.")
    date_pattern = re.compile(
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r"\s+(\d{1,2})\s+"
        r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
        r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
        r"\s+(20\d{2})", re.I
    )
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    time_pattern = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.I)

    def date_from_text(text):
        match = date_pattern.search(" ".join(text.split()))
        if not match:
            return ""
        day = int(match.group(1))
        month = months[match.group(2).lower()[:3]]
        year = int(match.group(3))
        tail = text[match.end():]
        time_match = time_pattern.search(tail)
        hour = minute = 0
        if time_match:
            hour = int(time_match.group(1)) % 12
            if time_match.group(3).lower() == "pm":
                hour += 12
            minute = int(time_match.group(2) or 0)
        try:
            return datetime(year, month, day, hour, minute).isoformat()
        except ValueError:
            return ""

    def find_image(page_soup, page_url):
        for element in page_soup.find_all(attrs={"data-background-image": True}):
            value = str(element.get("data-background-image", "")).strip()
            if value and not any(bad in value.lower() for bad in
                                 ("logo", "favicon", "icon", "getting-here")):
                return normalise_url(value, page_url)
        for prop in ("og:image", "twitter:image"):
            tag = page_soup.find("meta", attrs={"property": prop}) or page_soup.find(
                "meta", attrs={"name": prop}
            )
            if tag:
                value = str(tag.get("content", "")).strip()
                if value and not any(bad in value.lower() for bad in ("logo", "favicon")):
                    return normalise_url(value, page_url)
        return ""

    # Find the individual event links on the listing. Never use ticket links.
    for link in soup.find_all("a", href=True):
        url = normalise_url(link.get("href"), source_url)
        parsed = urlparse(url)
        if (parsed.hostname or "").removeprefix("www.") != hostname:
            continue
        path = parsed.path.rstrip("/")
        if not path.startswith("/events/") or path == "/events":
            continue
        url = f"{parsed.scheme}://{parsed.netloc}{path}/"
        if url.lower() in seen:
            continue

        # Listing cards include date, event title and a More info link.
        # Walk only nearby ancestors to avoid picking another event's date.
        card_date = ""
        card_title = ""
        node = link
        for _ in range(5):
            node = node.parent
            if node is None or node.name in ("body", "html"):
                break
            text = node.get_text(" ", strip=True)
            if len(text) > 1200:
                break
            candidate = date_from_text(text)
            if candidate:
                card_date = candidate
                heading = node.find(["h2", "h3", "h4", "h5", "h6"])
                if heading:
                    card_title = heading.get_text(" ", strip=True)
                break

        # Individual event pages give the definitive title and artwork.
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, "lxml")
        except requests.RequestException as exc:
            print(f"    Coopers event page ERROR: {url} -> {exc}")
            continue

        heading = detail.find("h1")
        title = heading.get_text(" ", strip=True) if heading else card_title
        if not title or "cancelled" in title.lower() or "canceled" in title.lower():
            continue

        date = card_date
        if not date:
            # The date must be on the detail page if listing markup changes.
            for element in detail.find_all(["time", "p", "div", "span"], limit=150):
                candidate_text = element.get_text(" ", strip=True)
                if len(candidate_text) > 250:
                    continue
                date = date_from_text(candidate_text)
                if date:
                    break
        if not date:
            continue

        lower_title = title.lower()
        sport_terms = (
            "adelaide united", "football", "soccer", "fc ", " fc",
            "champions league", "a-league", "aleague", "matildas",
        )
        category = ["Sport"] if any(term in lower_title for term in sport_terms) else ["Music"]
        venue = "Coopers Stadium"
        if "hindmarsh stadium" in detail.get_text(" ", strip=True).lower():
            # Hindmarsh Stadium is another name for the same ground;
            # use one consistent venue label to prevent duplicates.
            venue = "Coopers Stadium"

        events.append({
            "title": title,
            "venue": venue,
            "date": date,
            "end_date": "",
            "category": category,
            "image": find_image(detail, url),
            "url": url,
        })
        seen.add(url.lower())

    print(f"\nTotal Coopers Stadium events collected: {len(events)}")
    return events


# ============================================================
# IMMERSIVE LIGHT AND ART (ILA)
# ============================================================

def parse_immersive_light_and_art(soup, source_url):
    """Read ILA What's On cards and individual event pages."""
    from urllib.parse import urlparse
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    now = datetime.now()
    month_map = {k[:3]: v for k, v in MONTHS.items()}
    month_map['sep'] = 9
    month_pattern = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'

    def parse_range(text):
        text = ' '.join(str(text or '').replace('\xa0', ' ').replace('–', '-').replace('—', '-').split())
        # Prefer a full, explicit year on detail pages.
        m = re.search(r'\b(\d{1,2})\s+(' + month_pattern + r')\s*-\s*(\d{1,2})\s+(' + month_pattern + r')\s+(20\d{2})\b', text, re.I)
        if m:
            d1, mo1, d2, mo2, year = m.groups()
            try:
                a = datetime(int(year), month_map[mo1[:3].lower()], int(d1))
                b = datetime(int(year), month_map[mo2[:3].lower()], int(d2), 23, 59, 59)
                if b < a: b = b.replace(year=b.year+1)
                return a.isoformat(), b.isoformat()
            except ValueError: pass
        m = re.search(r'\b(\d{1,2})\s*-\s*(\d{1,2})\s+(' + month_pattern + r')(?:\s+(20\d{2}))?\b', text, re.I)
        if m:
            d1, d2, mo, year = m.groups()
            try:
                y = int(year) if year else now.year
                a = datetime(y, month_map[mo[:3].lower()], int(d1))
                if not year and a.date() < now.date(): a = a.replace(year=y+1)
                b = a.replace(day=int(d2), hour=23, minute=59, second=59)
                if b >= a: return a.isoformat(), b.isoformat()
            except ValueError: pass
        m = re.search(r'\b(\d{1,2})\s+(' + month_pattern + r')\s*-\s*(\d{1,2})\s+(' + month_pattern + r')(?:\s+(20\d{2}))?\b', text, re.I)
        if m:
            d1, mo1, d2, mo2, year = m.groups()
            try:
                y = int(year) if year else now.year
                a = datetime(y, month_map[mo1[:3].lower()], int(d1))
                if not year and a.date() < now.date(): a = a.replace(year=y+1)
                b = datetime(a.year, month_map[mo2[:3].lower()], int(d2), 23, 59, 59)
                if b < a: b = b.replace(year=b.year+1)
                return a.isoformat(), b.isoformat()
            except ValueError: pass
        m = re.search(r'\b(?:from\s+)?(\d{1,2})\s+(' + month_pattern + r')(?:\s+(20\d{2}))?\b', text, re.I)
        if m:
            day, mo, year = m.groups()
            try:
                y = int(year) if year else now.year
                a = datetime(y, month_map[mo[:3].lower()], int(day))
                if not year and a.date() < now.date(): a = a.replace(year=y+1)
                return a.isoformat(), ''
            except ValueError: pass
        return '', ''

    def image_from_page(page, page_url):
        # Social metadata is normally the event's hero artwork.
        for key in ('og:image', 'twitter:image'):
            tag = page.find('meta', attrs={'property': key}) or page.find('meta', attrs={'name': key})
            if tag:
                url = normalise_url(tag.get('content', ''), page_url)
                if url and not any(x in url.lower() for x in ('logo', 'favicon', 'placeholder')):
                    return url
        for img in page.find_all('img', limit=15):
            url = img.get('data-src') or img.get('src') or ''
            if url and not url.startswith('data:') and not any(x in url.lower() for x in ('logo', 'favicon', 'icon')):
                return normalise_url(url, page_url)
        return ''

    events, seen = [], set()
    host = urlparse(source_url).hostname or ''
    for link in soup.find_all('a', href=True):
        url = normalise_url(link.get('href'), source_url).split('#')[0].split('?')[0]
        parsed = urlparse(url)
        if parsed.hostname != host or not parsed.path.startswith('/event/') or parsed.path.rstrip('/') == '/event':
            continue
        url = url.rstrip('/') + '/'
        if url in seen: continue
        seen.add(url)
        # Prefer date text from the detail page, not unrelated recommendations.
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
            page = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as exc:
            print(f'    ILA event page ERROR: {url} -> {exc}')
            continue
        heading = page.find('h1')
        title = heading.get_text(' ', strip=True) if heading else link.get_text(' ', strip=True)
        if not title: continue
        start, end = '', ''
        # Search short date-related elements first, to avoid footer and related events.
        for node in page.find_all(['h2','h3','h4','p','time','li','span'], limit=220):
            t = node.get_text(' ', strip=True)
            if not t or len(t) > 140: continue
            a, b = parse_range(t)
            if a:
                start, end = a, b
                if re.search(r'20\d{2}', t): break
        if not start:
            # Listing card may contain the date when detail markup changes.
            parent = link
            for _ in range(5):
                parent = parent.parent
                if not parent or parent.name in ('body','html'): break
                t = parent.get_text(' ', strip=True)
                if len(t) > 450: break
                start, end = parse_range(t)
                if start: break
        if not start:
            print(f'    ILA skipped (no date): {title}')
            continue
        lower = title.lower()
        if any(k in lower for k in ('lunch','dining','soil','table','food','wine')):
            category = ['Food & Beverage']
        elif any(k in lower for k in ('exhibition','architecture','andrew hill','thin ice','art')):
            category = ['Arts & Culture']
        elif any(k in lower for k in ('live','concert','music','grigoryan')):
            category = ['Music']
        else:
            category = categorise_event(title)
        events.append({'title': title, 'venue': 'Immersive Light and Art (ILA)',
                       'date': start, 'end_date': end, 'category': category,
                       'image': image_from_page(page, url), 'url': url})
    print(f'\nTotal Immersive Light and Art events collected: {len(events)}')
    return events


# ============================================================
# ADELAIDE TOWN HALL
# ============================================================

def parse_adelaide_town_hall(soup, source_url):
    """Read Town Hall event details, avoiding related-event dates/images."""
    from urllib.parse import urlparse

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"
    })
    host = urlparse(source_url).hostname
    urls = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        url = normalise_url(anchor.get("href", ""), source_url)
        parsed = urlparse(url)
        if parsed.hostname != host or not parsed.path.startswith("/events/"):
            continue
        url = url.split("#", 1)[0].split("?", 1)[0].rstrip("/") + "/"
        if url not in seen:
            seen.add(url)
            urls.append(url)

    events = []
    for url in urls:
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            page = BeautifulSoup(response.text, "lxml")
        except requests.RequestException as exc:
            print(f"    Town Hall detail ERROR: {url} -> {exc}")
            continue

        page_title = page.title.get_text(" ", strip=True) if page.title else ""
        title = re.split(r"\s*[|]\s*Adelaide Town Hall\s*$", page_title, flags=re.I)[0].strip()
        if not title or title == page_title == "What's on":
            print(f"    Town Hall skipped (no title): {url}")
            continue

        # Navigation also contains "Plan your visit", so splitting the whole
        # document at that phrase would remove the event before its date.
        # Instead, isolate the event details around its "When" field.
        content = page.get_text(" ", strip=True)
        when_match = re.search(r"\bWhen\s+", content, flags=re.I)
        event_details = content[when_match.end():when_match.end() + 500] if when_match else ""
        date_match = re.search(
            r"Next\s+occurrence\s+is\s+(\d{1,2}\s+[A-Za-z]+\s+20\d{2})",
            event_details, flags=re.I
        )
        date = parse_date_text(date_match.group(1)) if date_match else ""
        if not date:
            # Some events have a date range or a single dated "When" value.
            # Only inspect the event's When field, not recommended events.
            date = parse_date_text(event_details.split("Accessibility", 1)[0])
        if not date:
            print(f"    Town Hall skipped (no confirmed year/date): {title}")
            continue

        # For category detection, inspect the section around the event title,
        # rather than the navigation menu.
        title_position = content.find(title)
        main_text = content[title_position:title_position + 1800] if title_position >= 0 else content[:1800]

        # First ATDW image on the event detail is the event hero;
        # subsequent ATDW images can be unrelated suggested events.
        image = ""
        for img in page.find_all("img"):
            candidate = img.get("src") or img.get("data-src") or ""
            if "assets.atdw-online.com.au/images/" in candidate:
                image = normalise_url(candidate, url)
                break

        # Explicit Town Hall classifications override generic title heuristics.
        # Keep these as single-category lists so broad keyword matches cannot
        # incorrectly add Theatre, Talks, or other categories.
        title_key = re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip()
        town_hall_music_titles = (
            "paul lewis mozart",
            "encore classics",
            "bach s st john passion",
            "alina ibragimova plays tchaikovsky",
            "the choir of king s college cambridge and william barton",
            "aco in motion",
            "the john adams almanac",
        )
        if "daryl austin the long view" in title_key:
            category = ["Arts & Culture"]
        elif any(key in title_key for key in town_hall_music_titles):
            category = ["Music"]
        else:
            category = None

        category_text = main_text.split(title, 1)[0][-180:] if title in main_text else ""
        lower = category_text.lower()
        if category is None:
            if "music" in lower or "concert" in lower:
                category = ["Music"]
            elif "exhibition" in lower or "art" in lower:
                category = ["Arts & Culture"]
            elif "tour" in lower:
                category = ["Arts & Culture"]
            elif "workshop" in lower:
                category = ["Workshop"]
            else:
                category = categorise_event(title)

        events.append({
            "title": title,
            "venue": "Adelaide Town Hall",
            "date": date,
            "end_date": "",
            "category": category,
            "image": image,
            "url": url,
        })

    print(f"\nTotal Adelaide Town Hall events collected: {len(events)}")
    return events

# ============================================================
# LION ARTS FACTORY
# ============================================================

def parse_lion_arts_factory(soup, source_url):
    """Parse Lion Arts Factory's full What's On listing.

    The site provides gig cards directly, with a dated heading, a
    lazy-loaded Moshtix poster and a ticket link. No detail requests
    or year guessing are needed.
    """
    events = []
    seen = set()
    cards = soup.select(".gig_inner")

    if not cards:
        raise RuntimeError("Lion Arts Factory: no gig cards found; page layout may have changed")

    for card in cards:
        title_element = card.select_one(".gig_heading")
        date_element = card.select_one(".gig_date")
        if not title_element or not date_element:
            continue

        title = title_element.get_text(" ", strip=True)
        date_text = date_element.get_text(" ", strip=True)
        date = ""
        for fmt in ("%A %d %b %Y", "%a %d %b %Y", "%A %d %B %Y"):
            try:
                date = datetime.strptime(date_text, fmt).strftime("%Y-%m-%dT00:00:00")
                break
            except ValueError:
                pass

        if not title or not date:
            print(f"    Lion Arts skipped (missing title/date): {title or date_text}")
            continue

        image_element = card.select_one(".gig_image_container img")
        image = ""
        if image_element:
            image_src = (
                image_element.get("data-src")
                or image_element.get("data-lazy-src")
                or image_element.get("src")
                or ""
            )
            if image_src and not image_src.startswith("data:"):
                image = normalise_url(image_src, source_url)

        ticket = card.select_one("a.gig_button[href]")
        if not ticket:
            ticket = card.select_one('a[href*="moshtix.com.au"]')
        link = normalise_url(ticket.get("href"), source_url) if ticket else source_url

        key = (title.casefold(), date[:10])
        if key in seen:
            continue
        seen.add(key)

        # Lucha Fantastica is a wrestling performance, not a music gig.
        lower_title = title.casefold()
        if "lucha fantastica" in lower_title:
            category = ["Sport", "Family"] if "family show" in lower_title else ["Sport"]
        else:
            category = ["Music"]

        events.append({
            "title": title,
            "venue": "Lion Arts Factory",
            "date": date,
            "end_date": "",
            "category": category,
            "image": image,
            "url": link,
        })

    # Avoid silently accepting a broken partial listing if the page
    # contains many cards but most dates fail to parse.
    if len(events) < max(1, int(len(cards) * 0.8)):
        raise RuntimeError(
            f"Lion Arts Factory: parsed only {len(events)} of {len(cards)} cards; "
            "preserving existing records"
        )

    print(f"\nTotal Lion Arts Factory events collected: {len(events)}")
    return events


# Tourism-specific classification. Avoid the broad generic substring rules
# (e.g. "play" inside "playgroup" and "family" inside a wine producer name).
def categorise_tourism_event(title):
    name = " ".join(str(title).casefold().split())
    # Distinctive programme names are intentionally explicit. For unfamiliar
    # listings, the conservative fallback below avoids invented categories.
    exact = {
        "adelaide film festival": ["Film", "Festival"],
        "australian geographic nature photographer of the year": ["Exhibitions"],
        "calm seas – sanctuary series": ["Music"],
        "cheesefest 2026": ["Food & Beverage", "Festival"],
        "cipx kaurna miyurna (critical indigenous photographic exchange with the kaurna community)": ["Exhibitions", "First Nations"],
        "clos saint jean wine dinner": ["Food & Beverage"],
        "dirty dancing in concert - adelaide": ["Music", "Film"],
        "glam, gin & drag bingo at prohibition liquor co.": ["Club/Party", "Food & Beverage"],
        "endless sky – cathedral series": ["Music"],
        "exhibition: beginnings": ["Exhibitions"],
        "festival of halloween": ["Festival", "Family"],
        "fischer-z - adelaide": ["Music"],
        "gabriel iglesias": ["Comedy"],
        "grace": ["Music"],
        "inferno": ["Theatre"],
        "hoffmann family vineyards masterclass at bar septimus": ["Food & Beverage", "Conferences/Workshops/Expos"],
        "intergenerational playgroup, the learning tree": ["Community", "Family"],
        "ray white semaphore street fair": ["Community", "Festival"],
        "meet the maker: 10th anniversary botanic rosé": ["Food & Beverage"],
        "michelle nikou: tell it slant": ["Exhibitions"],
        "mindful clay, pottery wheel, hand building & colors": ["Conferences/Workshops/Expos"],
        "mmad wine dinner": ["Food & Beverage"],
        "monet to matisse: defying tradition": ["Exhibitions"],
        "monet to matisse friday nights: noriko tadano": ["Music", "Exhibitions"],
        "pattern and colour of the market": ["Exhibitions"],
        "raa bay to birdwood start": ["Community"],
        "rooftop raclette at merrymaker rooftop bar": ["Food & Beverage"],
        "bachata by the beach - latin dance party": ["Dance", "Club/Party"],
        "shannons adelaide rally": ["Sport"],
        "simply adelaide west coast swing": ["Dance"],
        "social clay session - pottery wheel": ["Conferences/Workshops/Expos"],
        "studio tours": ["Exhibitions"],
        "the mini-cine": ["Film"],
        "unwined uncovered": ["Food & Beverage"],
        "vinyl thursdays": ["Music", "Club/Party"],
    }
    if name in exact:
        return exact[name][:]
    if name.startswith("ozasia festival"):
        if "hong kong dragon" in name:
            return ["Festival", "Dance"]
        if "hyoshi in counterpoint" in name:
            return ["Festival", "Music"]
        if "jade ensemble" in name or "lastlings" in name or "regurgitator" in name:
            return ["Festival", "Music"]
        if "lucky dumpling market" in name:
            return ["Festival", "Food & Beverage"]
        if "maajela" in name:
            return ["Festival", "Dance"]
        return ["Festival"]

    categories = []
    def add(category):
        if category not in categories:
            categories.append(category)
    if re.search(r"\b(exhibition|gallery|photograph|museum)\b", name):
        add("Exhibitions")
    if re.search(r"\b(comedy|comedian|stand.up)\b", name):
        add("Comedy")
    if re.search(r"\b(concert|orchestra|symphony|live music|gig)\b", name):
        add("Music")
    if re.search(r"\b(dance|ballet|bachata|swing)\b", name):
        add("Dance")
    if re.search(r"\b(film|cinema|cine)\b", name):
        add("Film")
    if re.search(r"\b(wine|dinner|tasting|cocktail|food|raclette)\b", name):
        add("Food & Beverage")
    if re.search(r"\b(workshop|masterclass|pottery|clay session)\b", name):
        add("Conferences/Workshops/Expos")
    if re.search(r"\b(festival|fest)\b", name):
        add("Festival")
    return categories or ["Other"]


# ============================================================
# SOUTH AUSTRALIA TOURISM COMMISSION — ADELAIDE
# ============================================================

def parse_south_australia_tourism(soup, source_url):
    """Adelaide tourism listings only; fail safely if their layout changes.

    Regional festival exceptions are intentionally not automatically included:
    those require a curated list of approved festivals.
    """
    from urllib.parse import urlparse

    listing_url = "https://southaustralia.com/destinations/adelaide/what-s-on"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0.0.0 Safari/537.36"})
    response = session.get(listing_url, timeout=30)
    response.raise_for_status()
    listing = BeautifulSoup(response.text, "lxml")
    urls = set()
    for anchor in listing.find_all("a", href=True):
        link = normalise_url(anchor["href"], listing_url).split("#")[0].split("?")[0]
        parsed = urlparse(link)
        if parsed.hostname in ("southaustralia.com", "www.southaustralia.com") and re.fullmatch(r"/products/adelaide/event/[^/]+/?", parsed.path, re.I):
            urls.add(link.rstrip("/"))

    if not urls:
        raise RuntimeError("Tourism: no Adelaide event links found; preserving existing records")

    events = []
    failed = 0
    for url in sorted(urls):
        try:
            page_response = session.get(url, timeout=25)
            page_response.raise_for_status()
            page = BeautifulSoup(page_response.text, "lxml")
            blocks = []
            for tag in page.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(tag.string or tag.get_text())
                    if isinstance(data, dict):
                        blocks.extend(data.get("@graph", [data]))
                    elif isinstance(data, list):
                        blocks.extend(data)
                except (ValueError, TypeError):
                    continue

            event_data = next((x for x in blocks if isinstance(x, dict) and "Event" in ([x.get("@type")] if isinstance(x.get("@type"), str) else x.get("@type", []))), None)
            if not event_data:
                failed += 1
                continue
            title = str(event_data.get("name") or "").strip()
            raw_start = str(event_data.get("startDate") or "")
            if not title or not raw_start:
                failed += 1
                continue
            try:
                start = datetime.fromisoformat(raw_start.replace("Z", "+00:00")).replace(tzinfo=None).isoformat(timespec="seconds")
            except ValueError:
                failed += 1
                continue
            end = ""
            if event_data.get("endDate"):
                try:
                    end = datetime.fromisoformat(str(event_data["endDate"]).replace("Z", "+00:00")).replace(tzinfo=None).isoformat(timespec="seconds")
                except ValueError:
                    pass

            # Keep multi-day events while they are running; exclude only events
            # whose final calendar date is already in the past.
            if (end or start)[:10] < datetime.now().date().isoformat():
                continue

            # ATDW commonly places venue/address in a separate Organization block.
            locations = []
            direct_location = event_data.get("location")
            if isinstance(direct_location, dict):
                locations.append(direct_location)
            elif isinstance(direct_location, list):
                locations.extend(x for x in direct_location if isinstance(x, dict))
            for block in blocks:
                if isinstance(block, dict) and isinstance(block.get("location"), dict):
                    locations.append(block["location"])

            localities = []
            venue = ""
            for loc in locations:
                if not venue:
                    venue = str(loc.get("name") or "").strip()
                address = loc.get("address")
                if isinstance(address, dict):
                    locality = str(address.get("addressLocality") or "").strip()
                    if locality:
                        localities.append(locality)
            # The Adelaide listing can include outlying attractions. The
            # geographic test uses explicit known metro/nearby localities.
            permitted = {
                "adelaide", "north adelaide", "port adelaide", "glenelg", "glenelg south",
                "henley beach", "west beach", "brighton", "semaphore", "norwood",
                "unley", "prospect", "bowden", "hindmarsh", "thebarton", "mile end",
                "goodwood", "kent town", "stepney", "burnside", "magill", "modbury",
                "marion", "morphettville", "woodville", "findon", "fulham", "fulham gardens",
                "grange", "west lakes", "mawson lakes", "salisbury", "elizabeth",
                "tea tree gully", "belair", "blackwood", "bedford park", "oaklands park",
                "north terrace", "adelaide cbd", "parkside", "dulwich", "kensington",
                "hutt street", "rundle street", "northfield", "kilburn", "enfield",
                "mount barker", "hahndorf", "stirling", "aldgate", "crafers",
                "mount lofty", "cleland", "bridgewater", "mclaren vale", "willunga",
                "port noarlunga", "noarlunga", "aldinga", "aldinga beach", "moana",
            }
            if not localities or not any(x.casefold() in permitted for x in localities):
                continue

            image_data = event_data.get("image", "")
            if isinstance(image_data, dict):
                image_data = image_data.get("url") or image_data.get("contentUrl") or ""
            elif isinstance(image_data, list):
                image_data = image_data[0] if image_data else ""
                if isinstance(image_data, dict):
                    image_data = image_data.get("url") or ""
            image_url = normalise_url(str(image_data or ""), url)
            if not venue:
                venue = localities[0]
            events.append({
                "title": title, "venue": venue, "date": start, "end_date": end,
                "category": categorise_tourism_event(title), "image": image_url, "url": url,
            })
        except requests.RequestException:
            failed += 1

    if failed > max(3, len(urls) // 4):
        raise RuntimeError(f"Tourism: {failed}/{len(urls)} pages failed; preserving existing records")
    if not events:
        raise RuntimeError("Tourism: no eligible Adelaide events parsed; preserving existing records")
    print(f"    Tourism: {len(urls)} links, {len(events)} eligible events, {failed} failed pages")
    return events


# ============================================================
# TICKETMASTER DISCOVERY API — ADELAIDE REGION
# ============================================================

def parse_ticketmaster_adelaide(api_key):
    """Read official Ticketmaster Discovery API; never scrape checkout pages."""
    from datetime import date, timedelta
    from urllib.parse import urlparse
    if not api_key:
        print("Ticketmaster skipped: set TICKETMASTER_API_KEY first")
        return []

    session = requests.Session()
    today = date.today()
    results = []
    seen_ids = set()
    # Search a year ahead, 45 km from central Adelaide. Verify SA venue.
    for page in range(20):
        params = {
            "apikey": api_key, "countryCode": "AU", "latlong": "-34.9285,138.6007",
            "radius": 45, "unit": "km", "size": 200, "page": page,
            "sort": "date,asc", "startDateTime": today.strftime("%Y-%m-%dT00:00:00Z"),
            "endDateTime": (today + timedelta(days=366)).strftime("%Y-%m-%dT23:59:59Z"),
        }
        response = session.get("https://app.ticketmaster.com/discovery/v2/events.json", params=params, timeout=40)
        response.raise_for_status()
        data = response.json()
        items = data.get("_embedded", {}).get("events", [])
        for item in items:
            event_id = item.get("id")
            if not event_id or event_id in seen_ids:
                continue
            seen_ids.add(event_id)
            venues = item.get("_embedded", {}).get("venues", [])
            venue = venues[0] if venues else {}
            state = (venue.get("state") or {}).get("stateCode", "").upper()
            city = (venue.get("city") or {}).get("name", "")
            # Reject clearly non-SA venues; API location radius is also applied.
            if state and state != "SA":
                continue
            if not state and not city:
                continue
            name = (item.get("name") or "").strip()
            venue_name = (venue.get("name") or "").strip()
            dates = item.get("dates") or {}
            start = dates.get("start") or {}
            local_date = start.get("localDate")
            if not (name and venue_name and local_date):
                continue
            local_time = start.get("localTime") or "00:00:00"
            if len(local_time) == 5:
                local_time += ":00"
            dt = local_date + "T" + local_time
            if local_date < today.isoformat():
                continue
            classifications = item.get("classifications") or []
            genre = classifications[0] if classifications else {}
            segment = ((genre.get("segment") or {}).get("name") or "").lower()
            subgenre = ((genre.get("genre") or {}).get("name") or "").lower()
            if "comedy" in subgenre or "comedy" in segment:
                category = ["Comedy"]
            elif "music" in segment:
                category = ["Music"]
            elif "sport" in segment:
                category = ["Sport"]
            elif "arts" in segment or "theatre" in segment:
                category = ["Theatre"]
            else:
                category = categorise_event(name)
            images = item.get("images") or []
            images = [im for im in images if im.get("url") and im.get("width", 0) >= 400]
            images.sort(key=lambda im: abs(im.get("ratio", "") == "16_9") * -1)
            image = images[0]["url"] if images else ""
            url = item.get("url") or ""
            if urlparse(url).scheme not in ("http", "https"):
                continue
            results.append({"title": name, "venue": venue_name, "date": dt,
                            "category": category, "image": image, "url": url})
        pages = data.get("page") or {}
        if not items or page + 1 >= pages.get("totalPages", 1):
            break
    print("Ticketmaster Adelaide events collected:", len(results))
    return results



# ============================================================
# THEBARTON THEATRE — VERIFIED TICKETMASTER DISCOVERY
# ============================================================

def parse_thebarton_theatre(soup, source_url, api_key):
    """Match the theatre's linked Ticketmaster IDs to verified Adelaide API events.

    The homepage also promotes shows at other venues. Only events whose API
    venue is Thebarton Theatre are returned as theatre-source records.
    No dates, titles, or venues are inferred from image filenames.
    """
    import re
    from urllib.parse import urlparse

    linked_ids = set()
    for anchor in soup.find_all("a", href=True):
        match = re.search(r"/event/([A-Za-z0-9]+)", anchor["href"], re.I)
        if match:
            linked_ids.add(match.group(1).upper())

    print(f"    Thebarton homepage Ticketmaster IDs: {len(linked_ids)}")
    if not linked_ids:
        return []
    if not api_key:
        print("    Thebarton: Ticketmaster API key missing; preserving existing")
        return []

    # Reuse the established regional API parser and its verified local dates,
    # SA location checks, event classifications and booking URLs.
    discovered = parse_ticketmaster_adelaide(api_key)
    events = []
    matched = set()
    other_venues = 0
    for event in discovered:
        match = re.search(r"/event/([A-Za-z0-9]+)", str(event.get("url", "")), re.I)
        if not match:
            continue
        event_id = match.group(1).upper()
        if event_id not in linked_ids:
            continue
        matched.add(event_id)
        venue = re.sub(r"[^a-z0-9]+", " ", str(event.get("venue", "")).casefold()).strip()
        if venue not in ("thebarton theatre", "thebarton theater"):
            other_venues += 1
            continue
        events.append(event)

    print(f"    Thebarton: {len(events)} verified theatre events; "
          f"{other_venues} linked events at other venues")
    print(f"    Thebarton: {len(linked_ids - matched)} homepage IDs not found "
          "in the regional API (not invented)")
    return events


# ============================================================
# EXPERIENCE ADELAIDE (HTML event cards)
# ============================================================

def parse_experience_adelaide(soup, source_url):
    """Extract directory cards; do not guess missing dates or times."""
    from urllib.parse import urljoin
    seen = set()
    events = []
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }

    def date_from_text(value):
        match = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})\b", value)
        if not match:
            return ""
        try:
            return datetime(int(match[3]), months[match[2].lower()[:3]],
                            int(match[1])).strftime("%Y-%m-%dT00:00:00")
        except (ValueError, KeyError):
            return ""

    def category_for(title, raw):
        t = re.sub(r"[^a-z0-9]+", " ", title.lower())
        if "grand final parade" in t: return ["Festival"]
        if "christmas pageant" in t: return ["Family"]
        if any(x in t for x in ("tour down under", "adelaide international",
                                "colour frenzy", "grand final")): return ["Sport"]
        if "good music month" in t: return ["Music"]
        if any(x in t for x in ("taste gouger", "distillery sessions",
                                "melbourne cup on vardon", "huami")): return ["Food & Beverage"]
        if any(x in t for x in ("feast feastival", "italian festival", "ozasia festival")): return ["Festival"]
        if "pinkstachio" in t: return ["Club/Party"]
        if "moon lantern" in t or "hong kong dragon" in t: return ["Festival"]
        if "lucky dumpling market" in t: return ["Festival", "Food & Beverage"]
        mapping = {"sports and fitness": "Sport", "arts and culture": "Arts & Culture",
                   "music and concerts": "Music", "courses and workshops": "Workshop",
                   "bars and clubs": "Club/Party", "kids and family": "Family"}
        return [mapping.get(raw.lower().strip(), "Other")]

    for card in soup.select('[data-directory-type="events"]'):
        def val(selector):
            element = card.select_one(selector)
            return element.get_text(" ", strip=True) if element else ""

        title = val(".event-title")
        date_parts = re.split(r"\s+[-–]\s+", val(".detail-date"), maxsplit=1)
        start = date_from_text(date_parts[0])
        end = date_from_text(date_parts[1]) if len(date_parts) > 1 else ""
        link = card.select_one("a.thumb-link[href]")
        if not (title and start and link):
            continue
        url = urljoin(source_url, link["href"]).split("#", 1)[0]
        if url in seen:
            continue
        seen.add(url)
        image_element = card.select_one(".img-top")
        style = image_element.get("style", "") if image_element else ""
        image_match=re.search(r'background-image:\s*url\([\'\"]?([^\'\")]+)',style)
        events.append({
            "title": title, "venue": val(".location-address") or "Adelaide",
            "date": start, "end_date": end, "category": category_for(title, val(".event-cat")),
            "image": urljoin(source_url, image_match[1]) if image_match else "",
            "url": url,
        })
    return events


# ============================================================
# MOSHTIX — SA search pages + The Ed Castle venue page
# ============================================================

def parse_moshtix_adelaide():
    """Collect verified Adelaide CBD listings; fail safely on incomplete pages."""
    from html import unescape
    from urllib.parse import urlparse, urljoin

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    base = "https://www.moshtix.com.au"
    search = base + "/v2/search"
    ed = base + "/v2/venues/the-ed-castle-sa/10424"
    seen_ids = set()
    results = []

    # Strictly identified city venues/addresses. Postcode 5000 by itself
    # is not enough to prove CBD location. Add new venues after verification.
    verified_venues = {
        "the ed castle", "jive", "jive adelaide", "lion arts factory",
        "hindley st music hall", "hindley street music hall", "the austral hotel",
        "div de", "unibar adelaide", "unibar", "the gov", # the gov is explicitly excluded below
    }
    verified_streets = {
        "233 currie st", "233 currie street", "181 hindley st", "181 hindley street",
        "68 north terrace", "149 hindley st", "149 hindley street",
        "205 rundle street", "205 rundle st",
    }
    excluded_names = {"the gov", "governor hindmarsh hotel"}

    def normalized(text):
        return " ".join(re.sub(r"[^a-z0-9]+", " ", unescape(str(text)).casefold()).split())

    def city_location(location):
        if not isinstance(location, dict):
            return False
        address = location.get("address") or {}
        if not isinstance(address, dict):
            return False
        venue = normalized(location.get("name", ""))
        street = normalized(address.get("streetAddress", ""))
        locality = normalized(address.get("addressLocality", ""))
        postcode = str(address.get("postalCode", "")).strip()
        if venue in excluded_names:
            return False
        if venue in {"unibar", "unibar adelaide"} and postcode == "5005":
            return True
        if postcode != "5000":
            return False
        if any(x in street for x in verified_streets):
            return True
        return (locality == "adelaide" and bool(street)) or (venue in verified_venues and locality in {"adelaide", "hindley street"})

    def flatten(data):
        if isinstance(data, list):
            for item in data:
                yield from flatten(item)
        elif isinstance(data, dict):
            if data.get("@type") in ("MusicEvent", "Event", "Festival", "TheaterEvent", "DanceEvent", "ComedyEvent"):
                yield data
            if "@graph" in data:
                yield from flatten(data["@graph"])

    def collect(soup, page_url, ed_only=False):
        count = 0
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            for event in flatten(data):
                location = event.get("location") or {}
                if not city_location(location):
                    continue
                if ed_only and normalized(location.get("name", "")) != "the ed castle":
                    continue
                title = unescape(str(event.get("name", ""))).strip()
                start = str(event.get("startDate", "")).strip()
                link = urljoin(page_url, str(event.get("url", "")))
                match = re.search(r"/v2/event/[^/]+/(\d+)", link)
                if not match or not title or not re.match(r"^20\d{2}-\d{2}-\d{2}", start):
                    continue
                event_id = match.group(1)
                if event_id in seen_ids:
                    continue
                if re.search(r"\b(membership|gift voucher|gift card)\b", title, re.I):
                    continue
                if event.get("eventStatus") in ("EventCancelled", "EventPostponed"):
                    continue
                seen_ids.add(event_id)
                venue = unescape(str(location.get("name", ""))).strip()
                aliases = {
                    "jive adelaide": "Jive",
                    "lion arts factory adelaide": "Lion Arts Factory",
                    "hindley st music hall adelaide": "Hindley Street Music Hall",
                    "hindley st music hall": "Hindley Street Music Hall",
                }
                venue = aliases.get(normalized(venue), venue)
                image = event.get("image") or ""
                if isinstance(image, list):
                    image = image[0] if image else ""
                if isinstance(image, dict):
                    image = image.get("url", "")
                image = urljoin(base, str(image)).replace("http://www.moshtix.com.au/", "https://www.moshtix.com.au/")
                # Moshtix JSON-LD commonly supplies a tiny 140x140 thumbnail.
                # The same CDN artwork is available at 600x600; preserve the
                # rest of the URL unchanged (including any query parameters).
                image = re.sub(r"x140x140(?=\D|$)", "x600x600", image, flags=re.I)
                results.append({
                    "title": title,
                    "venue": venue,
                    "date": start,
                    "end_date": str(event.get("endDate") or ""),
                    "category": ["Music"] if event.get("@type") == "MusicEvent" else categorise_event(title),
                    "image": image,
                    "url": link,
                })
                count += 1
        return count

    def get_page(url, params=None):
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    # Search first, including all pagination. Fail the source if any page
    # errors, so existing Moshtix events are preserved by scrape.py.
    first = get_page(search, {"StateId": 5, "TimePeriod": 6, "Page": 1})
    page_numbers = [1]
    for a in first.find_all("a", href=True):
        m = re.search(r"[?&]Page=(\d+)", a["href"], re.I)
        if m:
            page_numbers.append(int(m.group(1)))
    last_page = max(page_numbers)
    if last_page > 100:
        raise RuntimeError("Unexpected Moshtix pagination; refusing incomplete scrape")
    for page in range(1, last_page + 1):
        soup = first if page == 1 else get_page(search, {"StateId": 5, "TimePeriod": 6, "Page": page})
        blocks = soup.select('script[type="application/ld+json"]')
        if not blocks:
            raise RuntimeError(f"Moshtix search page {page} had no structured data")
        found = collect(soup, search)
        print(f"    Moshtix search page {page}/{last_page}: {found} CBD events")

    ed_soup = get_page(ed)
    if not ed_soup.select('script[type="application/ld+json"]'):
        raise RuntimeError("The Ed Castle structured data missing")
    ed_count = collect(ed_soup, ed, ed_only=True)
    total_ed = sum(normalized(x["venue"]) == "the ed castle" for x in results)
    print(f"    The Ed Castle: {total_ed} unique events ({ed_count} newly collected)")
    print(f"    Moshtix: {len(results)} unique verified CBD events")
    if not results:
        raise RuntimeError("No verified Moshtix CBD events; preserving existing")
    return results


# ============================================================
# ALLEVENTS — VICTORIA SQUARE ONLY
# ============================================================

def parse_allevents_victoria_square(soup, source_url):
    """Import only verified events physically held in Victoria Square.

    AllEvents' venue landing pages also show unrelated nearby events.
    Therefore every candidate's individual page must confirm its venue.
    If the website changes its HTML, return zero and let scrape.py
    preserve existing records rather than guessing.
    """
    from urllib.parse import urlparse
    from datetime import timezone

    def is_square(name):
        value = re.sub(r"[^a-z0-9]+", " ", str(name or "").casefold()).strip()
        # Match the public square itself, not hotels and offices whose
        # street address happens to contain "Victoria Square".
        return bool(re.fullmatch(
            r"(?:victoria (?:square|sq)|tarntanyangga)"
            r"(?: (?:tarntanyangga|victoria (?:square|sq)|adelaide|sa|"
            r"south australia|australia|5000))*", value
        ))

    def schema_events(node):
        if isinstance(node, list):
            for child in node:
                yield from schema_events(child)
        elif isinstance(node, dict):
            kind = node.get("@type", "")
            types = kind if isinstance(kind, list) else [kind]
            if any(str(t).lower().endswith("event") for t in types):
                yield node
            for key in ("@graph", "itemListElement"):
                if key in node:
                    yield from schema_events(node[key])
            if "item" in node:
                yield from schema_events(node["item"])

    def location_names(location):
        if isinstance(location, list):
            return [n for item in location for n in location_names(item)]
        if isinstance(location, dict):
            return [str(location.get("name") or "")]
        return [str(location or "")]

    # AllEvents listing cards link to /adelaide/<event-slug>/<numeric-id>.
    # Do not follow the site's "events near" and recommended venue links.
    candidates = []
    seen = set()
    for a in soup.select("a[href]"):
        href = urljoin(source_url, a.get("href", "")).split("#")[0].split("?")[0]
        parsed = urlparse(href)
        if parsed.hostname not in ("allevents.in", "www.allevents.in"):
            continue
        if not re.fullmatch(r"/adelaide/[^/]+/\d{8,}", parsed.path):
            continue
        if href not in seen:
            seen.add(href)
            candidates.append(href)

    session = requests.Session()
    session.headers.update({"User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"})
    results = []
    for href in candidates[:100]:
        try:
            response = session.get(href, timeout=20)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, "lxml")
        except requests.RequestException:
            continue

        for script in detail.find_all("script", type="application/ld+json"):
            try:
                payload = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            for item in schema_events(payload):
                locations = location_names(item.get("location"))
                if not any(is_square(name) for name in locations):
                    continue
                title = str(item.get("name") or "").strip()
                raw_date = str(item.get("startDate") or "").strip()
                if not title or not re.match(r"^20\d\d-\d\d-\d\d", raw_date):
                    continue
                try:
                    date_part = datetime.fromisoformat(
                        raw_date.replace("Z", "+00:00")
                    )
                    # Avoid comparing timezone-aware against naive.
                    if date_part.date() < datetime.now().date():
                        continue
                except ValueError:
                    continue

                date = raw_date
                # Existing event schema expects ISO datetime with T.
                if len(date) == 10:
                    date += "T00:00:00"
                end = str(item.get("endDate") or "")
                if end and len(end) == 10:
                    end += "T23:59:59"
                picture = item.get("image") or ""
                if isinstance(picture, list):
                    picture = picture[0] if picture else ""
                if isinstance(picture, dict):
                    picture = picture.get("url") or picture.get("contentUrl") or ""
                event_url = str(item.get("url") or href)
                if urlparse(event_url).hostname not in ("allevents.in", "www.allevents.in"):
                    event_url = href
                results.append({
                    "title": title,
                    "venue": "Victoria Square / Tarntanyangga",
                    "date": date,
                    "end_date": end,
                    "category": categorise_event(title, str(item.get("description") or "")[:300]),
                    "image": urljoin(href, str(picture)) if picture else "",
                    "url": event_url,
                })
                break

    # Prevent repeated listing links from generating duplicate records.
    unique = {}
    for event in results:
        key = (event["title"].casefold(), event["date"][:10])
        unique.setdefault(key, event)
    print(f"    AllEvents: {len(candidates)} event links, "
          f"{len(unique)} verified Victoria Square events")
    return list(unique.values())



# ============================================================
# THE DRIVE — CURRENT WHAT'S ON ONLY
# ============================================================

def parse_the_drive(soup, source_url):
    """Read The Drive's current listing, verifying dates on detail pages.

    Deliberately reject missing years and old dates. Never infer a future
    year from a month/day on a stale page.
    """
    from urllib.parse import urlparse
    from datetime import date

    root = "https://www.thedriveadelaide.com.au"
    today = datetime.now().date()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0 Safari/537.36"})
    candidates = {}
    for heading in soup.find_all(["h2", "h3", "h4", "h5"]):
        anchor = heading.find("a", href=True) or heading.find_parent("a", href=True)
        if anchor is None:
            parent = heading.parent
            if parent is not None:
                anchor = parent.find("a", href=True)
        if anchor is None:
            continue
        title = heading.get_text(" ", strip=True)
        url = urljoin(source_url, anchor.get("href", "")).split("#")[0]
        parsed = urlparse(url)
        if not title or parsed.netloc.lower().removeprefix("www.") != "thedriveadelaide.com.au":
            continue
        if parsed.path.rstrip("/") in ("", "/whatson", "/events", "/past-events"):
            continue
        candidates[url] = title

    events = []
    rejected = 0
    for url, listing_title in candidates.items():
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, "lxml")
        except requests.RequestException as exc:
            print(f"    The Drive detail unavailable: {url} ({exc})")
            continue

        title = listing_title
        heading = detail.find("h1")
        if heading and heading.get_text(" ", strip=True):
            title = heading.get_text(" ", strip=True)
        if not title or "past event" in title.casefold():
            continue

        # Only structured event dates or explicit four-digit years are valid.
        start = ""
        end = ""
        image = ""
        for tag in detail.find_all("script", type="application/ld+json"):
            try:
                raw = json.loads(tag.string or tag.get_text())
            except (ValueError, TypeError):
                continue
            def walk(obj):
                if isinstance(obj, list):
                    for v in obj:
                        yield from walk(v)
                elif isinstance(obj, dict):
                    if obj.get("@type") == "Event" or (isinstance(obj.get("@type"), list) and "Event" in obj["@type"]):
                        yield obj
                    for k in ("@graph", "mainEntity", "itemListElement"):
                        if k in obj:
                            yield from walk(obj[k])
            for item in walk(raw):
                raw_start = str(item.get("startDate") or "")
                if re.match(r"^20\d{2}-\d{2}-\d{2}", raw_start):
                    start = raw_start
                    end = str(item.get("endDate") or "")
                    im = item.get("image") or ""
                    image = im[0] if isinstance(im, list) and im else (im if isinstance(im, str) else "")
                    break
            if start:
                break

        if not start:
            # Event detail content only; avoid footer/related-event dates.
            content = detail.find("article") or detail.find("main") or detail
            for tag in content.find_all("time"):
                value = str(tag.get("datetime") or tag.get_text(" ", strip=True))
                if re.search(r"20\d{2}", value):
                    start = parse_date_text(value)
                    if start:
                        break
            if not start:
                text = content.get_text(" ", strip=True)
                start = parse_date_text(text[:2200])

        try:
            day = datetime.fromisoformat(start[:10]).date()
        except (ValueError, TypeError):
            rejected += 1
            continue
        if day < today:
            try:
                last = datetime.fromisoformat(end[:10]).date()
            except (ValueError, TypeError):
                last = day
            if last < today:
                rejected += 1
                continue

        if not image:
            meta = detail.find("meta", attrs={"property": "og:image"})
            image = str(meta.get("content") or "") if meta else ""
        if image and any(x in image.casefold() for x in ("favicon", "logo")):
            image = ""
        category = ["Sport"] if any(w in title.casefold() for w in ("tennis", "volleyball", "championship", "finals", "league")) else categorise_event(title)
        events.append({"title": title, "venue": "The Drive", "date": start,
                       "end_date": end if end[:10] != start[:10] else "",
                       "category": category, "image": urljoin(url, image) if image else "",
                       "url": url})
    print(f"    The Drive: {len(candidates)} candidate pages; {len(events)} verified current events; {rejected} stale/undated excluded")
    return events


# ============================================================
# ADELAIDE SYMPHONY ORCHESTRA — INDIVIDUAL SESSIONS
# ============================================================

def parse_adelaide_symphony_orchestra(soup, source_url):
    """Extract confirmed, individually dated ASO performances.

    Do not invent a year or venue. One event record per session, including
    multiple performances on the same date at different confirmed times.
    """
    from urllib.parse import urlparse
    from datetime import date

    today = datetime.now().date()
    domain = "aso.com.au"
    urls = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        url = urljoin(source_url, anchor["href"]).split("#", 1)[0].split("?", 1)[0]
        parsed = urlparse(url)
        if (parsed.hostname or "").lower().removeprefix("www.") != domain:
            continue
        if not re.fullmatch(r"/events/[^/]+/?", parsed.path):
            continue
        key = url.rstrip("/").lower()
        if key not in seen:
            seen.add(key)
            urls.append(url)

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0 Safari/537.36"})
    events = []
    errors = 0
    missing = 0
    # Only complete dates and explicit session times are accepted.
    date_pattern = re.compile(
        r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)(?:day)?\s+"
        r"(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+"
        r"(20\d{2}),?\s+(\d{1,2}:\d{2}\s*(?:am|pm))\b", re.I)
    months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
              "jul":7,"aug":8,"sep":9,"sept":9,"oct":10,"nov":11,"dec":12}
    for url in urls:
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, "lxml")
        except requests.RequestException as exc:
            errors += 1
            print(f"    ASO detail ERROR: {url} ({exc})")
            continue

        heading = detail.find("h1")
        title = heading.get_text(" ", strip=True) if heading else ""
        if not title:
            missing += 1
            continue
        # ASO event pages explicitly identify the venue with 'Where'.
        venue = ""
        for node in detail.find_all(string=re.compile(r"^\s*Where\s*$", re.I)):
            parent = node.parent
            if parent is None:
                continue
            candidate = parent.get_text(" ", strip=True)
            if candidate.casefold() == "where" and parent.parent:
                candidate = parent.parent.get_text(" ", strip=True)
            candidate = re.sub(r"^Where\s*", "", candidate, flags=re.I).strip(" :-")
            candidate = re.split(r"\bPrices\b", candidate, maxsplit=1, flags=re.I)[0].strip()
            if candidate and candidate.casefold() != "where" and len(candidate) < 100:
                venue = candidate
                break
        if not venue:
            # The visible event page often renders 'Where VENUE' as one item.
            for node in detail.find_all(["li", "p", "div", "span"]):
                candidate = node.get_text(" ", strip=True)
                match = re.fullmatch(r"Where\s+(.{3,85})", candidate, re.I)
                if match and "Prices" not in match.group(1):
                    venue = match.group(1).strip()
                    break
        if not venue:
            missing += 1
            print(f"    ASO missing venue: {title}")
            continue
        venue = re.sub(r"\s+", " ", venue).replace("’", "'")
        image = _official_event_artwork(detail, url, title)
        # An animated GIF/WebP may be the site's motion hero. Prefer a
        # labelled static image of this concert if the page provides one.
        if image and image.lower().split("?", 1)[0].endswith(".gif"):
            for img in detail.select('main img, article img'):
                candidate = _official_event_artwork(
                    BeautifulSoup(str(img), "lxml"), url, title)
                if candidate and not candidate.lower().split("?", 1)[0].endswith(".gif"):
                    image = candidate
                    break

        # Restrict dates to the event's booking information, before the
        # description / 'You might also like' recommendations.
        content = detail.find("main") or detail.find("article") or detail.body or detail
        parts = list(content.stripped_strings)
        title_index = next((i for i,t in enumerate(parts) if t.strip() == title), None)
        if title_index is None:
            missing += 1
            continue
        tail = parts[title_index + 1:]
        stop = next((i for i,t in enumerate(tail) if re.search(
            r"Book this concert as part of a package|You might also like|Venue Accessibility", t, re.I)), len(tail))
        tail = tail[:stop]
        # Limit to booking header: descriptions may mention historical dates.
        session_text = " ".join(tail[:min(len(tail), 220)])
        found = set()
        for match in date_pattern.finditer(session_text):
            try:
                mon = match.group(2).lower()[:3]
                dt = datetime.strptime(match.group(4).replace(" ", "").lower(), "%I:%M%p")
                day = datetime(int(match.group(3)), months[mon], int(match.group(1)), dt.hour, dt.minute)
            except (ValueError, KeyError):
                continue
            if day.date() < today:
                continue
            iso = day.isoformat(timespec="seconds")
            if iso in found:
                continue
            found.add(iso)
            events.append({"title":title,"venue":venue,"date":iso,"end_date":"",
                           "category":["Music"],"image":image,"url":url})
        if not found:
            missing += 1
            print(f"    ASO no confirmed future sessions: {title}")
    print(f"    ASO: {len(urls)} event pages, {len(events)} verified sessions; "
          f"{errors} page errors, {missing} without usable session/venue")
    return events


# ============================================================
# ALLEVENTS ADELAIDE AND SURROUNDS — VERIFIED DETAIL PAGES
# ============================================================

def parse_allevents_adelaide_and_surrounds(soup, source_url):
    """Discover AllEvents listings and verify their individual event metadata.

    Broad directory pages contain suggestions from other states and past events;
    neither a listing title nor its city label is sufficient evidence. Only
    confirmed Adelaide/nearby South Australian locations are accepted.
    """
    from urllib.parse import urlparse
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import date

    listing_urls = [
        source_url.rstrip('/'),
        'https://allevents.in/adelaide/bonython',
        'https://allevents.in/adelaide/bonython%20park',
        'https://allevents.in/adelaide/events',
    ]
    session = requests.Session()
    session.headers.update({'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'})
    pages = [(source_url, soup)]
    for listing_url in listing_urls[1:]:
        try:
            response = session.get(listing_url, timeout=25)
            response.raise_for_status()
            pages.append((listing_url, BeautifulSoup(response.text, 'lxml')))
        except requests.RequestException as exc:
            print(f'    AllEvents listing unavailable: {listing_url} ({exc})')

    def iter_events(node):
        if isinstance(node, list):
            for child in node:
                yield from iter_events(child)
        elif isinstance(node, dict):
            kinds = node.get('@type', [])
            kinds = kinds if isinstance(kinds, list) else [kinds]
            if any(str(kind).casefold().endswith('event') for kind in kinds):
                yield node
            for key in ('@graph', 'itemListElement', 'item'):
                if key in node:
                    yield from iter_events(node[key])

    def event_location(node):
        if isinstance(node, list):
            return [value for part in node for value in event_location(part)]
        if isinstance(node, dict):
            address = node.get('address') or {}
            if isinstance(address, dict):
                address_text = ' '.join(str(address.get(k) or '') for k in
                    ('streetAddress', 'addressLocality', 'addressRegion', 'postalCode', 'addressCountry'))
            else:
                address_text = str(address)
            return [(str(node.get('name') or '').strip(), address_text.strip())]
        return [(str(node or '').strip(), '')]

    def local_location(venue, address):
        text = f'{venue} {address}'.casefold()
        # A recognisable SA place is required; the site's Adelaide URL alone
        # does not establish where a recommended event is actually held.
        excluded = re.search(r'\b(?:vic|victoria|nsw|new south wales|qld|queensland|wa|western australia|tas|tasmania|nt|northern territory|act|canberra)\b', text)
        if excluded:
            return False
        if re.search(r'\b(?:adelaide|north adelaide|port adelaide|glenelg|norwood|unley|prospect|thebarton|hindmarsh|bowden|mile end|west lakes|henley beach|brighton|semaphore|grange|modbury|marion|morphettville|mclaren vale|hahndorf|mount barker|mt barker|bonython|tulya wardli|tarntanyangga|victoria square|south australia)\b', text):
            return True
        if re.search(r'\bSA\s*5\d{3}\b', f'{venue} {address}'):
            return True
        return False

    links = set()
    for listing_url, listing in pages:
        for anchor in listing.select('a[href]'):
            href = urljoin(listing_url, anchor.get('href', '')).split('#')[0].split('?')[0]
            parsed = urlparse(href)
            if (parsed.hostname or '').lower() not in ('allevents.in', 'www.allevents.in'):
                continue
            # Individual event URLs have a numeric ID; exclude directory pages.
            if re.fullmatch(r'/[^/]+/[^/]+/\d{8,}', parsed.path):
                links.add(href)

    def fetch_detail(href):
        try:
            response = session.get(href, timeout=22)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException:
            return []
        found = []
        for script in detail.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            for item in iter_events(data):
                title = str(item.get('name') or '').strip()
                start = str(item.get('startDate') or '').strip()
                if not title or not re.match(r'^20\d{2}-\d{2}-\d{2}', start):
                    continue
                try:
                    if datetime.fromisoformat(start.replace('Z', '+00:00')).date() < date.today():
                        continue
                except ValueError:
                    continue
                locations = event_location(item.get('location'))
                verified = [(venue, address) for venue, address in locations
                            if venue and local_location(venue, address)]
                if not verified:
                    continue
                venue, address = verified[0]
                # Avoid generic city labels as venue names.
                if venue.casefold() in ('adelaide', 'south australia', 'sa'):
                    continue
                end = str(item.get('endDate') or '')
                if len(start) == 10:
                    start += 'T00:00:00'
                if len(end) == 10:
                    end += 'T23:59:59'
                image = item.get('image') or ''
                if isinstance(image, list):
                    image = image[0] if image else ''
                if isinstance(image, dict):
                    image = image.get('url') or image.get('contentUrl') or ''
                found.append({
                    'title': title, 'venue': venue, 'date': start,
                    'end_date': end,
                    'category': categorise_event(title, str(item.get('description') or '')[:300]),
                    'image': urljoin(href, str(image)) if image else '',
                    'url': href,
                })
        return found

    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_detail, href) for href in sorted(links)[:350]]
        for future in as_completed(futures):
            results.extend(future.result())
    unique = {}
    for event in results:
        key = (re.sub(r'[^a-z0-9]+', ' ', event['title'].casefold()).strip(),
               event['date'], re.sub(r'[^a-z0-9]+', ' ', event['venue'].casefold()).strip())
        unique.setdefault(key, event)
    bonython = sum(bool(re.search(r'bonython|tulya wardli', e['venue'], re.I))
                   for e in unique.values())
    print(f'    AllEvents Adelaide: {len(pages)} listing pages, {len(links)} detail links, '
          f'{len(unique)} verified local events ({bonython} Bonython)')
    return list(unique.values())


# ============================================================
# STATE OPERA SOUTH AUSTRALIA — SA performances only
# ============================================================

def parse_state_opera_south_australia(soup, source_url):
    """Discover production detail pages and accept only SA-located performances.

    Conservative by design: a missing/unrecognised venue is NOT proof that an
    event is in South Australia. Do not guess a year, location or performance
    time. A production date range is a single listing unless individual
    performance sessions are explicitly published in structured event data.
    """
    from urllib.parse import urlparse
    from datetime import date as calendar_date

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
    })
    known_sa_venues = {
        "her majesty's theatre", "her majesty’s theatre", "festival theatre",
        "dunstan playhouse", "space theatre", "adelaide festival centre",
        "st peter's cathedral", "st peter’s cathedral", "st peters cathedral",
        "ukaria cultural centre", "ukaria", "barossa arts centre",
        "adelaide town hall", "nexus arts", "adelaide entertainment centre",
        "elder hall", "adelaide concert hall", "adelaide oval",
    }
    other_state_pattern = re.compile(
        r"\b(?:NSW|VIC|QLD|WA|TAS|NT|ACT|New South Wales|Victoria|"
        r"Queensland|Western Australia|Tasmania|Northern Territory|"
        r"Canberra|Melbourne|Sydney|Brisbane|Perth|Hobart|Darwin|"
        r"London|Hong Kong|New Zealand)\b", re.I)

    def plain(value):
        return " ".join(str(value or "").replace("\xa0", " ").split())

    def is_sa(venue, address):
        venue = plain(venue)
        address = plain(address)
        if other_state_pattern.search(venue + " " + address):
            return False
        if venue.casefold() in known_sa_venues:
            return True
        # Require an explicit SA address, not the organisation's postal address.
        return bool(re.search(r"\b(?:South Australia|SA\s*5\d{3})\b", address, re.I))

    def get_structured(page):
        result = []
        def visit(node):
            if isinstance(node, list):
                for part in node: visit(part)
            elif isinstance(node, dict):
                kinds = node.get("@type", [])
                kinds = kinds if isinstance(kinds, list) else [kinds]
                if any(str(k).split("/")[-1] in ("Event", "MusicEvent", "TheaterEvent") for k in kinds):
                    result.append(node)
                if "@graph" in node: visit(node["@graph"])
        for script in page.select('script[type="application/ld+json"]'):
            try: visit(json.loads(script.string or script.get_text()))
            except (ValueError, TypeError): pass
        return result

    def structured_location(obj):
        loc = obj.get("location") or {}
        if isinstance(loc, list): loc = next((x for x in loc if isinstance(x, dict)), {})
        if not isinstance(loc, dict): return "", ""
        venue = plain(loc.get("name"))
        addr = loc.get("address") or {}
        if isinstance(addr, dict):
            address = " ".join(plain(addr.get(k)) for k in (
                "streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"))
        else: address = plain(addr)
        return venue, address

    def iso_date(raw):
        raw = plain(raw)
        if not re.match(r"^20\d\d-\d\d-\d\d(?:$|T)", raw): return ""
        try: calendar_date.fromisoformat(raw[:10])
        except ValueError: return ""
        return raw[:19] if "T" in raw and len(raw) >= 19 else raw[:10] + "T00:00:00"

    urls = set()
    for link in soup.select('a[href]'):
        url = normalise_url(link.get('href'), source_url).split('#')[0].split('?')[0].rstrip('/')
        parsed = urlparse(url)
        if parsed.hostname not in ('stateopera.com.au', 'www.stateopera.com.au'): continue
        if re.fullmatch(r'/productions/20\d\d/[^/]+', parsed.path, re.I): urls.add(url)
    if not urls:
        print('    State Opera: no production detail links found; preserving existing events')
        return []

    results = []
    seen = set()
    failed = 0
    outside = 0
    undated = 0
    for url in sorted(urls):
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            page = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as exc:
            failed += 1
            print(f'    State Opera detail error: {url} -> {exc}')
            continue
        h1 = page.find('h1')
        title = plain(h1.get_text(' ', strip=True)) if h1 else ''
        if not title: continue
        # Prefer the production's own artwork over site-wide social imagery.
        # State Opera pages can omit og:image and use responsive <picture>,
        # lazy-loaded <img>, or CSS background images for their hero.
        def production_artwork(page, page_url):
            from urllib.parse import urlparse

            def usable(candidate):
                candidate = str(candidate or '').strip().strip('\"\'')
                if not candidate or candidate.startswith(('data:', 'blob:', '#')):
                    return ''
                absolute = normalise_url(candidate, page_url)
                parsed = urlparse(absolute)
                if parsed.scheme not in ('http', 'https'):
                    return ''
                lowered = parsed.path.casefold()
                if any(term in lowered for term in (
                    'logo', 'favicon', 'icon-', 'placeholder', 'default-image',
                    'jubilee-fund', 'partner', 'sponsor', 'donate', 'footer',
                )):
                    return ''
                return absolute

            def srcset_largest(value):
                options = []
                for entry in str(value or '').split(','):
                    parts = entry.strip().split()
                    if not parts:
                        continue
                    weight = 0
                    if len(parts) > 1:
                        descriptor = parts[-1].lower()
                        try:
                            if descriptor.endswith('w'):
                                weight = float(descriptor[:-1])
                            elif descriptor.endswith('x'):
                                weight = float(descriptor[:-1]) * 1000
                        except ValueError:
                            pass
                    options.append((weight, parts[0]))
                for _, candidate in sorted(options, reverse=True):
                    found = usable(candidate)
                    if found:
                        return found
                return ''

            def from_element(element):
                if element.name == 'picture':
                    for img in element.select('img'):
                        result = from_element(img)
                        if result:
                            return result
                    for source in element.select('source'):
                        result = from_element(source)
                        if result:
                            return result
                for attr in ('data-srcset', 'srcset'):
                    found = srcset_largest(element.get(attr))
                    if found:
                        return found
                for attr in ('data-src', 'data-lazy-src', 'data-original', 'src'):
                    found = usable(element.get(attr))
                    if found:
                        return found
                for attr in ('style', 'data-bg', 'data-background-image'):
                    value = str(element.get(attr) or '')
                    match = re.search(r'url\(\s*[\"\']?([^\"\')]+)', value, re.I)
                    found = usable(match.group(1) if match else value if attr != 'style' else '')
                    if found:
                        return found
                return ''

            # Hero / primary production content comes before other page images.
            selectors = (
                'main [class*="hero"] picture', 'main [class*="hero"] img',
                'main [class*="banner"] picture', 'main [class*="banner"] img',
                '[class*="production-hero"] picture', '[class*="production-hero"] img',
                'main picture', 'main img',
                'main [style*="background-image"]',
                '[class*="hero"] [style*="background-image"]',
            )
            for selector in selectors:
                for element in page.select(selector):
                    # Exclude artwork in the page's footer and promotional sections.
                    if element.find_parent(('footer', 'nav')):
                        continue
                    found = from_element(element)
                    if found:
                        return found

            # Structured data may provide artwork when no visible hero exists.
            for script in page.select('script[type="application/ld+json"]'):
                try:
                    data = json.loads(script.string or script.get_text())
                except (ValueError, TypeError):
                    continue
                nodes = data if isinstance(data, list) else [data]
                while nodes:
                    item = nodes.pop(0)
                    if not isinstance(item, dict):
                        continue
                    graph = item.get('@graph')
                    if isinstance(graph, list):
                        nodes.extend(graph)
                    elif isinstance(graph, dict):
                        nodes.append(graph)
                    kinds = item.get('@type', [])
                    kinds = kinds if isinstance(kinds, list) else [kinds]
                    if not any(str(k).split('/')[-1] in
                               ('Event', 'MusicEvent', 'TheaterEvent') for k in kinds):
                        continue
                    value = item.get('image')
                    values = value if isinstance(value, list) else [value]
                    for candidate in values:
                        if isinstance(candidate, dict):
                            candidate = candidate.get('url') or candidate.get('contentUrl')
                        found = usable(candidate)
                        if found:
                            return found

            for attrs in ({'property': 'og:image'},
                          {'name': 'twitter:image'},
                          {'property': 'twitter:image'}):
                tag = page.find('meta', attrs=attrs)
                found = usable(tag.get('content')) if tag else ''
                if found:
                    return found
            return ''

        image = production_artwork(page, url)
        structured = get_structured(page)
        added = 0
        for item in structured:
            venue, address = structured_location(item)
            if not is_sa(venue, address):
                outside += 1
                continue
            start = iso_date(item.get('startDate'))
            if not start:
                undated += 1
                continue
            if start[:10] < calendar_date.today().isoformat(): continue
            end = iso_date(item.get('endDate'))
            if end and end < start: end = ''
            key = (title.casefold(), venue.casefold(), start)
            if key in seen: continue
            seen.add(key)
            results.append({'title': title, 'venue': venue, 'date': start,
                'end_date': end if end != start else '',
                'category': ['Theatre', 'Music'], 'image': image,
                'url': url})
            added += 1
        if added: continue

        # When Event JSON-LD is absent, accept the production's visible
        # date range ONLY if the venue is explicitly a recognised SA venue.
        # This is one production listing, not fabricated daily performances.
        text = plain(page.get_text(' ', strip=True))
        venue = next((v for v in sorted(known_sa_venues, key=len, reverse=True)
                      if re.search(r'(?<!\w)' + re.escape(v) + r'(?!\w)', text, re.I)), '')
        if not venue:
            outside += 1
            continue
        # The header contains the year and start date; never infer a year.
        date_match = re.search(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\s*[–—-]\s*(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b', text, re.I)
        single_match = re.search(r'\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b', text, re.I)
        if not date_match and not single_match:
            undated += 1
            continue
        def as_iso(day, month, year):
            months = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
            try: return calendar_date(int(year), months.index(month[:3].lower()) + 1, int(day)).isoformat()
            except (ValueError, IndexError): return ''
        m = date_match or single_match
        start_day = as_iso(m.group(1), m.group(2), m.group(3))
        end_day = as_iso(m.group(4), m.group(5), m.group(6)) if date_match else ''
        if not start_day or (end_day and end_day < start_day): continue
        if (end_day or start_day) < calendar_date.today().isoformat(): continue
        key = (title.casefold(), venue.casefold(), start_day)
        if key in seen: continue
        seen.add(key)
        results.append({'title': title, 'venue': venue.title() if venue == venue.lower() else venue,
            'date': start_day + 'T00:00:00',
            'end_date': end_day + 'T23:59:59' if end_day and end_day != start_day else '',
            'category': ['Theatre', 'Music'], 'image': image, 'url': url})
    print(f'    State Opera: {len(urls)} production pages, {len(results)} SA listings, '
          f'{outside} unverified/outside-SA, {undated} undated, {failed} page errors')
    if failed:
        raise RuntimeError('State Opera production pages incomplete; preserve previous records')
    return results


# ============================================================
# GOVERNMENT HOUSE - PUBLIC VISITOR EVENTS ONLY
# ============================================================

GOVERNMENT_HOUSE_IMAGE = 'https://www.governor.sa.gov.au/assets/_1400x846_crop_center-center_none/13610/Government-House-Adelaide-March-2023.webp'

def parse_government_house(soup, source_url):
    """Read confirmed Government House tour dates; never infer recurring dates."""
    from datetime import date
    from urllib.parse import urljoin

    base = "https://www.governor.sa.gov.au"
    lunch_url = base + "/vice-regal/lunch-on-the-lawns"
    open_url = base + "/vice-regal/government-house-open-day"
    fallback_booking = "https://ghadelaide.eventsair.com/garden-tours-26/registrations-2026"
    today = date.today()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    events = []

    def page_text(page):
        main = page.find("main") or page.find("article") or page
        return " ".join(main.stripped_strings)

    def page_image(page, url):
        for key in ("og:image", "twitter:image"):
            tag = page.find("meta", attrs={"property": key}) or page.find("meta", attrs={"name": key})
            candidate = tag.get("content", "") if tag else ""
            if candidate and not any(x in candidate.lower() for x in ("logo", "favicon", "icon", "crown")):
                return urljoin(url, candidate)
        return ""

    def fetch(url):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def add(title, day, start_hour, start_minute, end_hour, end_minute, url, image):
        if day < today:
            return
        start = datetime(day.year, day.month, day.day, start_hour, start_minute)
        end = datetime(day.year, day.month, day.day, end_hour, end_minute)
        events.append({
            "title": title, "venue": "Government House",
            "date": start.isoformat(timespec="seconds"),
            "end_date": end.isoformat(timespec="seconds"),
            "category": ["Community"], "image": GOVERNMENT_HOUSE_IMAGE, "url": url,
        })

    lunch_text = page_text(soup)
    image = page_image(soup, lunch_url)
    # Find the official registration link, rather than assuming it stays at a 2026 URL.
    booking_urls = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(lunch_url, anchor["href"])
        if "ghadelaide.eventsair.com" in href.lower() and "garden-tour" in href.lower():
            if href not in booking_urls:
                booking_urls.append(href)
    if not booking_urls:
        booking_urls = [fallback_booking]

    for booking_url in booking_urls:
        try:
            booking_page = fetch(booking_url)
        except requests.RequestException as exc:
            print(f"    Government House: unable to read tour registration dates: {exc}")
            continue
        booking_text = page_text(booking_page)
        # The official form uses 'Register for Friday, 6 November 2026 Full'.
        # Capture the status before the next date or field label.
        pattern = (r"Register\s+for\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
                   r"\s*,?\s*(\d{1,2})\s+"
                   r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                   r"\s+(20\d{2})\b")
        matches = list(re.finditer(pattern, booking_text, re.I))
        print(f"    Government House: {len(matches)} dated tour options found in registration form")
        for idx, match in enumerate(matches):
            weekday, day_num, month_name, year_num = match.groups()
            try:
                day = date(int(year_num), MONTHS[month_name.lower()], int(day_num))
            except ValueError:
                continue
            if day.strftime("%A").lower() != weekday.lower():
                print(f"    Government House: skipped weekday mismatch: {match.group(0)}")
                continue
            tail_end = matches[idx + 1].start() if idx + 1 < len(matches) else min(len(booking_text), match.end() + 80)
            status_text = booking_text[match.end():tail_end][:80]
            full = bool(re.search(r"\bfull\b|\bfully\s+booked\b", status_text, re.I))
            title = "Government House Garden Tour (Fully Booked)" if full else "Government House Garden Tour"
            if not any(e["date"].startswith(day.isoformat()) and "Garden Tour" in e["title"] for e in events):
                add(title, day, 10, 45, 11, 45, booking_url, image)

    print("    Government House: no Lunch on the Lawns dates inferred without a dated announcement")

    try:
        open_page = fetch(open_url)
        open_text = page_text(open_page)
        # An undated announcement supersedes unrelated dates elsewhere on the page.
        unannounced = bool(re.search(
            r"(?:next|upcoming)\s+(?:Government\s+House\s+)?Open\s+Day.{0,120}"
            r"(?:announced\s+soon|yet\s+to\s+be\s+announced|to\s+be\s+announced|TBA)",
            open_text, re.I))
        if unannounced:
            print("    Government House: next Open Day not yet announced")
        else:
            # Require a date explicitly in an Open Day announcement, not merely
            # another date in a sidebar or site footer.
            for match in re.finditer(
                r"\b(?:Government\s+House\s+)?Open\s+Day\b.{0,100}?"
                r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b",
                open_text, re.I):
                try:
                    day = date(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1)))
                except ValueError:
                    continue
                if day >= today:
                    # Unknown hours: omit event rather than publishing midnight as opening time.
                    print(f"    Government House: Open Day {day} found, but hours require verification; not added")
    except requests.RequestException as exc:
        print(f"    Government House: Open Day page unavailable: {exc}")

    print(f"    Government House: {len(events)} confirmed dated public activities")
    return events


# ============================================================
# NEXUS ARTS — official event pages
# ============================================================

def parse_nexus_arts(soup, source_url):
    """Collect dated Nexus Arts performances and exhibitions.

    Discover links from What's On, then verify dates on each detail page.
    Never guess a year or publish undated announcements.
    """
    from datetime import date as _date
    from urllib.parse import urlparse

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    today = _date.today()
    events = []
    candidates = {}
    # Nexus uses /events/<slug>/ detail URLs, not /whats-on/<slug>/.
    # Inspect all anchors because its cards are not necessarily inside <main>.
    for page_number in range(1, 5):
        url = source_url if page_number == 1 else source_url.rstrip('/') + f'/page/{page_number}/'
        if page_number == 1:
            page = soup
        else:
            try:
                response = session.get(url, timeout=20)
                if not response.ok:
                    break
                page = BeautifulSoup(response.text, 'lxml')
            except requests.RequestException:
                break
        added = 0
        for anchor in page.find_all('a', href=True):
            href = normalise_url(anchor.get('href'), url).split('#', 1)[0].split('?', 1)[0]
            parsed = urlparse(href)
            if parsed.hostname not in ('nexusarts.org.au', 'www.nexusarts.org.au'):
                continue
            if not re.match(r'^/events/[^/]+/?$', parsed.path, re.I):
                continue
            if href not in candidates:
                candidates[href] = ''
                added += 1
        if page_number > 1 and added == 0:
            break
    # Homepage also features upcoming official events when listing pagination
    # is incomplete. This is discovery only; each detail page is verified.
    try:
        home = session.get('https://nexusarts.org.au/', timeout=20)
        if home.ok:
            for anchor in BeautifulSoup(home.text, 'lxml').find_all('a', href=True):
                href = normalise_url(anchor.get('href'), 'https://nexusarts.org.au/')
                href = href.split('#', 1)[0].split('?', 1)[0]
                parsed = urlparse(href)
                if parsed.hostname in ('nexusarts.org.au', 'www.nexusarts.org.au') and re.match(r'^/events/[^/]+/?$', parsed.path, re.I):
                    candidates.setdefault(href, '')
    except requests.RequestException:
        pass
    print(f'    Nexus Arts: {len(candidates)} candidate event links')

    def metadata(page, key):
        tag = page.find('meta', attrs={'property': key}) or page.find('meta', attrs={'name': key})
        return str(tag.get('content', '')).strip() if tag else ''

    def parse_explicit_date(value):
        value = ' '.join(str(value or '').split())
        # ISO date or datetime, retaining confirmed clock time.
        match = re.search(r'\b(20\d{2})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2}))?', value)
        if match:
            try:
                return datetime(int(match[1]), int(match[2]), int(match[3]), int(match[4] or 0), int(match[5] or 0))
            except ValueError:
                return None
        month_names = '|'.join(MONTHS)
        match = re.search(r'\b(\d{1,2})\s+(' + month_names + r')\s*,?\s*(20\d{2})\b', value, re.I)
        if match:
            try:
                return datetime(int(match[3]), MONTHS[match[2].lower()], int(match[1]))
            except ValueError:
                return None
        match = re.search(r'\b(' + month_names + r')\s+(\d{1,2}),?\s+(20\d{2})\b', value, re.I)
        if match:
            try:
                return datetime(int(match[3]), MONTHS[match[1].lower()], int(match[2]))
            except ValueError:
                return None
        return None

    seen = set()
    for event_url, listing_context in list(candidates.items())[:100]:
        try:
            response = session.get(event_url, timeout=20)
            response.raise_for_status()
            page = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as exc:
            print(f'    Nexus Arts: skipped inaccessible page {event_url}: {exc}')
            continue
        main = page.find('main') or page.find('article') or page
        heading = main.find('h1') or page.find('h1')
        title = ' '.join(heading.stripped_strings) if heading else metadata(page, 'og:title')
        title = re.sub(r'\s*[|–-]\s*Nexus Arts\s*$', '', title, flags=re.I).strip()
        if not title:
            continue
        text = ' '.join(main.stripped_strings)
        structured = []
        for script in page.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            queue = [data]
            while queue:
                item = queue.pop()
                if isinstance(item, list):
                    queue.extend(item)
                elif isinstance(item, dict):
                    typ = item.get('@type', '')
                    if typ == 'Event' or isinstance(typ, list) and 'Event' in typ:
                        structured.append(item)
                    if '@graph' in item:
                        queue.append(item['@graph'])
        starts = []
        for item in structured:
            dt = parse_explicit_date(item.get('startDate'))
            if dt:
                starts.append((dt, parse_explicit_date(item.get('endDate')), item))
        if not starts:
            # Nexus event pages label their date as "When 12 Nov - 18 Dec 2026".
            # Extract that field rather than parsing unrelated page text.
            when_match = re.search(r'\bWhen\s+(.{0,90}?)\s+Where\b', text, re.I)
            when_text = when_match.group(1) if when_match else ''
            months_short = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
                            'jul':7,'aug':8,'sep':9,'sept':9,'oct':10,'nov':11,'dec':12}
            def nexus_short_date(day, month, year):
                try:
                    return datetime(int(year), months_short[month.lower()[:4] if month.lower()[:4]=='sept' else month.lower()[:3]], int(day))
                except (ValueError, KeyError):
                    return None
            range_match = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})\s*[-–—]\s*(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})', when_text)
            same_month = re.search(r'(\d{1,2})\s*[-–—]\s*(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})', when_text)
            single = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})', when_text)
            if range_match:
                start = nexus_short_date(range_match[1], range_match[2], range_match[5])
                end = nexus_short_date(range_match[3], range_match[4], range_match[5])
            elif same_month:
                start = nexus_short_date(same_month[1], same_month[3], same_month[4])
                end = nexus_short_date(same_month[2], same_month[3], same_month[4])
            elif single:
                start = nexus_short_date(single[1], single[2], single[3])
                end = None
            else:
                start = end = None
            if start:
                starts.append((start, end, {}))
        if not starts:
            # Date must be explicitly present in the event content; do not
            # fall back to unrelated footer or site-wide calendar dates.
            # No verified event date: skip this page.
            pass
        for start, end, item in starts:
            if (end or start).date() < today:
                continue
            item_title = str(item.get('name') or title).strip()
            if item_title:
                title_to_use = item_title
            else:
                title_to_use = title
            location = item.get('location') or {}
            if isinstance(location, dict):
                venue = str(location.get('name') or '').strip()
            else:
                venue = ''
            if not venue or venue.casefold() in ('nexus arts', 'nexus'):
                venue = 'Nexus Arts Gallery' if re.search(r'\b(exhibition|gallery)\b', title_to_use + ' ' + text[:500], re.I) else 'Nexus Arts Venue'
            image = item.get('image') or metadata(page, 'og:image') or metadata(page, 'twitter:image')
            if isinstance(image, list):
                image = image[0] if image else ''
            if isinstance(image, dict):
                image = image.get('url') or image.get('contentUrl') or ''
            image = normalise_url(str(image or ''), event_url)
            if any(x in image.lower() for x in ('logo', 'favicon', 'placeholder')):
                image = ''
            if not image:
                image = get_image(main, event_url)
            if 'gallery' in venue.lower() or re.search(r'\bexhibition\b', title_to_use, re.I):
                category = ['Exhibitions']
            elif re.search(r'\b(workshop|masterclass)\b', title_to_use, re.I):
                category = ['Conferences/Workshops/Expos']
            else:
                category = ['Music'] if re.search(r'\b(music|concert|gig|jazz|live|interplay)\b', title_to_use + ' ' + text[:300], re.I) else categorise_event(title_to_use)
            key = (title_to_use.casefold(), start.isoformat(), venue.casefold())
            if key in seen:
                continue
            seen.add(key)
            events.append({'title': title_to_use, 'venue': venue, 'date': start.isoformat(timespec='seconds'),
                           'end_date': end.isoformat(timespec='seconds') if end else '',
                           'category': category, 'image': image, 'url': event_url})
    print(f'    Nexus Arts: {len(events)} verified dated events')
    return events


# ============================================================
# DOM POLSKI CENTRE — Squarespace Events
# ============================================================

def parse_dom_polski_centre(soup, source_url):
    """Discover official event pages and verify dates before adding records.

    Supports Squarespace event collections with /whats-on/<slug> links,
    machine-readable <time> attributes, and event date-range displays.
    """
    from datetime import date as _date
    from urllib.parse import urlparse
    from html import unescape

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    base = source_url.rstrip('/') + '/'
    host = urlparse(base).netloc.removeprefix('www.')
    candidates = {}
    for anchor in soup.find_all('a', href=True):
        link = urljoin(base, anchor.get('href', '')).split('#')[0].split('?')[0].rstrip('/')
        parsed = urlparse(link)
        if parsed.netloc.removeprefix('www.') != host:
            continue
        path = parsed.path.strip('/').split('/')
        if len(path) != 2 or path[0] != 'whats-on' or not path[1]:
            continue
        if path[1] in ('calendar', 'events', 'archive', 'page'):
            continue
        candidates.setdefault(link, ' '.join(anchor.stripped_strings).strip())

    print(f'    Dom Polski Centre: {len(candidates)} candidate event links')
    events = []
    failed = 0

    def metadata(page, name):
        tag = page.find('meta', attrs={'property': name}) or page.find('meta', attrs={'name': name})
        return str(tag.get('content', '')).strip() if tag else ''

    def iso_datetime(raw):
        raw = str(raw or '').strip()
        match = re.match(r'^(20\d{2}-\d{2}-\d{2})(?:[T ](\d{2}:\d{2})(?::(\d{2}))?)?', raw)
        if not match:
            return ''
        try:
            dt = datetime.strptime(match.group(1), '%Y-%m-%d')
            if match.group(2):
                return f'{dt.date().isoformat()}T{match.group(2)}:{match.group(3) or "00"}'
            return f'{dt.date().isoformat()}T00:00:00'
        except ValueError:
            return ''

    def visible_dates(text):
        """Only use dates explicitly showing a four-digit year."""
        months = r'Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?'
        found = []
        for match in re.finditer(rf'\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*,?\s*(\d{{1,2}})\s+({months})\s*,?\s*(20\d{{2}})\b', text, re.I):
            try:
                month = match.group(2)[:3].lower()
                number = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}[month]
                day = datetime(int(match.group(3)), number, int(match.group(1)))
                found.append(day.isoformat() + 'T00:00:00')
            except (ValueError, KeyError):
                pass
        return found

    def image_for(page, url):
        for candidate in [metadata(page, 'og:image'), metadata(page, 'twitter:image')]:
            if candidate and not any(x in candidate.lower() for x in ('favicon', 'logo', 'placeholder')):
                return urljoin(url, candidate)
        for element in page.select('article img, .eventitem img, .event-image img'):
            raw = element.get('data-src') or element.get('src') or ''
            if raw and not raw.startswith('data:'):
                return urljoin(url, raw)
        return ''

    for link, card_title in list(candidates.items())[:100]:
        try:
            response = session.get(link, timeout=25)
            response.raise_for_status()
            page = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as exc:
            failed += 1
            print(f'    Dom Polski Centre: page unavailable {link}: {exc}')
            continue

        main = page.select_one('article.eventitem, article, .eventitem, main, #page') or page
        heading = main.find('h1') or page.find('h1')
        title = ' '.join(heading.stripped_strings).strip() if heading else ''
        if not title:
            title = metadata(page, 'og:title').split(' | ')[0].strip() or card_title
        title = unescape(title)
        if not title:
            continue

        start = end = ''
        # Prefer Squarespace's event-specific structured metadata.
        for script in page.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            queue = [data]
            while queue:
                item = queue.pop()
                if isinstance(item, list):
                    queue.extend(item)
                elif isinstance(item, dict):
                    queue.extend(x for k, x in item.items() if k in ('@graph', 'mainEntity', 'itemListElement') and isinstance(x, (list, dict)))
                    types = item.get('@type', [])
                    types = types if isinstance(types, list) else [types]
                    if 'Event' in types:
                        start = iso_datetime(item.get('startDate')) or start
                        end = iso_datetime(item.get('endDate')) or end
        if not start:
            for element in main.select('time[datetime], [itemprop="startDate"][content], .eventitem-meta-date time'):
                start = iso_datetime(element.get('datetime') or element.get('content'))
                if start:
                    break
        # Squarespace stores event timestamps in <time class="event-date"> and
        # uses <time> elements for start and end of multi-day events.
        if not start:
            for element in main.select('[data-start-date], [data-start], [data-event-start-date]'):
                start = iso_datetime(element.get('data-start-date') or element.get('data-start') or element.get('data-event-start-date'))
                if start:
                    break
        text = ' '.join(main.stripped_strings)
        if not start:
            dates = visible_dates(text[:1400])
            if dates:
                start = dates[0]
                if len(dates) > 1 and dates[1] > start:
                    end = dates[1]
        if not start:
            continue
        # Reject past events only after checking an explicit end date.
        if (end or start)[:10] < _date.today().isoformat():
            continue
        if end and end[:10] < start[:10]:
            end = ''
        # If structured data didn't provide a range, inspect explicitly
        # labelled end-date time elements, never infer from unrelated text.
        if not end:
            for element in main.select('[itemprop="endDate"], time.eventitem-meta-date-end'):
                end = iso_datetime(element.get('datetime') or element.get('content'))
                if end:
                    break
        if end and end[:10] < start[:10]:
            end = ''
        lower = title.casefold()
        if 'boxing' in lower or 'championship' in lower:
            category = ['Sport']
        elif 'dance' in lower or 'swing' in lower:
            category = ['Dance']
        elif 'meeting' in lower or 'club night' in lower:
            category = ['Community']
        else:
            category = categorise_event(title, text[:350])
        events.append({'title': title, 'venue': 'Dom Polski Centre',
                       'date': start, 'end_date': end, 'category': category,
                       'image': image_for(page, link), 'url': link})

    print(f'    Dom Polski Centre: {len(events)} verified dated events; {failed} inaccessible pages')
    return events


# ============================================================
# KINGS OF COMEDY — ADELAIDE ONLY
# ============================================================

def parse_kings_of_comedy(soup, source_url):
    """Discover booking links, accept only independently dated Adelaide shows.

    This parser deliberately does not fabricate weekly dates from promotional
    text. Eventbrite or official event pages must expose actual Event metadata.
    """
    from urllib.parse import urlparse, urlunparse
    from datetime import timezone

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/140.0.0.0 Safari/537.36",
    })
    now = datetime.now().date()
    links = []
    seen_links = set()

    def add_link(value):
        if not value:
            return
        link = urljoin(source_url, str(value).strip())
        parsed = urlparse(link)
        host = (parsed.hostname or "").casefold()
        path = parsed.path.casefold()
        if not (host == "eventbrite.com" or host.endswith(".eventbrite.com")
                or host == "eventbrite.com.au" or host.endswith(".eventbrite.com.au")
                or host in ("koc.lol", "www.koc.lol")):
            return
        if host in ("koc.lol", "www.koc.lol") and not any(
                word in path for word in ("/event", "/show", "/comedy-club-adelaide")):
            return
        if host in ("koc.lol", "www.koc.lol") and path.rstrip("/") == urlparse(source_url).path.rstrip("/").casefold():
            return
        # Keep booking parameters only where needed; remove fragment.
        link = urlunparse(parsed._replace(fragment=""))
        key = link.split("?", 1)[0].rstrip("/").casefold()
        if key not in seen_links:
            seen_links.add(key)
            links.append(link)

    for anchor in soup.find_all("a", href=True):
        add_link(anchor.get("href"))
    for element in soup.select("[data-url], [data-href]"):
        add_link(element.get("data-url") or element.get("data-href"))
    for match in re.findall(r'https?[^\s"\'<>]+', str(soup)):
        if "eventbrite" in match.casefold():
            add_link(match.replace("&amp;", "&"))

    print(f"    Kings of Comedy: {len(links)} candidate booking/event links")
    events = []
    failures = 0
    rejected = 0
    for link in links[:70]:
        try:
            response = session.get(link, timeout=22)
            response.raise_for_status()
            page = BeautifulSoup(response.text, "lxml")
        except requests.RequestException:
            failures += 1
            continue

        # Event metadata can be nested in @graph or a top-level list.
        objects = []
        def walk(value):
            if isinstance(value, list):
                for entry in value:
                    walk(entry)
            elif isinstance(value, dict):
                types = value.get("@type", [])
                types = [types] if isinstance(types, str) else types
                if any(str(t).casefold().endswith("event") for t in types):
                    objects.append(value)
                if "@graph" in value:
                    walk(value["@graph"])
        for script in page.find_all("script", type="application/ld+json"):
            try:
                walk(json.loads(script.string or script.get_text()))
            except (ValueError, TypeError):
                continue

        for item in objects:
            title = str(item.get("name") or "").strip()
            start = str(item.get("startDate") or "").strip()
            location = item.get("location") or {}
            locations = location if isinstance(location, list) else [location]
            location_texts = []
            venue = ""
            for loc in locations:
                if isinstance(loc, dict):
                    name = str(loc.get("name") or "").strip()
                    address = loc.get("address") or {}
                    address_text = " ".join(str(v) for v in address.values()) if isinstance(address, dict) else str(address)
                    location_texts.append(f"{name} {address_text}")
                    if name and not venue:
                        venue = name
                else:
                    location_texts.append(str(loc))
            location_text = " ".join(location_texts).casefold()
            # Require explicit Adelaide evidence in event location or title;
            # reject other Australian cities and online-only shows.
            if not ("adelaide" in location_text or "south australia" in location_text
                    or " sa 5000" in location_text or "adelaide" in title.casefold()):
                rejected += 1
                continue
            if any(x in location_text for x in ("melbourne", "sydney", "brisbane", "perth wa", "gold coast", "online event")):
                rejected += 1
                continue
            try:
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            except ValueError:
                rejected += 1
                continue
            if start_dt.date() < now or not title:
                rejected += 1
                continue
            end = str(item.get("endDate") or "").strip()
            if end:
                try:
                    datetime.fromisoformat(end.replace("Z", "+00:00"))
                except ValueError:
                    end = ""
            image = item.get("image") or ""
            if isinstance(image, list):
                image = image[0] if image else ""
            if isinstance(image, dict):
                image = image.get("url") or ""
            if not image:
                meta = page.find("meta", property="og:image")
                image = meta.get("content", "") if meta else ""
            events.append({
                "title": title,
                "venue": venue or "Kings of Comedy Adelaide",
                "date": start,
                "end_date": end,
                "category": ["Comedy"],
                "image": urljoin(link, str(image)) if image else "",
                "url": str(item.get("url") or link),
            })
    unique = {}
    for event in events:
        key = (event["title"].casefold(), event["venue"].casefold(), event["date"])
        unique.setdefault(key, event)
    print(f"    Kings of Comedy: {len(unique)} verified Adelaide shows; "
          f"{rejected} excluded/undated; {failures} inaccessible pages")
    if not links:
        print("    Kings of Comedy: no booking links in static HTML; "
              "page may require browser rendering or external ticketing discovery")
    return list(unique.values())


# ============================================================
# ADELAIDE REPERTORY THEATRE — OFFICIAL CURRENT PRODUCTION
# ============================================================

def parse_adelaide_repertory_theatre(soup, source_url):
    """Use the official homepage's CURRENT PRODUCTION only.

    One dated season is represented as a single range event; the published
    session timetable is not used to invent individual performance dates.
    Auditions, old season archives and undated productions are excluded.
    """
    from datetime import date
    from urllib.parse import urljoin

    main = soup.find('main') or soup
    text = ' '.join(main.stripped_strings)
    marker = re.search(r'\bCURRENT\s+PRODUCTION\b', text, re.I)
    if not marker:
        print('    Adelaide Rep: no current-production section found')
        return []
    section = text[marker.end():marker.end()+3200]
    season = re.search(r'\bSeason\s*:\s*(.{0,110})', section, re.I)
    if not season:
        print('    Adelaide Rep: no published season dates')
        return []
    # Accept a *fully specified* day range and year, not a year inferred
    # from the current date or an audition notice.
    dates = re.search(
        r'\b(\d{1,2})\s*[–—-]\s*(\d{1,2})\s+'
        r'(January|February|March|April|May|June|July|August|September|October|November|December)'
        r'\s+(20\d{2})\b', season.group(1), re.I)
    if not dates:
        print('    Adelaide Rep: current production has no verified full date range')
        return []
    months = {m.lower(): i for i, m in enumerate(
        ('January','February','March','April','May','June','July','August',
         'September','October','November','December'), 1)}
    try:
        first = date(int(dates.group(4)), months[dates.group(3).lower()], int(dates.group(1)))
        last = date(int(dates.group(4)), months[dates.group(3).lower()], int(dates.group(2)))
    except ValueError:
        return []
    if last < date.today() or first > last:
        print('    Adelaide Rep: current production already ended or invalid')
        return []

    # The homepage uses an h2 for the current production's name.
    heading = None
    for h in main.find_all(['h1','h2','h3','h4']):
        if 'current production' in h.get_text(' ', strip=True).casefold():
            heading = h.find_next(['h1','h2','h3','h4'])
            break
    if not heading:
        print('    Adelaide Rep: no current production title found')
        return []
    title = heading.get_text(' ', strip=True)
    if not title or title.casefold() in ('current production','2026 season'):
        return []

    image = ''
    # Search nearby preceding poster before title, not unrelated page images.
    for element in heading.find_all_previous('img', limit=4):
        candidate = element.get('data-src') or element.get('src') or ''
        if candidate and not candidate.startswith('data:') and not any(
                x in candidate.lower() for x in ('logo', 'icon', 'avatar')):
            image = urljoin(source_url, candidate)
            break
    if not image:
        meta = soup.find('meta', attrs={'property':'og:image'})
        if meta:
            image = urljoin(source_url, meta.get('content') or '')

    event = {
        'title': title,
        'venue': 'Arts Theatre',
        'date': first.isoformat() + 'T00:00:00',
        'end_date': last.isoformat() + 'T23:59:59',
        'category': ['Theatre'],
        'image': image,
        'url': source_url,
    }
    print(f'    Adelaide Rep: verified {title} ({first} to {last}); 1 production')
    return [event]


# ============================================================
# STATE THEATRE COMPANY SOUTH AUSTRALIA — OFFICIAL SHOW PAGES
# ============================================================


STATE_THEATRE_OFFICIAL_IMAGES = {'An Iliad': 'assets/state-theatre/An-Iliad-Portrait-600x800-c-default.jpg', 'The Dark Matter of Usulal': 'assets/state-theatre/Dark-Matter-of-Usulal-Portrait-600x800-c-default.jpg', 'Summer of the Seventeenth Doll': 'assets/state-theatre/Seventeenth-Doll-Portrait-600x800-c-default.jpg', 'A Guide to Success In the Workplace': 'assets/state-theatre/Success-in-the-Workplace-Portrait-600x800-c-default.jpg', 'Evil Hour': 'assets/state-theatre/Evil-Hour-Portrait-600x800-c-default.jpg', 'Snappy': 'assets/state-theatre/Snappy-Portrait-600x800-c-default.jpg', 'The Bookbinder of Jericho': 'assets/state-theatre/Bookbinder-of-Jericho-Portrait-600x800-c-default.jpg', 'Squid': 'assets/state-theatre/Squid-Portrait-600x800-c-default.jpg'}

def parse_state_theatre_company(soup, source_url):
    """Parse dated production cards from a saved official upcoming-shows page.

    No requests to protected individual pages. Never invent image URLs from
    browser-local downloaded asset paths.
    """
    from datetime import date
    from urllib.parse import urljoin, urlparse

    months = {m[:3].lower(): i for i, m in enumerate(
        ('January','February','March','April','May','June','July','August',
         'September','October','November','December'), 1)}
    pattern = re.compile(
        r"^(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"\s*[–—-]\s*(\d{1,2})\s+"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(20\d{2})$", re.I)
    valid_venues = {
        'Dunstan Playhouse, Adelaide Festival Centre': 'Dunstan Playhouse',
        'Odeon Theatre': 'Odeon Theatre',
        'Main Theatre, Adelaide College of the Arts': 'Main Theatre, Adelaide College of the Arts',
        'Space Theatre, Adelaide Festival Centre': 'Space Theatre',
        'X Space, Adelaide College of the Arts': 'X Space, Adelaide College of the Arts',
    }
    events = []
    seen = set()
    for card in soup.select('a.showsGrid_item[href]'):
        heading = card.select_one('h3.showsGrid_item_title')
        details = card.select_one('.showsGrid_item_dates')
        if not heading or not details:
            continue
        title = heading.get_text(' ', strip=True)
        lines = [x.strip() for x in details.stripped_strings if x.strip()]
        if len(lines) < 2:
            continue
        match = pattern.fullmatch(lines[0])
        if not match:
            print(f'    State Theatre skipped (unrecognised dates): {title}: {lines[0]}')
            continue
        venue = valid_venues.get(lines[1])
        if not venue:
            print(f'    State Theatre skipped (unknown venue): {title}: {lines[1]}')
            continue
        try:
            year = int(match.group(5))
            start = date(year, months[match.group(2).lower()], int(match.group(1)))
            end = date(year, months[match.group(4).lower()], int(match.group(3)))
        except ValueError:
            continue
        if end < date.today() or end < start:
            continue
        link = urljoin(source_url, card['href']).split('#')[0].split('?')[0]
        parsed = urlparse(link)
        if parsed.hostname not in ('statetheatrecompany.com.au','www.statetheatrecompany.com.au') or not re.fullmatch(r'/shows/[^/]+/?', parsed.path):
            continue
        key = (title.casefold(), start.isoformat())
        if key in seen:
            continue
        seen.add(key)
        # Browser-saved image paths are local files, not usable on GitHub Pages.
        # Only accept an explicitly absolute official web image URL.
        image = ''
        img = card.find('img')
        if img:
            for attr in ('data-src','src'):
                candidate = str(img.get(attr) or '')
                if candidate.startswith(('https://','http://')) and 'statetheatrecompany.com.au' in urlparse(candidate).netloc:
                    image = candidate
                    break
        image = STATE_THEATRE_OFFICIAL_IMAGES.get(title, image or 'assets/state-theatre-placeholder.svg')
        events.append({
            'title': title, 'venue': venue,
            'date': start.isoformat() + 'T00:00:00',
            'end_date': end.isoformat() + 'T23:59:59',
            'category': ['Theatre'], 'image': image, 'url': link,
        })
        print(f'    State Theatre: {title} | {start} to {end} | {venue}')
    print(f'    State Theatre: {len(events)} verified upcoming productions from saved official page')
    return events


# ============================================================
# SOUTH AUSTRALIAN MUSEUM - OFFICIAL WHAT'S ON
# ============================================================

def parse_south_australian_museum(soup, source_url):
    """Collect dated Museum events, using their own page dates and artwork."""
    from datetime import date
    from urllib.parse import urlparse

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    urls, seen = [], set()
    for anchor in soup.select('a[href]'):
        url = normalise_url(anchor.get('href'), source_url).split('#')[0].split('?')[0]
        parsed = urlparse(url)
        if parsed.hostname != 'whatson.samuseum.sa.gov.au' or not parsed.path.startswith('/events/'):
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)

    month_pattern = (r'(?:January|February|March|April|May|June|July|August|'
                     r'September|October|November|December|Jan|Feb|Mar|Apr|Jun|'
                     r'Jul|Aug|Sep|Sept|Oct|Nov|Dec)')
    month_numbers = {name.lower(): number for number, name in enumerate(
        ('January', 'February', 'March', 'April', 'May', 'June', 'July',
         'August', 'September', 'October', 'November', 'December'), 1)}
    month_numbers.update({name[:3].lower(): number for name, number in
                          list(month_numbers.items())})
    month_numbers['sept'] = 9

    def as_iso(day, month, year, end=False):
        try:
            return datetime(int(year), month_numbers[month.lower()], int(day),
                            23 if end else 0, 59 if end else 0,
                            59 if end else 0).isoformat()
        except (ValueError, KeyError):
            return ''

    def parse_dates(value):
        """Recognise explicitly dated spans; do not infer missing years."""
        value = ' '.join(str(value or '').replace('\xa0', ' ').replace('–', '-')
                         .replace('—', '-').split())
        m = re.search(rf'\b(\d{{1,2}})\s+({month_pattern})\s+(20\d{{2}})\s*'
                      rf'-\s*(\d{{1,2}})\s+({month_pattern})\s+(20\d{{2}})\b', value, re.I)
        if m:
            d1, mo1, y1, d2, mo2, y2 = m.groups()
            return as_iso(d1, mo1, y1), as_iso(d2, mo2, y2, True)
        m = re.search(rf'\b(\d{{1,2}})\s+({month_pattern})\s*-\s*'
                      rf'(\d{{1,2}})\s+({month_pattern})\s+(20\d{{2}})\b', value, re.I)
        if m:
            d1, mo1, d2, mo2, year = m.groups()
            start = as_iso(d1, mo1, year)
            end_year = int(year) + (month_numbers[mo1.lower()] > month_numbers[mo2.lower()])
            return start, as_iso(d2, mo2, end_year, True)
        m = re.search(rf'\b(\d{{1,2}})\s*-\s*(\d{{1,2}})\s+'
                      rf'({month_pattern})\s+(20\d{{2}})\b', value, re.I)
        if m:
            d1, d2, month, year = m.groups()
            return as_iso(d1, month, year), as_iso(d2, month, year, True)
        m = re.search(rf'\b(\d{{1,2}})\s+({month_pattern})\s+(20\d{{2}})\b', value, re.I)
        if m:
            day, month, year = m.groups()
            return as_iso(day, month, year), ''
        m = re.search(rf'\b({month_pattern})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b', value, re.I)
        if m:
            month, day, year = m.groups()
            return as_iso(day, month, year), ''
        return '', ''

    def image_url(value, base):
        value = str(value or '').strip()
        if not value or value.startswith(('data:', 'blob:')):
            return ''
        url = normalise_url(value, base)
        path = urlparse(url).path.lower()
        if not path.endswith(('.jpg', '.jpeg', '.png', '.webp', '.avif')):
            return ''
        if any(bad in path for bad in ('vectors-wrapper', 'logo', 'favicon',
                                       'placeholder', 'icon-', 'sprite', 'arrow',
                                       'payment', 'social-', 'badge', 'brandmark')):
            return ''
        return url

    def event_image(detail, url):
        """Prefer the event's main hero, never the Webflow SVG placeholder."""
        main = detail.find('main') or detail
        candidates = []
        for element in main.find_all(['img', 'source']):
            for attr in ('data-src', 'data-lazy-src', 'data-original', 'src',
                         'data-srcset', 'srcset'):
                raw = element.get(attr)
                if not raw:
                    continue
                # The first srcset entry is usually an actual Webflow image.
                first = str(raw).split(',')[0].strip().split(' ')[0]
                candidate = image_url(first, url)
                if candidate:
                    alt = str(element.get('alt') or '').lower()
                    score = 2 if any(term in alt for term in ('event', 'exhibition', 'poster')) else 0
                    score += 1 if element.find_parent(['header', 'figure', 'picture']) else 0
                    candidates.append((score, candidate))
        for element in main.find_all(attrs={'style': True}):
            match = re.search(r'background-image\s*:\s*url\([\'\"]?([^\'\")]+)',
                              str(element.get('style')), re.I)
            if match:
                candidate = image_url(match.group(1), url)
                if candidate:
                    candidates.append((1, candidate))
        # Meta images are a fallback; some pages expose a generic SVG there.
        for attr, value in (('property', 'og:image'), ('name', 'twitter:image')):
            meta = detail.find('meta', attrs={attr: value})
            candidate = image_url(meta.get('content'), url) if meta else ''
            if candidate:
                candidates.append((0, candidate))
        return sorted(enumerate(candidates), key=lambda x: (-x[1][0], x[0]))[0][1][1] if candidates else ''

    result = []
    for url in urls:
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as exc:
            print(f'    Museum detail ERROR: {url} -> {exc}')
            continue
        title_tag = detail.title
        title = title_tag.get_text(' ', strip=True).split(' | ')[0].strip() if title_tag else ''
        if not title:
            og = detail.find('meta', attrs={'property': 'og:title'})
            title = str(og.get('content') or '').split(' | ')[0].strip() if og else ''
        if not title or title.lower().startswith(('access guide:', 'professional development for teachers', 'museum in a box')):
            continue

        main = detail.find('main') or detail
        page_text = ' '.join(main.get_text(' ', strip=True).split())
        start, end = '', ''
        # The page's labelled Dates field is more authoritative than an
        # unrelated offer, a footer date, or a news item.
        labelled = re.search(r'\b(?:Exhibition details\s+)?Dates?\s*:\s*(.{0,160})',
                             page_text, re.I)
        if labelled:
            start, end = parse_dates(labelled.group(1))
        if not start:
            for item in parse_json_ld(detail, url):
                candidate = str(item.get('date') or '')
                if re.fullmatch(r'20\d{2}-\d{2}-\d{2}(?:T.*)?', candidate):
                    start = candidate[:10] + 'T00:00:00'
                    candidate_end = str(item.get('end_date') or '')
                    if re.match(r'20\d{2}-\d{2}-\d{2}', candidate_end):
                        end = candidate_end[:10] + 'T23:59:59'
                    break
        if not start:
            # Search the event introduction only, not navigation/related events.
            start, end = parse_dates(page_text[:1400])
        if not start:
            print(f'    Museum skipped (no confirmed dated event): {title}')
            continue
        if end and end[:10] < start[:10]:
            end = ''
        if (end or start)[:10] < date.today().isoformat():
            continue
        # Nonconsecutive dates (e.g. tours on 3 and 7 November) must not
        # become a continuous 3-7 November exhibition. Keep a single
        # verified occurrence rather than inventing an uninterrupted range.
        image = event_image(detail, url)
        if not image:
            print(f'    Museum no event artwork found: {title}')
        lower = title.lower()
        if 'exhibition' in lower or 'on display' in page_text[:350].lower():
            category = ['Exhibitions']
        elif 'tour' in lower:
            category = ['Talks']
        elif 'conference' in lower:
            category = ['Conferences/Workshops/Expos']
        elif 'on the terrace' in lower or 'concert' in lower:
            category = ['Music']
        else:
            category = ['Other']
        result.append({'title': title, 'venue': 'South Australian Museum',
                       'date': start, 'end_date': end, 'category': category,
                       'image': image, 'url': url})
    print(f'    South Australian Museum: {len(urls)} detail links, {len(result)} verified dated events')
    return result


# ============================================================
# ART GALLERY OF SOUTH AUSTRALIA (AGSA)
# ============================================================

def parse_art_gallery_south_australia(soup, source_url):
    """Read AGSA's official AJAX calendar; never infer dates for undated items."""
    import calendar
    import html as html_lib
    from datetime import date, datetime, timedelta

    page_html = html_lib.unescape(str(soup))
    token_match = re.search(r"csrfToken\s*:\s*['\"]([^'\"]+)", page_html)
    if not token_match:
        raise RuntimeError("AGSA calendar CSRF token not found")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"})
    # A fresh GET establishes the CSRF cookie required by Django.
    response = session.get(source_url, timeout=30)
    response.raise_for_status()
    token_match = re.search(r"csrfToken\s*:\s*['\"]([^'\"]+)", html_lib.unescape(response.text))
    if not token_match:
        raise RuntimeError("AGSA calendar CSRF token missing from live page")
    token = token_match.group(1)
    response = session.post(
        urljoin(source_url, "/calendar-api/events/"),
        data={"csrfmiddlewaretoken": token, "date_range": "anytime", "event_category": ""},
        headers={"Referer": source_url, "Origin": "https://www.agsa.sa.gov.au", "X-Requested-With": "XMLHttpRequest"},
        timeout=40,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success") or not isinstance(payload.get("html"), str):
        raise RuntimeError("AGSA calendar returned no valid event HTML")
    return parse_agsa_calendar_html(payload["html"])


def parse_agsa_calendar_html(calendar_html, today=None):
    """Parse the actual HTML returned by AGSA's calendar API.

    Keeps separate dated activities; expands explicit weekly recurrence only.
    Undated, daily and ongoing listings are skipped rather than guessed.
    """
    from datetime import date, datetime, timedelta

    today = today or date.today()
    soup = BeautifulSoup(calendar_html, "lxml")
    months = {m.lower(): i for i, m in enumerate(
        ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    ) if m}
    month_pattern = r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec"
    date_pattern = re.compile(r"(\d{1,2})\s+(" + month_pattern + r")[a-z]*\s*(20\d{2})?", re.I)
    weekday_names = {name.lower(): idx for idx, name in enumerate(
        ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    )}

    def parse_dates(label):
        label = re.sub(r"\s+", " ", label).strip()
        matches = list(date_pattern.finditer(label))
        if not matches:
            return []
        year_hint = next((int(m.group(3)) for m in matches if m.group(3)), None)
        if not year_hint:
            return []
        parsed = []
        for idx, match in enumerate(matches[:2]):
            day, month = int(match.group(1)), months[match.group(2)[:3].lower()]
            year = int(match.group(3)) if match.group(3) else year_hint
            # A range such as '15 May - 28 Feb 2027' starts the previous year.
            if idx == 0 and not match.group(3) and len(matches) > 1:
                last = matches[1]
                if (month, day) > (months[last.group(2)[:3].lower()], int(last.group(1))):
                    year -= 1
            try:
                parsed.append(date(year, month, day))
            except ValueError:
                return []
        if len(parsed) == 2 and parsed[1] < parsed[0]:
            return []
        recurring = re.search(r"\bEvery\s+(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b", label, re.I)
        if recurring and len(parsed) == 2:
            weekday = weekday_names[recurring.group(1).lower()]
            current = parsed[0] + timedelta(days=(weekday - parsed[0].weekday()) % 7)
            result = []
            while current <= parsed[1] and len(result) < 120:
                if current >= today:
                    result.append((current, None))
                current += timedelta(days=7)
            return result
        if len(parsed) == 2:
            if parsed[1] < today:
                return []
            # One record for a date-span exhibition, not a record every day.
            return [(max(parsed[0], today), parsed[1])]
        return [(parsed[0], None)] if parsed[0] >= today else []

    events = []
    seen = set()
    skipped = []
    cards = soup.select("li.events-list__item")
    if not cards:
        raise RuntimeError("AGSA API response contained no event cards")
    for card in cards:
        title_node = card.select_one(".page-promo__title")
        anchor = card.select_one("a.page-promo__link[href]")
        if not title_node or not anchor:
            continue
        title = title_node.get_text(" ", strip=True)
        date_node = card.select_one(".page-promo__data.human-date")
        date_label = date_node.get_text(" ", strip=True) if date_node else ""
        dates = parse_dates(date_label)
        if not dates:
            skipped.append((title, date_label))
            continue
        url = urljoin("https://www.agsa.sa.gov.au", anchor["href"])
        image_node = card.select_one(".page-promo__thumb img")
        image = ""
        if image_node:
            image = image_node.get("data-src", "")
            if not image:
                srcset = image_node.get("data-srcset", "")
                if srcset:
                    image = srcset.strip().split()[0]
            if image.startswith("data:"):
                image = ""
        label_node = card.select_one(".page-promo__pre-title")
        label = label_node.get_text(" ", strip=True) if label_node else ""
        categories = categorise_event(title, label)
        if "Exhibition" in label:
            categories = ["Arts & Culture"]
        elif "Talks" in label:
            categories = ["Talks & Conferences"]
        elif "Kids" in label:
            categories = ["Family"] + [c for c in categories if c != "Family"]
        elif "Workshop" in label:
            categories = ["Workshop"] + [c for c in categories if c != "Workshop"]
        elif categories == ["Other"]:
            categories = ["Arts & Culture"]
        for start, end in dates:
            key = (title.casefold(), start.isoformat(), url.rstrip("/"))
            if key in seen:
                continue
            seen.add(key)
            record = {
                "title": title, "venue": "Art Gallery of South Australia",
                "date": start.isoformat() + "T00:00:00",
                "category": categories, "image": image, "url": url,
            }
            if end and end > start:
                record["end_date"] = end.isoformat() + "T23:59:59"
            events.append(record)
    print(f"    AGSA API: {len(cards)} listings, {len(events)} dated records, {len(skipped)} undated/past listings skipped")
    return events


# ============================================================
# BOTANIC GARDENS OF SOUTH AUSTRALIA
# ============================================================

def parse_adelaide_botanic_gardens(soup, source_url):
    """Read official What's On cards; preserve date ranges and real artwork."""
    from datetime import date
    from urllib.parse import urlparse

    results = []
    seen = set()
    today = date.today()
    for heading in soup.select("h3"):
        anchor = heading.find_parent("a", href=True)
        if not anchor:
            continue
        url = normalise_url(anchor.get("href"), source_url).split("#", 1)[0]
        path = urlparse(url).path.rstrip("/")
        if not path.startswith("/whats-on/") or path == "/whats-on" or url in seen:
            continue
        # The event card's main wrapper contains its title, calendar and picture.
        card = heading
        for _ in range(5):
            if card.parent is None:
                break
            card = card.parent
            if card.select_one('img[alt="Calendar icon"]'):
                break
        calendar_icon = card.select_one('img[alt="Calendar icon"]')
        if not calendar_icon:
            continue
        calendar_row = calendar_icon.find_parent("div", class_=lambda c: c and "flex" in c)
        if not calendar_row:
            continue
        dates_text = " ".join(calendar_row.stripped_strings)
        matches = list(re.finditer(r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\s+(20\d{2})\b", dates_text, re.I))
        if not matches:
            continue
        def as_iso(match):
            value = parse_date_text(match.group(0))
            return value[:10] if value else ""
        start = as_iso(matches[0])
        end = as_iso(matches[1]) if len(matches) > 1 else ""
        if not start or (end or start) < today.isoformat():
            continue
        title = " ".join(heading.stripped_strings)
        if not title:
            continue
        # Find the card's original image URL in its responsive source srcset.
        image = ""
        picture = card.select_one("picture")
        if picture:
            for source in picture.select("source[srcset]"):
                srcset = source.get("srcset", "")
                candidate = srcset.split(",", 1)[0].strip().split(" ", 1)[0]
                if candidate.startswith("http"):
                    image = candidate
                    break
        if not image:
            img = card.select_one("img[src^='https://']")
            if img:
                image = img.get("src", "")
        # Prefer the venue label over the umbrella source name.
        venue = "Adelaide Botanic Garden"
        for label in ("Mount Lofty", "Wittunga", "Botanic Park", "Adelaide"):
            if label.lower() in title.lower() or label.lower() in card.get_text(" ", strip=True)[:100]:
                venue = {"Mount Lofty":"Mount Lofty Botanic Garden", "Wittunga":"Wittunga Botanic Garden", "Botanic Park":"Botanic Park", "Adelaide":"Adelaide Botanic Garden"}[label]
                break
        category = categorise_event(title)
        if category == ["Other"]:
            category = ["Arts & Culture"] if any(x in title.lower() for x in ("photograph", "exhibition", "art")) else ["Community"]
        seen.add(url)
        results.append({"title":title,"venue":venue,"date":start+"T00:00:00",
                        "end_date":end+"T23:59:59" if end and end > start else "",
                        "category":category,"image":image,"url":url})
    print(f"    Botanic Gardens: {len(seen)} verified dated event cards")
    return results


# ============================================================
# ADELAIDE CONTEMPORARY EXPERIMENTAL (ACE GALLERY)
# ============================================================

def parse_ace_gallery(soup, source_url):
    """Collect verified, dated ACE exhibitions and live programs.

    Discover official detail pages, then read the displayed When/date range.
    Return [] on failure; existing records are protected by scrape.py.
    """
    from datetime import date
    from urllib.parse import urlparse
    from concurrent.futures import ThreadPoolExecutor, as_completed

    base = "https://ace.gallery/"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; AdelaideEvents/1.0)"})
    links = set()
    listing_pages = [soup]
    for path in ("whats-on", "whats-on/exhibitions", "whats-on/live-programs"):
        try:
            response = session.get(urljoin(base, path), timeout=20)
            response.raise_for_status()
            listing_pages.append(BeautifulSoup(response.text, "lxml"))
        except requests.RequestException as exc:
            print(f"    ACE listing {path}: {exc}")

    for listing in listing_pages:
        for anchor in listing.select("a[href]"):
            link = urljoin(base, anchor.get("href", "")).split("#")[0].split("?")[0].rstrip("/")
            parsed = urlparse(link)
            if parsed.hostname not in ("ace.gallery", "www.ace.gallery"):
                continue
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 3 and parts[0] == "whats-on" and parts[1] in ("exhibitions", "live-programs") and parts[2]:
                links.add(link)

    print(f"    ACE: {len(links)} official detail links discovered")
    months = {name.lower(): i for i, name in enumerate(
        ("January", "February", "March", "April", "May", "June",
         "July", "August", "September", "October", "November", "December"), 1)}
    month_pattern = "|".join(months)
    date_pattern = re.compile(
        rf"\b(\d{{1,2}})\s+({month_pattern})\s*(?:20\d{{2}})?"
        rf"(?:\s*(?:-|–|—|to)\s*(\d{{1,2}})\s+({month_pattern})\s*(20\d{{2}}))?", re.I)
    single_pattern = re.compile(rf"\b(\d{{1,2}})\s+({month_pattern})\s+(20\d{{2}})\b", re.I)
    today = date.today()

    def extract(url):
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            page = BeautifulSoup(response.text, "lxml")
        except requests.RequestException:
            return None
        h1 = page.find("h1")
        title = " ".join(h1.stripped_strings).strip() if h1 else ""
        if not title:
            return None
        # Only the short heading/When area is eligible for dates. Avoid
        # dates embedded in artist biographies, articles or related links.
        main = page.find("main") or page
        text = " ".join(main.stripped_strings)
        when = re.search(r"\bWhen\b", text, re.I)
        candidates = []
        if when:
            candidates.append(text[when.end():when.end()+250])
        candidates.append(text[:min(450, len(text))])
        start = end = None
        for candidate in candidates:
            range_match = date_pattern.search(candidate)
            if range_match and range_match.group(3) and range_match.group(5):
                d1, m1, d2, m2, year = range_match.groups()
                year = int(year)
                try:
                    end = date(year, months[m2.lower()], int(d2))
                    start_year = year - 1 if (months[m1.lower()], int(d1)) > (end.month, end.day) else year
                    start = date(start_year, months[m1.lower()], int(d1))
                    break
                except ValueError:
                    pass
            single = single_pattern.search(candidate)
            if single:
                d, m, y = single.groups()
                try:
                    start = end = date(int(y), months[m.lower()], int(d))
                    break
                except ValueError:
                    pass
        if not start or not end or end < today:
            return None
        image = ""
        for attr, key in (("property", "og:image"), ("name", "twitter:image")):
            meta = page.find("meta", attrs={attr:key})
            if meta and meta.get("content"):
                image = urljoin(url, meta["content"]); break
        if not image:
            image = get_image(main, url)
        if image and ("favicon" in image.lower() or "logo" in image.lower()):
            image = ""
        category = ["Arts & Culture"]
        if "/live-programs/" in url:
            category = categorise_event(title, text[:300])
            if category == ["Other"]:
                category = ["Arts & Culture"]
        # ACE's 'When' block sometimes shows an explicit start time.
        time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b",
                               candidates[0][:140] if candidates else "", re.I)
        hour = minute = 0
        if time_match and start == end:
            hour = int(time_match.group(1)) % 12 + (12 if time_match.group(3).lower() == "pm" else 0)
            minute = int(time_match.group(2) or 0)
        return {"title": title, "venue": "Adelaide Contemporary Experimental (ACE)",
                "date": f"{start.isoformat()}T{hour:02d}:{minute:02d}:00",
                "end_date": end.isoformat()+"T23:59:59" if end > start else "",
                "category": category, "image": image, "url": url}

    events = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(extract, link) for link in sorted(links)]
        for future in as_completed(futures):
            try:
                event = future.result()
                if event:
                    events.append(event)
            except Exception as exc:
                print(f"    ACE detail warning: {exc}")
    events.sort(key=lambda e: (e["date"], e["title"]))
    print(f"    ACE: {len(events)} verified current/future events")
    return events


# ============================================================
# FEVER CANDLELIGHT ADELAIDE
# ============================================================

def parse_fever_candlelight(soup, source_url):
    """Read Fever's server-rendered ticket selector, with JSON-LD fallback.

    Each bookable performance is unique by plan, start time, and venue;
    ticket zones are not separate performances. The selector's nested level
    tree provides dates and times, avoiding misleading first/last dates and
    recommendations from other plans.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from datetime import datetime
    import json
    import re
    from bs4 import BeautifulSoup

    listing = str(soup)
    ids = set(re.findall(r'/m/(\d{4,9})(?!\d)', listing))
    for anchor in soup.select('a[href]'):
        match = re.search(r'/m/(\d{4,9})(?:[/?#]|$)', anchor.get('href', ''))
        if match:
            ids.add(match.group(1))
    print(f'    Fever: {len(ids)} unique event pages discovered')
    if not ids:
        return []

    now = datetime.now().astimezone()

    def read_one(plan_id):
        url = f'https://feverup.com/m/{plan_id}'
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=25)
            response.raise_for_status()
            page = BeautifulSoup(response.text, 'lxml')
        except requests.RequestException as exc:
            return [], f'{plan_id}: {exc}', False

        records = []
        for tag in page.find_all('script', attrs={'type': 'application/ld+json'}):
            try:
                payload = json.loads(tag.string or tag.get_text())
            except (ValueError, TypeError):
                continue
            records.extend(payload if isinstance(payload, list) else [payload])
        details = None
        for record in records:
            if not isinstance(record, dict):
                continue
            kinds = record.get('@type', [])
            if isinstance(kinds, str):
                kinds = [kinds]
            if 'Event' in kinds and 'candlelight' in str(record.get('name', '')).lower():
                details = record
                break
        if not details:
            return [], None, False

        location = details.get('location') or {}
        if isinstance(location, list):
            location = location[0] if location else {}
        venue = str(location.get('name') or '').strip() if isinstance(location, dict) else ''
        address = location.get('address') or {} if isinstance(location, dict) else {}
        locality = str(address.get('addressLocality') or '') if isinstance(address, dict) else ''
        if not venue or (locality and 'adelaide' not in locality.lower()):
            return [], None, False
        title = str(details.get('name') or '').strip()
        image = details.get('image') or ''
        if isinstance(image, dict):
            image = image.get('url') or image.get('contentUrl') or ''
        if isinstance(image, list):
            image = image[0] if image else ''

        def make_event(start_raw, end_raw=''):
            try:
                start = datetime.fromisoformat(str(start_raw).replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return None
            if start.tzinfo is None or start.astimezone() < now:
                return None
            event = {'title': title, 'venue': venue, 'date': start.isoformat(),
                     'category': ['Music'], 'image': str(image), 'url': url}
            try:
                end = datetime.fromisoformat(str(end_raw).replace('Z', '+00:00'))
                if end > start:
                    event['end_date'] = end.isoformat()
            except (ValueError, TypeError):
                pass
            return event

        # This is the plan-specific ticket selector state, not recommendation data.
        selector_found = False
        starts = {}
        state_tag = page.find('script', id='serverapp-state')
        if state_tag:
            try:
                state = json.loads(state_tag.string or state_tag.get_text())
            except (ValueError, TypeError):
                state = {}
            if isinstance(state, dict):
                for key, value in state.items():
                    if not key.startswith('LEVEL_TICKET_SELECTOR_SESSIONS.') or not isinstance(value, dict):
                        continue
                    # Verify that the selector belongs to this exact plan.
                    try:
                        selector_args = json.loads(key.split('LEVEL_TICKET_SELECTOR_SESSIONS.', 1)[1].rstrip('.'))
                    except (ValueError, TypeError):
                        continue
                    if str(selector_args.get('planId')) != str(plan_id):
                        continue
                    selector_found = True

                    def walk(node):
                        if not isinstance(node, dict):
                            return
                        if node.get('type') == 'session':
                            for item in node.get('items') or []:
                                if not isinstance(item, dict):
                                    continue
                                data = item.get('value') or {}
                                if not isinstance(data, dict) or not data.get('has_available_tickets'):
                                    continue
                                if data.get('available_tickets') is not None and data['available_tickets'] <= 0:
                                    continue
                                start_raw = data.get('starts_at_iso')
                                event = make_event(start_raw, data.get('ends_at_iso'))
                                if event:
                                    starts[event['date']] = event
                        for item in node.get('items') or []:
                            if isinstance(item, dict):
                                walk(item.get('level'))
                    walk(value.get('level'))
                    break

        if selector_found:
            return list(starts.values()), None, True
        # Fallback only when Fever does not provide the ticket selector state.
        fallback = make_event(details.get('startDate'), details.get('endDate'))
        return ([fallback] if fallback else []), None, False

    events = []
    failures = 0
    selectors = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(read_one, plan_id) for plan_id in sorted(ids)]
        for future in as_completed(futures):
            found, error, selector_used = future.result()
            if error:
                failures += 1
                print('    Fever warning:', error)
            if selector_used:
                selectors += 1
            events.extend(found)
    events.sort(key=lambda e: (e['date'], e['title'], e['venue']))
    print(f'    Fever: {len(events)} upcoming bookable performances; '
          f'{selectors} ticket selectors; {failures} page errors')
    return events


# ============================================================
# ADELAIDE CENTRAL MARKET — official Events Calendar
# ============================================================

def parse_adelaide_central_market(soup, source_url):
    """Read confirmed upcoming events from the Market's official Tribe Events API.

    Only dated API records are emitted; recurring promotional pages are not
    expanded without independently verified individual occurrence dates.
    """
    from datetime import datetime
    from html import unescape

    api = "https://adelaidecentralmarket.com.au/wp-json/tribe/events/v1/events"
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AdelaideEvents/1.0)"}
    today = datetime.now().date()
    start_date = today.isoformat() + " 00:00:00"
    events = []
    seen = set()
    total_pages = 1
    page = 1

    while page <= min(total_pages, 30):
        try:
            response = requests.get(api, params={
                "start_date": start_date, "per_page": 50, "page": page
            }, headers=headers, timeout=30)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
                raise ValueError("Unexpected Market API response structure")
        except (requests.RequestException, ValueError) as exc:
            print(f"    Market API page {page} unavailable: {exc}")
            # Return no records on a partial API failure to preserve existing
            # records under the scraper's source safety policy.
            return []

        try:
            total_pages = max(1, int(payload.get("total_pages", 1)))
        except (TypeError, ValueError):
            total_pages = 1

        for item in payload["events"]:
            if not isinstance(item, dict):
                continue
            title = unescape(BeautifulSoup(str(item.get("title") or ""), "html.parser").get_text(" ", strip=True))
            date_raw = str(item.get("start_date") or "")
            event_url = str(item.get("url") or "")
            if not title or not event_url:
                continue
            try:
                start = datetime.strptime(date_raw[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if start.date() < today:
                continue
            key = (str(item.get("id") or event_url), start.isoformat())
            if key in seen:
                continue
            seen.add(key)

            description = BeautifulSoup(str(item.get("description") or ""), "html.parser").get_text(" ", strip=True)
            categories = categorise_event(title, description[:500])
            if re.search(r"seafood|cooking|tasting|chef|food|market", title, re.I) and "Food & Beverage" not in categories:
                categories = ["Food & Beverage"] + categories

            image_data = item.get("image")
            image = image_data.get("url", "") if isinstance(image_data, dict) else ""
            if not isinstance(image, str):
                image = ""
            events.append({
                "title": title,
                "venue": "Adelaide Central Market",
                "date": start.isoformat(timespec="seconds"),
                "category": categories,
                "image": image,
                "url": event_url,
                "source": "Adelaide Central Market",
            })
        page += 1

    events.sort(key=lambda e: (e["date"], e["title"]))
    print(f"    Market API: {len(events)} confirmed upcoming events across {page - 1} page(s)")
    return events


# ============================================================
# DAVID ROCHE GALLERY — exhibitions and dated public programmes
# ============================================================

def parse_david_roche_gallery(soup, source_url):
    """Collect confirmed exhibitions and one-off public events from official pages.

    Keep the configured source name for continuity with existing events.json.
    Ordinary recurring Fermoy House tours are deliberately excluded.
    A single exhibition record covers the entire published date range.
    """
    from datetime import date

    root = "https://www.rochegallery.com.au"
    today = datetime.now().date()
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AdelaideEvents/1.0)"}
    events = []
    seen = set()
    errors = 0

    def read(url):
        nonlocal errors
        try:
            response = requests.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as exc:
            errors += 1
            print(f"    Roche warning: {url}: {exc}")
            return None

    def extract_image(page, url):
        tag = page.find("meta", attrs={"property": "og:image"})
        if tag and tag.get("content"):
            return urljoin(url, tag["content"])
        return get_image(page, url) or ""

    def add(title, start, url, category, end=None, page=None):
        if not title or not url or (end or start).date() < today:
            return
        key = (title.casefold().strip(), start.isoformat())
        if key in seen:
            return
        seen.add(key)
        item = {"title": title.strip(), "venue": "David Roche Gallery",
                "date": start.isoformat(timespec="seconds"),
                "category": category, "image": extract_image(page, url) if page else "",
                "url": url, "source": "David Roche Foundation"}
        if end:
            item["end_datetime"] = end.isoformat(timespec="seconds")
        events.append(item)

    def parse_day_month(text, year):
        match = re.search(r"\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\b", text, re.I)
        if not match:
            return None
        try:
            return date(year, MONTHS[match.group(2).lower()], int(match.group(1)))
        except ValueError:
            return None

    # Exhibition landing page provides canonical detail URLs.
    exhibitions_url = root + "/exhibitions/"
    listing = read(exhibitions_url)
    if listing:
        links = sorted({urljoin(exhibitions_url, a.get("href", ""))
                        for a in listing.select('a[href]')
                        if "/exhibitions/" in urljoin(exhibitions_url, a.get("href", ""))
                        and urljoin(exhibitions_url, a.get("href", "")).rstrip("/") != exhibitions_url.rstrip("/")
                        and urljoin(exhibitions_url, a.get("href", "")).startswith(root)})
        for url in links[:30]:
            page = read(url)
            if not page:
                continue
            heading = page.find("h1") or page.find("h2") or page.find("h3")
            title = heading.get_text(" ", strip=True) if heading else ""
            if re.search(r"^(?:future|current|past)?\s*exhibitions?$", title, re.I):
                heading = page.find("h3") or page.find("h2")
                title = heading.get_text(" ", strip=True) if heading else title
            text = page.get_text(" ", strip=True)[:4500]
            # Exhibition dates often omit the start year. Require the end
            # year to appear explicitly on the official calendar before inferring.
            calendar_text = soup.get_text(" ", strip=True) if soup else ""
            range_match = re.search(
                r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s*[–—-]\s*"
                r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})",
                calendar_text, re.I)
            if not range_match:
                continue
            d1, m1, d2, m2, end_year = range_match.groups()
            end_year = int(end_year)
            start_year = end_year - (MONTHS[m1.lower()] > MONTHS[m2.lower()])
            try:
                start = datetime(start_year, MONTHS[m1.lower()], int(d1), 10, 0)
                end = datetime(end_year, MONTHS[m2.lower()], int(d2), 16, 0)
            except ValueError:
                continue
            # Match the exhibition by its dates and title context, not another
            # exhibition that happens to be linked in the archives.
            if (f"{int(d1)} {m1}".lower() not in text.lower()
                    or f"{int(d2)} {m2}".lower() not in text.lower()):
                continue
            if title and not re.search(r"past exhibitions|previous exhibitions|archive", title, re.I):
                add(title, start, url, ["Exhibition"], end, page)

    # Event listing: detail pages give unambiguous dated one-off programmes.
    events_url = root + "/events/"
    event_listing = read(events_url)
    if event_listing:
        urls = sorted({urljoin(events_url, a.get("href", ""))
                       for a in event_listing.select('a[href]')
                       if re.search(r"/events/[^/]+/?$", urljoin(events_url, a.get("href", "")))
                       and urljoin(events_url, a.get("href", "")).rstrip("/") not in
                       (events_url.rstrip("/"), (events_url + "calendar/").rstrip("/"))
                       and urljoin(events_url, a.get("href", "")).startswith(root)})
        for url in urls[:40]:
            page = read(url)
            if not page:
                continue
            heading = page.find("h1") or page.find("h2") or page.find("h3")
            title = heading.get_text(" ", strip=True) if heading else ""
            text = page.get_text(" ", strip=True)[:3500]
            if not title or re.search(r"calendar|fermo[y]? house tour", title, re.I):
                continue
            # Require an explicit 4-digit year on the event page. Otherwise
            # use a month/year heading from the official upcoming calendar.
            explicit = re.search(r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*"
                                 r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b", text, re.I)
            if explicit:
                day, month, year = explicit.groups()
                when = parse_day_month(day + " " + month, int(year))
            else:
                # Calendar headings such as NOVEMBER 2026 must corroborate
                # the date; never infer the year merely from today's date.
                calendar = soup.get_text("\n", strip=True) if soup else ""
                month_year = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(20\d{2})\b", calendar, re.I)
                short = re.search(r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})\s*(?:,|\|)", text, re.I)
                when = (parse_day_month(short.group(1) + " " + month_year.group(1), int(month_year.group(2)))
                        if month_year and short else None)
            if not when:
                continue
            time_match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text, re.I)
            hour, minute = 0, 0
            if time_match:
                hour = int(time_match.group(1)) % 12 + (12 if time_match.group(3).lower() == "pm" else 0)
                minute = int(time_match.group(2) or 0)
            add(title, datetime(when.year, when.month, when.day, hour, minute), url,
                ["Talks"] if re.search(r"lecture|talk|pompeii", title, re.I) else ["Other"], page=page)

    # Do not allow partial failures to replace a healthy existing source.
    if errors:
        print(f"    Roche: {errors} page errors; preserving existing records rather than partial replacement")
        return []
    events.sort(key=lambda item: (item["date"], item["title"]))
    print(f"    Roche: {len(events)} verified upcoming exhibition/event records")
    return events


# ============================================================
# THE GOV — Moshtix venue listings + accessible Oztix records
# ============================================================

def parse_the_gov():
    """Collect only verified events at The Gov, Hindmarsh.

    Oztix's public search HTML is often a JavaScript shell. In that case
    no events are inferred; Moshtix remains a valid independent source.
    """
    from html import unescape
    from urllib.parse import urljoin

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36",
        "Accept-Language": "en-AU,en;q=0.9",
    })
    today = datetime.now().date()
    results = []
    seen = set()
    counters = {"Moshtix": 0, "Oztix": 0}

    def is_gov(location):
        if isinstance(location, list):
            return any(is_gov(x) for x in location)
        if not isinstance(location, dict):
            return False
        name = re.sub(r"[^a-z0-9]+", " ", str(location.get("name", "")).casefold()).strip()
        address = location.get("address") or {}
        if isinstance(address, str):
            street, locality, postcode = address.casefold(), "", ""
        elif isinstance(address, dict):
            street = str(address.get("streetAddress", "")).casefold()
            locality = str(address.get("addressLocality", "")).casefold()
            postcode = str(address.get("postalCode", ""))
        else:
            street, locality, postcode = "", "", ""
        verified_name = name in {
            "the gov", "the gov the venue", "the gov front bar",
            "the gov main room", "governor hindmarsh hotel",
            "the governor hindmarsh", "the governor hindmarsh hotel",
        }
        verified_address = "59 port" in street and ("hindmarsh" in locality or "5007" in postcode or "hindmarsh" in street)
        return verified_name or verified_address

    def objects(value):
        if isinstance(value, list):
            for x in value:
                yield from objects(x)
        elif isinstance(value, dict):
            yield value
            for x in value.values():
                if isinstance(x, (list, dict)):
                    yield from objects(x)

    def add(event, origin, page_url):
        types = event.get("@type", "")
        if isinstance(types, list):
            types = " ".join(types)
        if not any(x in str(types).lower() for x in ("event", "concert")):
            return
        if not is_gov(event.get("location")):
            return
        title = unescape(str(event.get("name", ""))).strip()
        start = str(event.get("startDate", "")).strip()
        if not title or not re.match(r"^20\d{2}-\d{2}-\d{2}", start):
            return
        try:
            if datetime.strptime(start[:10], "%Y-%m-%d").date() < today:
                return
        except ValueError:
            return
        status = str(event.get("eventStatus", "")).casefold()
        if "cancel" in status or "postpon" in status:
            return
        if re.search(r"\b(gift card|gift voucher|membership)\b", title, re.I):
            return
        url = urljoin(page_url, str(event.get("url") or ""))
        if not url.startswith("https://") or not any(host in url for host in ("moshtix.com.au", "oztix.com.au")):
            return
        image = event.get("image") or ""
        if isinstance(image, list):
            image = image[0] if image else ""
        if isinstance(image, dict):
            image = image.get("url", "")
        image = urljoin(page_url, str(image)) if image else ""
        image = re.sub(r"x140x140(?=\D|$)", "x600x600", image, flags=re.I)
        identity = (re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip(), start[:10])
        if identity in seen:
            return
        seen.add(identity)
        results.append({
            "title": title,
            "venue": "The Gov",
            "date": start,
            "end_date": str(event.get("endDate") or ""),
            "category": ["Music"] if "music" in str(types).casefold() else categorise_event(title),
            "image": image,
            "url": url,
        })
        counters[origin] += 1

    def extract(soup, origin, page_url):
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                payload = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            for obj in objects(payload):
                add(obj, origin, page_url)

    moshtix = "https://www.moshtix.com.au/v2/venues/the-gov-adelaide/923"
    try:
        response = session.get(moshtix, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        extract(soup, "Moshtix", moshtix)
        links = sorted({urljoin(moshtix, a.get("href", ""))
                        for a in soup.find_all("a", href=True)
                        if re.search(r"/v2/event/[^/]+/\d+", a.get("href", ""), re.I)})
        # Some venue cards have no JSON-LD, but event detail pages do.
        # Limit detail requests to actual links advertised on this venue page.
        for link in links[:100]:
            try:
                detail = session.get(link, timeout=25)
                if detail.ok:
                    extract(BeautifulSoup(detail.text, "lxml"), "Moshtix", link)
            except requests.RequestException:
                continue
        print(f"    Gov Moshtix: {len(links)} unique venue links, {counters['Moshtix']} verified upcoming events")
    except requests.RequestException as exc:
        print(f"    Gov Moshtix unavailable: {exc}")

    # Oztix's publicly exposed Algolia event-guide search (same service as
    # the official website). Configuration is read from its current JS bundle,
    # not embedded as a permanent key in this project.
    try:
        from urllib.parse import urlparse
        from datetime import timezone, timedelta
        from zoneinfo import ZoneInfo

        homepage = session.get("https://www.oztix.com.au/search/", timeout=30)
        homepage.raise_for_status()
        homepage_soup = BeautifulSoup(homepage.text, "lxml")
        bundle_urls = [urljoin(homepage.url, tag.get("src", ""))
                       for tag in homepage_soup.select("script[src]")
                       if "/js/app." in tag.get("src", "")]
        if not bundle_urls:
            raise ValueError("Oztix app bundle not found")
        bundle = session.get(bundle_urls[0], timeout=35)
        bundle.raise_for_status()
        def public_setting(key):
            found = re.search(r"\b" + re.escape(key) + r':"([^"]+)"', bundle.text)
            if not found:
                raise ValueError("Oztix search setting missing: " + key)
            return found.group(1)
        app_id = public_setting("ALGOLIA_APPLICATION_ID")
        public_key = public_setting("ALGOLIA_PERSONALISATION_API_KEY")
        endpoint = "https://" + app_id.lower() + "-dsn.algolia.net/1/indexes/*/queries"
        headers = {"X-Algolia-Application-Id": app_id,
                   "X-Algolia-API-Key": public_key,
                   "Content-Type": "application/json"}

        # Search by exact verified Oztix venue IDs, rather than the broad
        # keyword "the gov". Both filters were confirmed by live diagnostics.
        # Search every page for each venue independently.
        from urllib.parse import urlencode

        def oztix_query(venue_id, page):
            params = urlencode({"query": "", "filters": f"Venue.Id={venue_id}",
                                "hitsPerPage": 100, "page": page})
            payload = {"requests": [{"indexName": "prod_oztix_eventguide",
                                     "params": params}]}
            response = session.post(endpoint, headers=headers, json=payload, timeout=35)
            response.raise_for_status()
            sections = response.json().get("results", [])
            if not sections:
                raise ValueError(f"Oztix returned no results for venue {venue_id}")
            if sections[0].get("message"):
                raise ValueError(str(sections[0]["message"]))
            return sections[0]

        all_hits = []
        venue_counts = {}
        total_pages = 0
        for venue_id, venue_label in ((2437, "The Venue"),
                                      (4633, "Gibson Stage")):
            first = oztix_query(venue_id, 0)
            count = int(first.get("nbHits", 0))
            pages = int(first.get("nbPages", 0))
            if pages > 40:
                raise ValueError(f"Unexpectedly large Oztix pagination for {venue_label}: {pages}")
            venue_hits = list(first.get("hits", []))
            for page in range(1, pages):
                venue_hits.extend(oztix_query(venue_id, page).get("hits", []))
            if len(venue_hits) < count:
                raise ValueError(f"Incomplete Oztix search for {venue_label}: "
                                 f"{len(venue_hits)} of {count} hits")
            all_hits.extend(venue_hits)
            venue_counts[venue_label] = len(venue_hits)
            total_pages += max(pages, 1)
        print("    Gov Oztix venue search: " + ", ".join(
              f"{label} {count}" for label, count in venue_counts.items()))

        gov_venue_ids = {2437, 4633}  # The Venue and Gibson Stage
        gov_names = {"the gov the venue", "the gov the gibson stage",
                     "the gov", "the gov front bar", "the gov main room"}
        unique_oztix = set()
        rejected = 0
        for hit in all_hits:
            venue = hit.get("Venue") or {}
            if not isinstance(venue, dict):
                rejected += 1
                continue
            venue_name = re.sub(r"[^a-z0-9]+", " ",
                                str(venue.get("Name", "")).casefold()).strip()
            try:
                venue_id = int(venue.get("Id") or 0)
            except (ValueError, TypeError):
                venue_id = 0
            address = str(venue.get("Address", "")).casefold()
            locality = str(venue.get("Locality", "")).casefold()
            postcode = str(venue.get("Postcode", ""))
            at_gov = (venue_id in gov_venue_ids or
                      (venue_name in gov_names and "59 port" in address and
                       ("hindmarsh" in locality or postcode == "5007")))
            if not at_gov or hit.get("IsCancelled") or hit.get("IsPostponed") or hit.get("IsApproved") is False:
                rejected += 1
                continue
            title = unescape(str(hit.get("EventName") or "")).strip()
            if not title or re.search(r"\b(gift card|gift voucher|membership)\b", title, re.I):
                rejected += 1
                continue
            try:
                stamp = int(hit.get("DateStartUnix") or 0)
                if stamp <= 0:
                    rejected += 1
                    continue
                try:
                    local = datetime.fromtimestamp(stamp, timezone.utc).astimezone(ZoneInfo("Australia/Adelaide"))
                except Exception:
                    # Windows Python may lack IANA tzdata. South Australian
                    # DST: first Sunday in October through first Sunday in April.
                    utc = datetime.fromtimestamp(stamp, timezone.utc)
                    year = utc.year
                    def first_sunday(year, month):
                        d = datetime(year, month, 1)
                        return 1 + ((6 - d.weekday()) % 7)
                    dst_start = datetime(year, 10, first_sunday(year, 10), 2)
                    dst_end = datetime(year, 4, first_sunday(year, 4), 3)
                    local_standard = utc + timedelta(hours=9, minutes=30)
                    dst = (local_standard >= dst_start if local_standard.month >= 10 else
                           local_standard < dst_end if local_standard.month <= 4 else False)
                    local = utc + timedelta(hours=10, minutes=30) if dst else local_standard
                if local.date() < today:
                    rejected += 1
                    continue
            except (ValueError, TypeError, OverflowError):
                rejected += 1
                continue
            url = str(hit.get("EventUrl") or "").strip()
            if urlparse(url).hostname not in {"tickets.oztix.com.au", "www.oztix.com.au", "oztix.com.au"}:
                rejected += 1
                continue
            guid = str(hit.get("EventGuid") or hit.get("EventId") or "")
            if not guid or guid in unique_oztix:
                continue
            unique_oztix.add(guid)
            start = local.strftime("%Y-%m-%dT%H:%M:%S")
            identity = (re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip(), start[:10])
            if identity in seen:
                continue
            seen.add(identity)
            categories = [str(x).casefold() for x in (hit.get("Categories") or [])]
            if any("comedy" in x for x in categories):
                category = "Comedy"
            elif any("dance" in x or "dj" in x for x in categories):
                category = "Club/Party"
            else:
                category = "Music"
            results.append({"title": title, "venue": "The Gov", "date": start,
                            "category": category,
                            "image": str(hit.get("EventImage1") or hit.get("HomepageImage") or ""),
                            "url": url})
            counters["Oztix"] += 1
        print(f"    Gov Oztix: {len(all_hits)} search results across {total_pages} venue-filtered page(s); "
              f"{counters['Oztix']} new verified Gov events; {rejected} filtered")
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"    Gov Oztix unavailable: {exc}")

    print(f"    The Gov: {len(results)} unique verified upcoming events")
    return results


# ============================================================
# NORWOOD CONCERT HALL — official event detail pages
# ============================================================

def parse_norwood_concert_hall(soup, source_url):
    """Read official venue listings and their individual verified detail pages.

    Only links under /events/<numeric-id>_ are followed. If detail-page
    verification fails, no event is invented from the listing alone.
    """
    from html import unescape
    from urllib.parse import urlparse

    base_host = urlparse(source_url).hostname
    links = sorted({urljoin(source_url, a.get("href", ""))
                    for a in soup.select("a[href]")
                    if re.search(r"/events/\d+[_/-]", a.get("href", ""), re.I)
                    and urlparse(urljoin(source_url, a.get("href", ""))).hostname == base_host})
    if not links:
        print("    Norwood Concert Hall: no official detail links found")
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    today = datetime.now().date()
    results, seen = [], set()

    def first_meta(page, *selectors):
        for selector in selectors:
            tag = page.select_one(selector)
            if tag:
                value = tag.get("content") or tag.get("src") or ""
                if value.strip():
                    return urljoin(source_url, value.strip())
        return ""

    def category_for(title):
        if re.search(r"\b(comedy|comedian|stand.up|dara|creasey|dollop|des bishop|adam kay|zarna garg|david sedaris)\b", title, re.I):
            return ["Comedy"]
        if re.search(r"\b(psychology|cult|lecture|conversation|talk)\b", title, re.I):
            return ["Talks"]
        if re.search(r"\b(pevan|sarah)\b", title, re.I):
            return ["Family"]
        if re.search(r"\b(drag race|lip sync)\b", title, re.I):
            return ["Theatre"]
        return ["Music"]

    for link in links[:150]:
        try:
            response = session.get(link, timeout=25)
            response.raise_for_status()
            page = BeautifulSoup(response.text, "lxml")
            heading = page.select_one("h1")
            title = unescape(heading.get_text(" ", strip=True) if heading else "").strip()
            if not title or title.casefold() in ("events", "norwood concert hall"):
                continue
            content = page.select_one("main") or page
            text = " ".join(content.stripped_strings)
            # Detail pages publish 'Date: Friday, 20 November 2026' and
            # 'Time: 7:30pm — 9:40pm'. Match the date label, not other dates
            # mentioned in event descriptions or ticket-sale notices.
            date_match = re.search(
                r"\bDate\s*:\s*(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*,?\s*"
                r"(\d{1,2})\s+"
                r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                r"\s+(20\d{2})\b", text, re.I)
            if not date_match:
                continue
            day, month, year = date_match.groups()
            try:
                event_day = datetime.strptime(f"{day} {month} {year}", "%d %B %Y")
            except ValueError:
                continue
            if event_day.date() < today:
                continue
            time_match = re.search(r"\bTime\s*:\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text, re.I)
            if time_match:
                hour, minute, period = time_match.groups()
                hour = int(hour) % 12 + (12 if period.casefold() == "pm" else 0)
                event_day = event_day.replace(hour=hour, minute=int(minute or 0))
            else:
                # A date-only event is valid; midnight means time unknown.
                event_day = event_day.replace(hour=0, minute=0)
            event_date = event_day.strftime("%Y-%m-%dT%H:%M:%S")
            key = (re.sub(r"[^a-z0-9]+", " ", title.casefold()).strip(), event_date)
            if key in seen:
                continue
            seen.add(key)
            image = first_meta(page, 'meta[property="og:image"]', 'meta[name="twitter:image"]')
            # Norwood's official artwork is in /file/resize/... image tags.
            # These may sit outside <main>, and the site logo must not be used.
            official_art = next((urljoin(link, tag.get("data-src") or tag.get("src") or "")
                                 for tag in page.select('img[src], img[data-src]')
                                 if "/file/resize/" in (tag.get("data-src") or tag.get("src") or "").lower()), "")
            if official_art:
                image = official_art
            elif not image:
                image_tag = page.select_one('main img[src], article img[src]')
                if image_tag:
                    candidate = urljoin(link, image_tag.get("data-src") or image_tag.get("src") or "")
                    if not candidate.lower().endswith('logo.svg'):
                        image = candidate
            results.append({"title": title, "venue": "Norwood Concert Hall",
                            "date": event_date, "category": category_for(title),
                            "image": image, "url": link})
        except requests.RequestException as exc:
            print(f"    Norwood detail unavailable: {link} ({exc})")
            continue
    print(f"    Norwood Concert Hall: {len(links)} official detail links, "
          f"{len(results)} verified upcoming events")
    return results


# ============================================================
# TRINITY SESSIONS — official Wix homepage concert listings
# ============================================================

def parse_trinity_sessions(soup, source_url):
    """Read dated concerts from Trinity Sessions' official homepage.

    Each event has a date heading followed by a concert title heading.
    Multiple performances in one date heading become separate records.
    Yearless dates are resolved in homepage order, with New Year rollover.
    Never derive dates from descriptions or from the past-dates archive.
    """
    from html import unescape
    from urllib.parse import urljoin
    from datetime import date

    now = datetime.now().date()
    headings = soup.find_all(["h1", "h2", "h3", "h4"])
    months = {name.lower(): number for number, name in enumerate(
        ["January", "February", "March", "April", "May", "June", "July",
         "August", "September", "October", "November", "December"], 1)}
    weekdays = r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
    month_names = "|".join(name.title() for name in months)
    # Date headings can contain one or several performance dates.
    date_pattern = re.compile(
        rf"\b{weekdays}\s+(\d{{1,2}})\s+({month_names})\b"
        rf"(?:\s+(20\d{{2}}))?"
        rf"(?:\s+(\d{{1,2}})(?::(\d{{2}}))?\s*(am|pm))?", re.I)
    # Some listings use 'Friday and Saturday 25 and 26 September 7.30pm'.
    joint_pattern = re.compile(
        rf"\b{weekdays}\s+and\s+{weekdays}\s+"
        rf"(\d{{1,2}})\s+and\s+(\d{{1,2}})\s+({month_names})\b"
        rf"(?:\s+(20\d{{2}}))?"
        rf"(?:\s+(\d{{1,2}})(?::(\d{{2}}))?\s*(am|pm))?", re.I)
    # Wix commonly prints '7.30pm' rather than '7:30pm'.
    def heading_text(tag):
        return " ".join(unescape(tag.get_text(" ", strip=True)).replace("\xa0", " ").split()).replace("7.30", "7:30")

    def is_date_heading(text):
        return bool(date_pattern.search(text) or joint_pattern.search(text))

    def event_dates(text, previous):
        raw = joint_pattern.search(text)
        entries = []
        if raw:
            first, second, month, explicit, hh, mm, ampm = raw.groups()
            entries = [(int(first), month, explicit, hh, mm, ampm),
                       (int(second), month, explicit, hh, mm, ampm)]
        else:
            entries = [(int(day), month, explicit, hh, mm, ampm)
                       for day, month, explicit, hh, mm, ampm in date_pattern.findall(text)]
        parsed = []
        for day, month, explicit, hh, mm, ampm in entries:
            number = months[month.lower()]
            if explicit:
                year = int(explicit)
            elif previous:
                year = previous.year + (number < previous.month - 6)
            else:
                year = now.year + (number < now.month - 6)
            try:
                hour = int(hh) % 12 + (12 if ampm.lower() == "pm" else 0) if hh else 0
                minute = int(mm or 0)
                dt = datetime(year, number, day, hour, minute)
            except ValueError:
                continue
            parsed.append(dt)
            previous = dt.date()
        return parsed, previous

    events, seen = [], set()
    previous = None
    for index, heading in enumerate(headings):
        text = heading_text(heading)
        if not is_date_heading(text):
            continue
        dates, previous = event_dates(text, previous)
        if not dates:
            continue
        # The immediately following heading is the concert name. Do not use
        # body paragraphs (which can mention other artists and old dates).
        if index + 1 >= len(headings):
            continue
        title_heading = headings[index + 1]
        title = heading_text(title_heading)
        if not title or is_date_heading(title) or len(title) > 180:
            continue
        image = ""
        ticket_url = ""
        # Only search content between this title and the next date heading.
        for node in title_heading.next_elements:
            if getattr(node, "name", None) in ("h1", "h2", "h3", "h4") and node is not title_heading:
                if is_date_heading(heading_text(node)):
                    break
            if not getattr(node, "name", None):
                continue
            if node.name == "img" and not image:
                candidate = (node.get("data-src") or node.get("src") or "").strip()
                if candidate and not candidate.startswith("data:") and not any(
                    bad in candidate.lower() for bad in ("logo", "icon", "placeholder")
                ):
                    image = urljoin(source_url, candidate)
            if node.name == "a" and not ticket_url:
                label = node.get_text(" ", strip=True).lower()
                href = (node.get("href") or "").strip()
                if href and ("buy tix" in label or "book" in label or "tickets" in label):
                    ticket_url = urljoin(source_url, href)
        for dt in dates:
            if dt.date() < now:
                continue
            key = (title.casefold(), dt.isoformat())
            if key in seen:
                continue
            seen.add(key)
            events.append({
                "title": title,
                "venue": "Trinity Sessions",
                "date": dt.isoformat(timespec="seconds"),
                "end_date": "",
                "category": ["Music"],
                "image": image,
                "url": ticket_url or source_url,
            })
    print(f"    Trinity Sessions: {len(headings)} headings, "
          f"{len(events)} verified upcoming performances")
    return events

# ============================================================
# MORPHETTVILLE RACECOURSE — OFFICIAL DATED LISTINGS
# ============================================================

def parse_morphettville_racecourse(soup, source_url):
    """Collect dated public race days and public entertainment from official pages.

    Avoid navigation-only links, undated promotional pages and private functions.
    Each race day remains a distinct event. Never invent start times.
    """
    from urllib.parse import urlparse

    base = "https://morphettville.com.au/"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"})
    today = datetime.now().date()
    events = []
    seen = set()
    pages = [(base, soup)]

    for path in ("racing/", "upcoming-events/", "about/race-day-calendar-2/"):
        url = urljoin(base, path)
        try:
            response = session.get(url, timeout=25)
            response.raise_for_status()
            pages.append((url, BeautifulSoup(response.text, "lxml")))
        except requests.RequestException as exc:
            print(f"    Morphettville listing unavailable: {url} ({exc})")

    def tile_date(text):
        value = " ".join(text.split())
        # Race-day cards explicitly display a full year.
        m = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
                      r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                      r"\s+(20\d{2})\b", value, re.I)
        if m:
            try:
                return datetime(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).date().isoformat()
            except ValueError:
                return ""
        # Upcoming Events cards sometimes show '29 Oct - 05 Dec' without a year.
        # Use a rolling year only for a date in the current or next 12 months.
        m = re.search(r"\b(\d{1,2})\s+"
                      r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b", value, re.I)
        if not m:
            return ""
        short = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                 "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
        try:
            candidate = datetime(today.year, short[m.group(2).lower()], int(m.group(1))).date()
            if candidate < today - timedelta(days=45):
                candidate = candidate.replace(year=candidate.year + 1)
            return candidate.isoformat()
        except ValueError:
            return ""

    def end_date(text, start):
        m = re.search(r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
                      r"\s*[-–—]\s*(\d{1,2})\s+"
                      r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b", text, re.I)
        if not m or not start:
            return ""
        short = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                 "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
        try:
            first = datetime.fromisoformat(start).date()
            year = first.year + (short[m.group(2).lower()] < first.month)
            last = datetime(year, short[m.group(2).lower()], int(m.group(1))).date()
            return last.isoformat() if last > first else ""
        except ValueError:
            return ""

    def detail_image(url):
        # Prefer artwork from the actual event detail page, not the site-wide banner.
        if urlparse(url).netloc.lower() not in ("morphettville.com.au", "www.morphettville.com.au"):
            return ""
        try:
            response = session.get(url, timeout=20)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, "lxml")
        except requests.RequestException:
            return ""
        for attr, value in (("property", "og:image"), ("name", "twitter:image")):
            tag = detail.find("meta", attrs={attr: value})
            candidate = str(tag.get("content") or "").strip() if tag else ""
            if candidate and not any(word in candidate.lower() for word in ("logo", "favicon")):
                return urljoin(url, candidate)
        hero = detail.select_one(".hero img[src], .hero__item img[src], article img[src]")
        return urljoin(url, hero.get("src")) if hero else ""

    for page_url, page in pages:
        for tile in page.select("li.tile.block-link"):
            links = [a for a in tile.select("a[href]") if a.get("href")]
            if not links:
                continue
            text = " ".join(tile.stripped_strings).strip()
            if not text:
                continue
            start = tile_date(text)
            if not start:
                continue
            finish = end_date(text, start)
            if (finish or start) < today.isoformat():
                continue
            is_race = False
            link = ""
            for anchor in links:
                candidate = urljoin(page_url, anchor.get("href"))
                if "/feature-race-day/" in candidate.lower():
                    link = candidate
                    is_race = True
                    break
            if not link and "/upcoming-events/" in page_url:
                for anchor in links:
                    candidate = urljoin(page_url, anchor.get("href"))
                    if urlparse(candidate).scheme in ("http", "https") and "#" not in candidate:
                        link = candidate
                        break
            if not link:
                continue
            if is_race:
                title = re.sub(r"^\s*(?:\d{1,2}(?:st|nd|rd|th)?\s+)?"
                               r"(?:January|February|March|April|May|June|July|August|September|October|November|December)?"
                               r"\s*(?:20\d{2})?\s*", "", text, count=1, flags=re.I)
                title = re.sub(r"\s*(?:Read more|Book Now.*)$", "", title, flags=re.I).strip()
                title = re.sub(r"\s*,?\s*(?:October|November|December|January|February|March|April|May|June|July|August|September)\s+\d{1,2}$", "", title, flags=re.I).strip()
                if title.lower().startswith("race day") and len(title) > 35:
                    title = title[:35].strip()
                category = ["Sport"]
            else:
                title = re.sub(r"^\s*\d{1,2}\s+[A-Za-z]{3}\s*[-–—]\s*\d{1,2}\s+[A-Za-z]{3}\s*", "", text).strip()
                title = re.sub(r"^\s*\d{1,2}\s+[A-Za-z]{3}\s*", "", title).strip()
                if not title or title.lower() in ("upcoming events", "read more"):
                    continue
                category = categorise_event(title)
                if category == ["Other"] and "greatest showman" in title.lower():
                    category = ["Theatre"]
            key = (title.casefold(), start, link.rstrip("/").casefold())
            if key in seen:
                continue
            seen.add(key)
            img = ""
            picture = tile.find("img")
            if picture:
                img = urljoin(page_url, picture.get("data-src") or picture.get("src") or "")
            if not img:
                img = detail_image(link)
            events.append({"title": title, "venue": "Morphettville Racecourse",
                           "date": start + "T00:00:00",
                           "end_date": finish + "T23:59:59" if finish else "",
                           "category": category, "image": img, "url": link})
    print(f"    Morphettville: {len(events)} verified dated public listings")
    return events


# ============================================================
# GILLES AT THE GROUNDS - OFFICIAL MARKET CALENDAR
# ============================================================

def parse_gilles_at_the_grounds(soup, source_url):
    """Read the official Market Dates section; one event per dated session.

    The organiser lists month headings followed by day numbers, without years.
    A year is assigned only to dates reasonably close to the current season.
    Times are based on the site's Saturday-night/Sunday-day schedule.
    """
    from bs4 import NavigableString
    from calendar import monthrange

    now = datetime.now().date()
    month_lookup = {name.casefold(): number for name, number in MONTHS.items()}
    month_lookup.update({name[:3].casefold(): number for name, number in MONTHS.items()})
    headings = soup.find_all(re.compile(r"^h[1-6]$"))
    heading = next((h for h in headings if re.search(r"^\s*market\s+dates\s*$", h.get_text(" ", strip=True), re.I)), None)
    if heading is None:
        print("    Gilles: official Market Dates heading not found")
        return []

    # Walk only text nodes after the Market Dates heading, stopping at the
    # application form heading. This avoids past dates in the page footer/PDFs.
    tokens = []
    for node in heading.next_elements:
        if node is heading:
            continue
        if getattr(node, "name", None) in ("h1", "h2", "h3", "h4", "h5", "h6"):
            label = node.get_text(" ", strip=True).casefold()
            if "apply for a stall" in label or "apply for stall" in label:
                break
        if isinstance(node, NavigableString):
            parent = node.parent
            if parent and parent.name in ("script", "style", "noscript"):
                continue
            value = " ".join(str(node).split())
            if value:
                tokens.append(value)
        if len(tokens) > 350:
            break

    # Match month/day tokens, including layouts where month and dates appear
    # in one text node. Do not infer arbitrary dates elsewhere on the page.
    events = []
    seen = set()
    active_month = None
    months_pattern = "|".join(re.escape(m) for m in MONTHS)
    for token in tokens:
        clean = token.strip().strip(":")
        month = month_lookup.get(clean.casefold())
        if month:
            active_month = month
            continue
        if active_month is None:
            continue
        if not re.fullmatch(r"(?:[0-3]?\d(?:st|nd|rd|th)?(?:\s*[,/&-]\s*)?)+", clean, re.I):
            continue
        for day_str in re.findall(r"\b([0-3]?\d)(?:st|nd|rd|th)?\b", clean, re.I):
            day = int(day_str)
            if day < 1 or day > monthrange(now.year, active_month)[1]:
                continue
            try:
                candidate = datetime(now.year, active_month, day).date()
                if candidate < now - timedelta(days=45):
                    candidate = datetime(now.year + 1, active_month, day).date()
            except ValueError:
                continue
            if candidate < now or candidate > now + timedelta(days=400):
                continue
            # Official hours distinguish Saturday night from Sunday daytime.
            if candidate.weekday() == 5:
                start_hour, end_hour = 15, 21
                title = "Gilles at the Grounds Night Market"
            elif candidate.weekday() == 6:
                start_hour, end_hour = 9, 15
                title = "Gilles at the Grounds Market"
            else:
                # Don't invent trading hours for unexpected weekdays.
                print(f"    Gilles: skipped unexpected weekday {candidate.isoformat()}")
                continue
            if candidate.isoformat() in seen:
                continue
            seen.add(candidate.isoformat())
            events.append({
                "title": title,
                "venue": "Adelaide Showground - Old Brick Dairy",
                "date": f"{candidate.isoformat()}T{start_hour:02d}:00:00",
                "end_date": f"{candidate.isoformat()}T{end_hour:02d}:00:00",
                "category": ["Community", "Arts & Culture", "Food & Beverage"],
                "image": "https://gilles.lbcdn.io/uploads/0G6A3766-510x350.jpg",
                "url": source_url,
            })
    print(f"    Gilles at the Grounds: {len(events)} dated market sessions")
    return sorted(events, key=lambda event: event["date"])


# ============================================================
# UNIBAR ADELAIDE - OFFICIAL DATED GIGS
# ============================================================

def parse_unibar_adelaide(soup, source_url):
    """Read the UniBar Wix gig cards; don't invent unlisted start times.

    Each event's date, poster and Moshtix link are inside the same
    comp-lso1f1yj-container. Wix's rendered thumbnail can be tiny, so
    retain its original static media identifier for full-resolution artwork.
    """
    from urllib.parse import urlparse

    today = datetime.now().date()
    events = []
    seen = set()
    for card in soup.select("div.comp-lso1f1yj-container"):
        date_tag = next((tag for tag in card.find_all(re.compile(r"^h[1-6]$"))
                         if re.fullmatch(r"\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}",
                                         tag.get_text(" ", strip=True))), None)
        if date_tag is None:
            continue
        try:
            event_date = datetime.strptime(date_tag.get_text(" ", strip=True), "%d %b %Y").date()
        except ValueError:
            continue
        if event_date < today:
            continue

        ticket = next((a for a in card.find_all("a", href=True)
                       if "moshtix.com.au" in urlparse(a["href"]).netloc.lower()
                       and "/event/" in urlparse(a["href"]).path), None)
        if ticket is None:
            continue
        ticket_url = ticket["href"].strip()
        if (event_date.isoformat(), ticket_url) in seen:
            continue

        # The official Wix card has one primary artist/title paragraph,
        # followed by an optional tour name or support acts paragraph.
        content = card.select_one("div.comp-lso1ex5n-container")
        if content is None:
            continue
        paragraphs = [p.get_text(" ", strip=True) for p in content.find_all("p")]
        paragraphs = [t for t in paragraphs if t and t.casefold() not in
                      ("all ages", "18+", "tickets")]
        if not paragraphs:
            continue
        title = paragraphs[0]
        if len(paragraphs) > 1:
            title += " - " + paragraphs[1]

        poster = card.find("img", src=True)
        image = ""
        if poster is not None:
            original = poster.get("src", "")
            # Wix's media endpoint serves the full original without the
            # thumbnail's /v1/fill/w_49... resize and AVIF conversion.
            match = re.search(r"https://static\.wixstatic\.com/media/([^/?#]+)", original)
            if match:
                image = "https://static.wixstatic.com/media/" + match.group(1)
            elif original.startswith("https://"):
                image = original

        seen.add((event_date.isoformat(), ticket_url))
        events.append({
            "title": title,
            "venue": "UniBar Adelaide",
            "date": event_date.isoformat(),
            "category": ["Music"],
            "image": image,
            "url": ticket_url,
        })
    events.sort(key=lambda e: (e["date"], e["title"]))
    print(f"    UniBar Adelaide: {len(events)} upcoming dated gigs; "
          f"{sum(bool(e['image']) for e in events)} official posters")
    return events


# ============================================================
# ARKABA HOTEL - OFFICIAL WHAT'S ON EVENT CARDS
# ============================================================

def parse_arkaba_hotel(soup, source_url):
    """Parse Arkaba's dated bn_event cards and their original lazy images.

    The site's event cards use h4.event-title, div.time and event links
    containing ?bn_event=. No date/year/time is fabricated: years are
    determined by matching the published weekday and a near-future window.
    A multi-day date RANGE is one event with an end date, not assumed to
    be daily or weekly performances.
    """
    from datetime import date
    from urllib.parse import urlparse, parse_qs

    today = date.today()
    events = []
    seen = set()
    weekday = {"mon": 0, "tue": 1, "wed": 2, "thu": 3,
               "fri": 4, "sat": 5, "sun": 6}
    months = {name[:3].lower(): number for name, number in MONTHS.items()}

    def read_dates(raw):
        text = " ".join(raw.replace("\xa0", " ").split())
        # Example: Sat, 5-19 December; Thu, 1-Sat, 31 October
        pattern = (r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*"
                   r"(\d{1,2})(?:\s*[-–]\s*(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),?\s*)?(\d{1,2}))?"
                   r"\s+([A-Za-z]+)(?:\s+(20\d{2}))?$")
        match = re.match(pattern, text, re.I)
        if not match:
            return None
        dow, day, end_day, month_text, explicit_year = match.groups()
        month = months.get(month_text[:3].lower())
        if not month:
            return None
        years = [int(explicit_year)] if explicit_year else list(range(today.year - 1, today.year + 4))
        candidates = []
        for year in years:
            try:
                start = date(year, month, int(day))
                end = date(year, month, int(end_day)) if end_day else start
            except ValueError:
                continue
            if start.weekday() != weekday[dow.lower()[:3]] or end < start:
                continue
            if end < today:
                continue
            # Prefer nearest upcoming year; don't push an already elapsed
            # date into the following year unless weekday corroborates it.
            candidates.append((start, end))
        return min(candidates, key=lambda item: item[0]) if candidates else None

    for heading in soup.select("h4.event-title"):
        title = " ".join(heading.stripped_strings).strip()
        if not title:
            continue
        # Locate the smallest card containing this heading, its date,
        # official image, and its unique bn_event detail-page link.
        card = heading
        for _ in range(7):
            card = card.parent
            if card is None:
                break
            if len(card.select("h4.event-title")) != 1:
                continue
            if card.select_one("div.time") and any(
                "bn_event=" in str(a.get("href", ""))
                for a in card.find_all("a", href=True)
            ):
                break
        else:
            continue
        if card is None or len(card.select("h4.event-title")) != 1:
            continue
        date_tag = card.select_one("div.time")
        if date_tag is None:
            continue
        span = read_dates(date_tag.get_text(" ", strip=True))
        if not span:
            continue
        start, end = span
        link = ""
        for anchor in card.find_all("a", href=True):
            candidate = normalise_url(anchor["href"], source_url)
            parsed = urlparse(candidate)
            if (parsed.hostname or "").lower().removeprefix("www.") != "arkabahotel.com.au":
                continue
            if parse_qs(parsed.query).get("bn_event"):
                link = candidate
                break
        if not link:
            continue
        key = (link, start.isoformat())
        if key in seen:
            continue

        image = ""
        for img in card.find_all("img"):
            candidate = (img.get("data-src") or img.get("data-lazy-src")
                         or img.get("data-original") or img.get("src") or "").strip()
            if (not candidate or candidate.startswith("data:")
                    or "logo" in candidate.lower()):
                continue
            image = normalise_url(candidate, source_url)
            break

        lower = title.casefold()
        if "melbourne cup" in lower:
            categories = ["Sport", "Food & Beverage"]
        elif any(word in lower for word in ("christmas day", "christmas dinner")):
            categories = ["Food & Beverage"]
        elif "comedy" in lower or "casey rocket" in lower:
            categories = ["Comedy"]
            if "music" in lower:
                categories.append("Music")
        elif "pink pop party" in lower:
            categories = ["Music", "Family"]
        elif "silver style" in lower:
            categories = ["Food & Beverage", "Community"]
        elif "new year" in lower or "party" in lower:
            categories = ["Music", "Club/Party"]
        else:
            categories = ["Music"]

        seen.add(key)
        events.append({
            "title": title,
            "venue": "Arkaba Hotel",
            "date": start.isoformat(),
            "end_date": end.isoformat() if end > start else "",
            "category": categories,
            "image": image,
            "url": link,
        })

    events.sort(key=lambda e: (e["date"], e["title"]))
    print(f"    Arkaba Hotel: {len(events)} dated official event cards; "
          f"{sum(bool(e['image']) for e in events)} official images")
    return events


# ============================================================
# RHINO ROOM - PAGINATED OFFICIAL GIG GUIDE
# ============================================================

def parse_rhino_room(soup, source_url):
    """Read the Rhino Room's own event cards, times, artwork and ticket links."""
    from urllib.parse import urlsplit, urlunsplit

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    today = datetime.now().date()
    found = []
    seen = set()
    seen_pages = set()
    page = 1
    base_url = "https://rhinoroom.com.au/gig-guide/"

    def field(card, selector):
        node = card.select_one(selector)
        return " ".join(node.stripped_strings).strip() if node else ""

    while page <= 25:
        page_url = base_url if page == 1 else f"{base_url}page/{page}/"
        if page > 1:
            try:
                response = session.get(page_url, timeout=30)
                if response.status_code in (404, 410):
                    break
                response.raise_for_status()
                page_soup = BeautifulSoup(response.text, "lxml")
            except Exception as exc:
                print(f"    Rhino Room page {page} unavailable: {exc}")
                break
        else:
            page_soup = soup

        cards = page_soup.select(".events_grid .our_event")
        signature = tuple(card.get("id", "") for card in cards)
        if not cards or signature in seen_pages:
            break
        seen_pages.add(signature)
        count = 0

        for card in cards:
            date_text = field(card, ".datentime .date") or field(card, ".show-dates .showdate")
            start_text = field(card, ".datentime .start_time") or field(card, ".show-dates .start_time")
            if not date_text:
                continue
            try:
                start_day = datetime.strptime(date_text, "%a, %b %d, %Y")
            except ValueError:
                try:
                    start_day = datetime.strptime(date_text, "%A, %B %d, %Y")
                except ValueError:
                    continue
            if start_day.date() < today:
                continue
            start_time = None
            if start_text:
                for fmt in ("%I:%M %p", "%I %p"):
                    try:
                        start_time = datetime.strptime(start_text.strip().upper(), fmt).time()
                        break
                    except ValueError:
                        pass
            start = datetime.combine(start_day.date(), start_time).isoformat() if start_time else start_day.isoformat()

            end = ""
            end_day_text = field(card, ".show-dates .showenddate").lstrip("- ").strip()
            end_time_text = field(card, ".show-dates .end_time").lstrip("- ").strip()
            if end_day_text:
                try:
                    end_day = datetime.strptime(end_day_text, "%a, %b %d, %Y")
                    if end_day.date() >= start_day.date():
                        end_time = None
                        for fmt in ("%I:%M %p", "%I %p"):
                            try:
                                end_time = datetime.strptime(end_time_text.upper(), fmt).time()
                                break
                            except ValueError:
                                pass
                        if end_time and (end_day.date() > start_day.date() or end_time > (start_time or datetime.min.time())):
                            end = datetime.combine(end_day.date(), end_time).isoformat()
                        elif end_day.date() > start_day.date():
                            end = end_day.isoformat()
                except ValueError:
                    pass

            # The card includes both an image link and a separate title link.
            anchors = card.select("a[href]")
            named_links = [a for a in anchors if a.get_text(" ", strip=True)]
            title_anchor = max(named_links, key=lambda a: len(a.get_text(" ", strip=True)), default=None)
            title = " ".join(title_anchor.stripped_strings).strip() if title_anchor else ""
            if not title:
                for selector in (".post-box h2", ".post-box h3", ".post-box h4", ".post-box .title"):
                    title = field(card, selector)
                    if title:
                        break
            if not title:
                continue
            ticket = title_anchor.get("href", "") if title_anchor else ""
            if not ticket and anchors:
                ticket = anchors[0].get("href", "")
            ticket = normalise_url(ticket.strip(), page_url)
            if not ticket:
                continue
            parts = urlsplit(ticket)
            ticket = urlunsplit((parts.scheme, parts.netloc, parts.path.rstrip("/"), parts.query, ""))

            img = card.select_one("img.wp-post-image") or card.select_one("img")
            image = ""
            if img:
                raw = img.get("data-src") or img.get("src") or ""
                if raw and not raw.startswith("data:"):
                    image = normalise_url(raw, page_url)

            venue_text = field(card, ".show-dates .venue") or field(card, ".post-box .venue")
            if not venue_text:
                # The venue label may be an unclassed sibling inside the card.
                text = card.get_text(" ", strip=True).lower()
                venue_text = "Lowlife Basement Bar" if "lowlife basement" in text else "Rhino Room"
            venue = "Lowlife Basement Bar" if "lowlife" in venue_text.lower() else "Rhino Room"
            key = (title.casefold(), start, venue.casefold())
            if key in seen:
                continue
            seen.add(key)
            lower = title.casefold()
            if any(word in lower for word in ("comedy", "comedian", "standup", "stand-up", "open mic", "laugh lab", "jokers", "joke", "showcase", "friendly jordies", "rufus rice", "lucie pohl")):
                category = ["Comedy"]
            elif any(word in lower for word in ("party", "club", "dj", "halloween", "disney")):
                category = ["Club/Party"]
            elif any(word in lower for word in ("live", "band", "music", "tour", "rock")):
                category = ["Music"]
            else:
                category = categorise_event(title)
            found.append({"title": title, "venue": venue, "date": start, "end_date": end,
                          "category": category, "image": image, "url": ticket})
            count += 1
        print(f"    Rhino Room page {page}: {len(cards)} cards, {count} new dated events")
        page += 1

    print(f"    Rhino Room: {len(found)} dated official events; {sum(bool(x['image']) for x in found)} official images")
    return found


# ============================================================
# JIVE — OFFICIAL WEBFLOW WHAT'S ON
# ============================================================
def parse_jive(soup, source_url):
    """Collect official Jive event cards and verified detail-page start times."""
    from urllib.parse import urlparse

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})
    events = []
    seen = set()
    cards = soup.select(".collection-item-4.w-dyn-item")
    if not cards:
        print("    Jive: no official Webflow event cards found; preserving existing events")
        return []

    for card in cards:
        date_el = card.select_one(".event-top h2.headingall")
        artist_el = card.select_one(".event-top .bodycopy.uppercase")
        show_el = card.select_one(".event-bottom h1.headingall")
        link_el = card.select_one('a[href^="/event/"]') or card.select_one('a[href*="jivevenue.com/event/"]')
        if not (date_el and artist_el and link_el):
            continue
        date_text = date_el.get_text(" ", strip=True)
        date = parse_date_text(date_text)
        if not date:
            continue
        artist = " ".join(artist_el.stripped_strings).strip()
        show = " ".join(show_el.stripped_strings).strip() if show_el else ""
        if not artist:
            continue
        title = artist
        if show and show.casefold() not in artist.casefold() and show.casefold() not in ("live music", "live", "club night"):
            title = artist + " – " + show
        event_url = normalise_url(link_el.get("href", ""), source_url)
        if urlparse(event_url).hostname not in ("www.jivevenue.com", "jivevenue.com") or "/event/" not in event_url:
            continue
        if event_url in seen:
            continue
        seen.add(event_url)

        image = ""
        image_el = card.select_one(".event-img-div")
        if image_el:
            match = re.search(r'background-image\s*:\s*url\(\s*[\"\']?([^\"\')]+)', str(image_el.get("style", "")), re.I)
            if match:
                image = normalise_url(match.group(1).strip(), source_url)

        # Detail pages show the exact date/time in h1.headingall.
        try:
            response = session.get(event_url, timeout=20)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, "lxml")
            for heading in detail.select("h1.headingall"):
                detail_text = heading.get_text(" ", strip=True)
                dt_match = re.search(r"\b([A-Za-z]+\s+\d{1,2},\s+20\d{2})\s+(\d{1,2}:\d{2}\s*[AP]M)\b", detail_text, re.I)
                if not dt_match:
                    continue
                try:
                    parsed = datetime.strptime(dt_match.group(1) + " " + dt_match.group(2).upper().replace(" ", ""), "%B %d, %Y %I:%M%p")
                    if parsed.date().isoformat() == date[:10]:
                        date = parsed.isoformat(timespec="seconds")
                        break
                except ValueError:
                    pass
        except requests.RequestException as exc:
            print(f"    Jive detail unavailable for {artist}: {exc}; using verified listing date")

        kind_el = card.select_one(".event-bottom .heading-xs")
        kind = kind_el.get_text(" ", strip=True).casefold() if kind_el else ""
        if "club" in kind or "party" in kind or any(x in title.casefold() for x in ("rave", "halloween party", "dj set")):
            category = ["Club/Party"]
        else:
            category = ["Music"]
        events.append({"title": title, "venue": "Jive", "date": date,
                       "end_date": "", "category": category,
                       "image": image, "url": event_url})

    print(f"    Jive: {len(cards)} official cards; {len(events)} dated events; "
          f"{sum(bool(e['image']) for e in events)} official images; "
          f"{sum(e['date'][11:16] != '00:00' for e in events)} verified start times")
    return events


# ============================================================
# NATIONAL TRUST SOUTH AUSTRALIA - official Explore event cards
# ============================================================

def parse_national_trust_sa(soup, source_url):
    """Read dated SA event cards, never infer recurring session dates.

    Multi-month listings retain the *advertised range* as one event; they do
    not imply that tours operate every day. Live requests use the Explore page
    rather than an old saved snapshot. If the listing changes/returns no cards,
    the main scraper preserves previously collected National Trust records.
    """
    from datetime import date
    from urllib.parse import urlparse

    cards = soup.select('#exploremain .image-text')
    if not cards:
        cards = soup.select('.explore-main .image-text')
    if not cards:
        raise RuntimeError('National Trust Explore: no event cards found (layout changed or listing unavailable)')

    results = []
    seen = set()
    today = date.today().isoformat()
    for card in cards:
        heading = card.select_one('h3 a[href]')
        meta = card.select_one('.explore-meta')
        if not heading or not meta:
            continue
        title = ' '.join(heading.stripped_strings).strip()
        link = normalise_url(heading.get('href'), source_url)
        if not title or '/event/' not in urlparse(link).path:
            continue
        # The state indicator is part of the card itself, not just the URL.
        meta_text = ' '.join(meta.stripped_strings).strip()
        if not re.match(r'^sa\b', meta_text, re.I):
            continue
        dates = re.findall(r'\b\d{1,2}\s+[A-Za-z]+\s+20\d{2}\b', meta_text)
        if not dates:
            continue
        start = parse_date_text(dates[0])
        end = parse_date_text(dates[-1]) if len(dates) > 1 else ''
        if not start:
            continue
        if end and end[:10] < start[:10]:
            continue
        if (end or start)[:10] < today:
            continue
        key = link.split('?', 1)[0].rstrip('/').casefold()
        if key in seen:
            continue
        seen.add(key)

        img = card.select_one('img')
        image = ''
        if img:
            for attr in ('data-src', 'data-lazy-src', 'src'):
                raw = str(img.get(attr) or '').strip()
                if raw and not raw.startswith(('data:', './')):
                    image = normalise_url(raw, source_url)
                    break
        # Edge's "Save as HTML" rewrites images to local _files/ paths.
        # Live requests have absolute URLs or root-relative paths instead.
        if image and urlparse(image).hostname not in ('www.nationaltrust.org.au', 'nationaltrust.org.au'):
            image = ''

        lower = title.casefold()
        if 'carols' in lower or 'sing-along' in lower:
            category = ['Music', 'Family']
        elif 'halloween' in lower or 'fairy' in lower or 'elf picnic' in lower:
            category = ['Family', 'Arts & Culture']
        elif 'tree' in lower and 'christmas' in lower:
            category = ['Arts & Culture', 'Family']
        else:
            category = ['Arts & Culture']

        # Listing cards do not reliably supply a precise site/venue. Keep
        # a truthful organiser label instead of guessing a street address.
        results.append({
            'title': title,
            'venue': 'National Trust South Australia',
            'date': start,
            'end_date': end if end and end[:10] > start[:10] else '',
            'category': category,
            'image': image,
            'url': link,
        })

    if not results:
        raise RuntimeError('National Trust Explore: no upcoming dated SA events; preserving existing records')
    print(f'    National Trust SA: {len(cards)} cards, {len(results)} upcoming dated events')
    return results


# ============================================================
# CARRICK HILL — OFFICIAL WHAT'S ON
# ============================================================

def parse_carrick_hill(soup, source_url):
    """Parse verified dated event cards on Carrick Hill's official listing.

    The card date is a listing/start date, not proof of a recurring
    schedule or an exhibition end date. Do not invent such dates.
    """
    from datetime import date
    from urllib.parse import urlparse

    results = []
    seen = set()
    cards = soup.select('a.event-link[href]')
    today = date.today()

    for card in cards:
        url = normalise_url(card.get('href', ''), source_url)
        parsed = urlparse(url)
        if parsed.hostname not in ('www.carrickhill.sa.gov.au', 'carrickhill.sa.gov.au'):
            continue
        if not parsed.path.startswith('/events/'):
            continue
        url = f'{parsed.scheme}://{parsed.netloc}{parsed.path}'
        if url in seen:
            continue
        seen.add(url)

        heading = card.select_one('.event-name-text')
        title = heading.get_text(' ', strip=True) if heading else ''
        date_parts = [e.get_text(' ', strip=True) for e in card.select('.event-date-wrapper .event-date')]
        if not title or len(date_parts) < 3:
            continue
        try:
            start = datetime(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
        except (ValueError, TypeError):
            continue
        # Cards do not establish the last day of ongoing exhibitions/tours.
        # Skip past starts rather than inventing a future occurrence.
        if start.date() < today:
            continue

        img = card.select_one('img.events-image')
        image = ''
        if img:
            srcset = img.get('srcset') or ''
            if srcset:
                candidates = [part.strip().split()[0] for part in srcset.split(',') if part.strip()]
                if candidates:
                    image = candidates[-1]
            if not image:
                candidate = img.get('src') or ''
                if candidate and not candidate.startswith('./'):
                    image = normalise_url(candidate, source_url)

        lower = title.casefold()
        if 'musketeers' in lower or 'theatre' in lower:
            category = ['Theatre']
        elif 'christmas' in lower or 'halloween' in lower or 'mouse hunt' in lower:
            category = ['Family']
        elif 'sunset sessions' in lower:
            category = ['Music']
        elif 'conversation' in lower or 'world war' in lower:
            category = ['Talks & Conferences']
        elif 'exhibition' in lower or 'tour' in lower:
            category = ['Arts & Culture']
        else:
            category = categorise_event(title)

        results.append({
            'title': title, 'venue': 'Carrick Hill',
            'date': start.strftime('%Y-%m-%dT00:00:00'),
            'end_date': '', 'category': category,
            'image': image, 'url': url,
        })

    print(f'    Carrick Hill: {len(cards)} cards, {len(results)} future dated events')
    if not cards:
        raise RuntimeError('Carrick Hill event cards missing; retaining existing records')
    return results


def parse_jetty_road_glenelg(pages, source_url):
    """Collect confirmed event dates from official Jetty Road Glenelg listing cards.

    Cards show only the first occurrence of recurring events. Further dates
    require detail-page verification and are deliberately not inferred.
    """
    import re
    from datetime import date, datetime
    from urllib.parse import urlparse

    if not isinstance(pages, (list, tuple)):
        pages = [pages]
    results, seen = [], set()
    today = date.today()
    total_cards = 0
    months = {m.lower(): i for i, m in enumerate(
        ('January', 'February', 'March', 'April', 'May', 'June',
         'July', 'August', 'September', 'October', 'November', 'December'), 1)}
    weekdays = ('Monday', 'Tuesday', 'Wednesday', 'Thursday',
                'Friday', 'Saturday', 'Sunday')
    category_map = {
        'sports': ['Sport'], 'kids & family': ['Family'],
        'arts & culture': ['Arts & Culture'], 'libraries': ['Community'],
        'community': ['Community'], 'environment -green living': ['Community'],
    }
    for soup in pages:
        cards = soup.select('.card.card--event')
        total_cards += len(cards)
        for card in cards:
            title_el = card.select_one('a.card__title[href]')
            if not title_el:
                continue
            title = title_el.get_text(' ', strip=True)
            url = normalise_url(title_el.get('href', ''), source_url).split('#')[0]
            parsed_url = urlparse(url)
            if parsed_url.hostname not in ('jettyroadglenelg.com.au', 'www.jettyroadglenelg.com.au'):
                continue
            if not parsed_url.path.startswith('/whats-on/') or not title:
                continue
            vals = [el.get_text(' ', strip=True) for el in card.select('.datalist__value')]
            if not vals:
                continue
            date_text = vals[0]
            # An 'until' date is an end date, not a verified session date.
            if re.search(r'\b(until|through|daily from)\b', date_text, re.I):
                continue
            # The listing's explicit weekday guards against assigning the wrong
            # year to dates that omit it. No guessed recurring sessions.
            match = re.search(r'\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\s+(\d{1,2})\s+([A-Za-z]+)(?:\s+(20\d{2}))?', date_text, re.I)
            if not match:
                continue
            dayname, daystr, monthstr, yearstr = match.groups()
            month = months.get(monthstr.lower())
            if not month:
                continue
            years = [int(yearstr)] if yearstr else [today.year, today.year + 1]
            candidates = []
            for year in years:
                try:
                    d = date(year, month, int(daystr))
                except ValueError:
                    continue
                if d >= today and d.strftime('%A').lower() == dayname.lower():
                    candidates.append(d)
            if not candidates:
                continue
            event_date = min(candidates)
            # Never create duplicates when an event appears on multiple pages.
            key = (url, event_date.isoformat())
            if key in seen:
                continue
            seen.add(key)
            time_text = vals[1] if len(vals) > 1 else ''
            time_match = re.search(r'\b(\d{1,2}):(\d{2})\s*(am|pm)\b', time_text, re.I)
            hour, minute = 0, 0
            if time_match:
                hour = int(time_match.group(1)) % 12 + (12 if time_match.group(3).lower() == 'pm' else 0)
                minute = int(time_match.group(2))
            event_dt = datetime(event_date.year, event_date.month, event_date.day, hour, minute)
            image_el = card.select_one('.card__image img')
            image = ''
            if image_el:
                image = image_el.get('data-src') or ''
                if not image:
                    srcset = image_el.get('data-srcset') or image_el.get('srcset') or ''
                    image = srcset.split(',')[0].strip().split(' ')[0] if srcset else ''
                if not image:
                    image = image_el.get('src') or ''
                if image.startswith('./'):
                    image = ''
                elif image:
                    image = normalise_url(image, source_url)
            tag = card.select_one('.tag__text')
            raw_cat = tag.get_text(' ', strip=True).lower() if tag else ''
            category = category_map.get(raw_cat) or categorise_event(title)
            venue = ''
            if len(vals) > 2:
                candidate = vals[2]
                if candidate.lower() not in ('book now', 'view event details'):
                    venue = candidate
            if not venue:
                venue = 'Jetty Road Glenelg'
            results.append({
                'title': title, 'venue': venue,
                'date': event_dt.strftime('%Y-%m-%dT%H:%M:%S'),
                'end_date': '', 'category': category,
                'image': image, 'url': url,
            })
    print(f'    Jetty Road Glenelg: {total_cards} cards, {len(results)} verified upcoming first dates')
    if total_cards == 0:
        raise RuntimeError('Jetty Road Glenelg cards not found; preserve existing records')
    return results


# ============================================================
# OZTIX — ADELAIDE CBD AND NORTH ADELAIDE ONLY
# ============================================================

def parse_oztix_adelaide_city():
    """Query Oztix's public event-guide index and verify venue postcode.

    A text search alone is not a geographic filter. We search both locality
    names, then accept ONLY venue postcodes 5000/5006 and corresponding
    localities. Never infer a venue from the event title.
    """
    from urllib.parse import urlencode, urlparse
    from datetime import timezone, timedelta, date
    from html import unescape

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"})
    response = session.get("https://www.oztix.com.au/search/", timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    bundles = [urljoin(response.url, x.get("src", "")) for x in soup.select("script[src]")
               if "/js/app." in x.get("src", "")]
    if not bundles:
        raise ValueError("Oztix app bundle not found")
    bundle = session.get(bundles[0], timeout=35)
    bundle.raise_for_status()

    def setting(name):
        match = re.search(r"\b" + re.escape(name) + r':"([^"]+)"', bundle.text)
        if not match:
            raise ValueError("Oztix public search setting missing: " + name)
        return match.group(1)

    app_id = setting("ALGOLIA_APPLICATION_ID")
    api_key = setting("ALGOLIA_PERSONALISATION_API_KEY")
    endpoint = "https://" + app_id.lower() + "-dsn.algolia.net/1/indexes/*/queries"
    headers = {"X-Algolia-Application-Id": app_id,
               "X-Algolia-API-Key": api_key,
               "Content-Type": "application/json"}

    def search(query, page):
        params = urlencode({"query": query, "hitsPerPage": 100, "page": page})
        payload = {"requests": [{"indexName": "prod_oztix_eventguide", "params": params}]}
        r = session.post(endpoint, headers=headers, json=payload, timeout=35)
        r.raise_for_status()
        results = r.json().get("results", [])
        if not results or results[0].get("message"):
            raise ValueError("Oztix search failed: " + str(results[0].get("message") if results else "no results"))
        return results[0]

    hits = {}
    pages_checked = 0
    for query in ("Adelaide", "North Adelaide"):
        first = search(query, 0)
        pages = int(first.get("nbPages", 0))
        if pages > 40:
            raise ValueError(f"Oztix search for {query!r} requires {pages} pages; refusing incomplete pagination")
        for page in range(pages):
            batch = first if page == 0 else search(query, page)
            pages_checked += 1
            for hit in batch.get("hits", []):
                guid = str(hit.get("EventGuid") or hit.get("EventId") or hit.get("objectID") or "")
                if guid:
                    hits[guid] = hit

    def adelaide_local(stamp):
        utc = datetime.fromtimestamp(int(stamp), timezone.utc)
        try:
            from zoneinfo import ZoneInfo
            return utc.astimezone(ZoneInfo("Australia/Adelaide")).replace(tzinfo=None)
        except Exception:
            # Calculate DST using the first Sunday of October and April.
            def first_sunday(y, m):
                return 1 + (6 - datetime(y, m, 1).weekday()) % 7
            local_standard = utc.replace(tzinfo=None) + timedelta(hours=9, minutes=30)
            year = local_standard.year
            start = datetime(year, 10, first_sunday(year, 10), 2)
            end = datetime(year, 4, first_sunday(year, 4), 3)
            dst = local_standard >= start or local_standard < end
            return local_standard + (timedelta(hours=1) if dst else timedelta())

    events = []
    today = date.today()
    rejected_location = 0
    for hit in hits.values():
        venue = hit.get("Venue") or {}
        if not isinstance(venue, dict):
            continue
        postcode = str(venue.get("Postcode") or "").strip()
        locality = re.sub(r"\s+", " ", str(venue.get("Locality") or "")).strip().casefold()
        if postcode not in {"5000", "5006"} or locality not in {"adelaide", "north adelaide"}:
            rejected_location += 1
            continue
        if hit.get("IsCancelled") or hit.get("IsPostponed") or hit.get("IsApproved") is False:
            continue
        title = unescape(str(hit.get("EventName") or "")).strip()
        venue_name = unescape(str(venue.get("Name") or "")).strip()
        if not title or not venue_name or re.search(r"\b(gift card|gift voucher|membership)\b", title, re.I):
            continue
        try:
            local = adelaide_local(hit.get("DateStartUnix"))
        except (ValueError, TypeError, OverflowError, OSError):
            continue
        if local.date() < today:
            continue
        url = str(hit.get("EventUrl") or "").strip()
        if urlparse(url).hostname not in {"tickets.oztix.com.au", "www.oztix.com.au", "oztix.com.au"}:
            continue
        categories = [str(x).casefold() for x in (hit.get("Categories") or [])]
        if any("comedy" in x for x in categories):
            category = ["Comedy"]
        elif any("dance" in x or "dj" in x or "club" in x for x in categories):
            category = ["Club/Party"]
        elif any("theatre" in x for x in categories):
            category = ["Theatre"]
        else:
            category = ["Music"]
        events.append({"title": title, "venue": venue_name,
                       "date": local.strftime("%Y-%m-%dT%H:%M:%S"),
                       "category": category,
                       "image": str(hit.get("EventImage1") or hit.get("HomepageImage") or ""),
                       "url": url})
    print(f"    Oztix City: {pages_checked} search pages, {len(hits)} unique hits; "
          f"{rejected_location} outside CBD/North Adelaide; {len(events)} verified upcoming events")
    return events


# ============================================================
# PLANT 4 BOWDEN - recurring markets, bingo, special events
# ============================================================

def parse_plant_4_bowden():
    """Generate a short rolling window from confirmed venue schedules.

    If the official pages cannot be read, raise rather than publish unverified
    sessions. Special-event pages require an explicit full date and venue.
    """
    from datetime import date, datetime, timedelta
    from urllib.parse import urlparse

    base = "https://www.plant4bowden.com.au"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"}
    session = requests.Session()
    session.headers.update(headers)

    def page(path):
        response = session.get(base + path, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    whats_on = page("/whats-on")
    bingo = page("/bingo")
    market_text = whats_on.get_text(" ", strip=True).lower()
    bingo_text = bingo.get_text(" ", strip=True).lower()
    today = date.today()
    horizon = today + timedelta(days=55)
    events = []
    market_art = _official_event_artwork(whats_on, base + "/whats-on", allow_venue_photo=True)
    bingo_art = _official_event_artwork(bingo, base + "/bingo", allow_venue_photo=True)

    def recurring(title, weekday, hour, minute, categories, link):
        for offset in range((horizon - today).days + 1):
            day = today + timedelta(days=offset)
            if day.weekday() != weekday:
                continue
            events.append({
                "title": title,
                "venue": "Plant 4 Bowden",
                "date": datetime(day.year, day.month, day.day, hour, minute).isoformat(),
                "category": categories,
                "image": bingo_art if link == "/bingo" else market_art,
                "url": base + link,
            })

    # Only generate sessions while the official venue pages explicitly
    # advertise the relevant weekly recurrence.
    if ("night markets" in market_text and "wednesday" in market_text
            and "friday" in market_text and "5:00" in market_text):
        recurring("Plant 4 Bowden Wednesday Night Market", 2, 17, 0,
                  ["Food & Beverage", "Community"], "/whats-on")
        recurring("Plant 4 Bowden Friday Night Market", 4, 17, 0,
                  ["Food & Beverage", "Community"], "/whats-on")
    else:
        print("    Plant 4: weekly markets not confirmed on current website")

    if ("every wednesday" in bingo_text or "weekly on wednesday" in bingo_text) and (
            "7.00pm" in bingo_text or "7:00pm" in bingo_text or "7pm" in bingo_text):
        recurring("Plant 4 Bowden Musical Bingo", 2, 19, 0,
                  ["Music", "Community"], "/bingo")
    else:
        print("    Plant 4: weekly bingo not confirmed on current website")

    # Official special event pages: do not infer missing years or times.
    # Candidate links are discovered from the official venue pages, not
    # guessed from Instagram captions or arbitrary image text.
    links = {base + "/musical-bingo-event"}
    for soup in (whats_on, bingo):
        for anchor in soup.find_all("a", href=True):
            href = urljoin(base, anchor["href"]).split("#")[0]
            parsed = urlparse(href)
            if parsed.hostname not in ("www.plant4bowden.com.au", "plant4bowden.com.au"):
                continue
            path = parsed.path.lower().strip("/")
            if not path or path in {"whats-on", "whatson", "events", "bingo", "booking", "hours", "contact", "home"}:
                continue
            if any(word in path for word in ("event", "festival", "bingo", "quiz", "concert", "show", "music")):
                links.add(base + parsed.path)

    special_count = 0
    for link in sorted(links):
        try:
            response = session.get(link, timeout=20)
            response.raise_for_status()
            detail = BeautifulSoup(response.text, "lxml")
        except requests.RequestException:
            continue
        content = detail.get_text(" ", strip=True)
        # Require explicit day/month/year. No date inference from undated pages.
        match = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+"
                          r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                          r"\s+(20\d{2})\b", content, re.I)
        if not match:
            continue
        try:
            start = datetime(int(match.group(3)), MONTHS[match.group(2).lower()], int(match.group(1)))
        except ValueError:
            continue
        if not today <= start.date() <= horizon:
            continue
        if not re.search(r"plant\s*4\s*bowden", content, re.I):
            continue
        if re.search(r"\b(cancelled|canceled|postponed)\b", content[:600], re.I):
            continue
        # Time must be explicitly stated on the event page.
        time_match = re.search(r"(?:game\s+from|starts?\s+at|from|commences?\s+at)\s*:?\s*"
                               r"(\d{1,2})(?:[:.](\d{2}))?\s*(am|pm)", content, re.I)
        if not time_match:
            continue
        hour = int(time_match.group(1)) % 12 + (12 if time_match.group(3).lower() == "pm" else 0)
        start = start.replace(hour=hour, minute=int(time_match.group(2) or 0))
        heading = detail.find("h1")
        title = heading.get_text(" ", strip=True) if heading else ""
        if not title or len(title) > 120:
            meta = detail.find("meta", property="og:title")
            title = meta.get("content", "") if meta else ""
        if not title or len(title) > 120:
            continue
        # A generic 'Musical Bingo Event' page is specifically the special
        # Boot Scootin' edition, not the regular Wednesday game.
        if urlparse(link).path.rstrip("/") == "/musical-bingo-event":
            title = "Musical Bingo: Boot Scootin' Edition"
        image = _official_event_artwork(detail, link, title)
        events.append({"title": title, "venue": "Plant 4 Bowden",
                       "date": start.isoformat(),
                       "category": ["Music", "Community"] if "bingo" in title.lower() else categorise_event(title),
                       "image": image,
                       "url": link})
        special_count += 1

    # Keep distinct same-day market and bingo sessions; remove exact repeats.
    unique = {}
    for event in events:
        key = (event["title"].casefold(), event["date"])
        unique[key] = event
    result = sorted(unique.values(), key=lambda event: (event["date"], event["title"]))
    print(f"    Plant 4: {len(result) - special_count} recurring sessions, "
          f"{special_count} dated special events, {len(result)} total")
    return result


# ============================================================
# PLANT 3 BOWDEN - Bowden Brewing official recurring activities
# ============================================================

def parse_plant_3_bowden():
    """Fetch the official Bowden Brewing listings; publish a rolling 8 weeks.

    Do not generate an activity unless the live official page confirms it.
    Unpublished starting times are left as midnight placeholders (date only).
    """
    from datetime import date, datetime, timedelta

    root = "https://bowdenbrewing.com"
    listing = root + "/blogs/whats-on"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"})

    def get(url):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    index = get(listing)
    text = index.get_text(" ", strip=True).casefold()
    # Check individual official pages, not unrelated third-party event posts.
    specs = [
        ("Taco Tuesday", 1, 0, 0, ["Food & Beverage"], "/blogs/whats-on/taco-tuesday", ("taco tuesday", "each tuesday")),
        ("Pizza & Pint", 2, 0, 0, ["Food & Beverage"], "/blogs/whats-on/pizza-pint", ("pizza & pint", "wednesday")),
        ("Friday Froths", 4, 17, 0, ["Food & Beverage", "Community"], "/blogs/whats-on/friday-froths", ("friday froths", "every friday")),
        ("Weekly 50 Quiz", 4, 19, 0, ["Community"], "/blogs/whats-on/weekly-50-quiz", ("weekly 50 quiz", "every friday")),
    ]
    today = date.today()
    events = []
    confirmed = []
    for title, weekday, hour, minute, categories, path, clues in specs:
        # A missing page is a source failure, not permission to invent dates.
        detail = get(root + path)
        detail_text = detail.get_text(" ", strip=True).casefold()
        if not all(clue in (text + " " + detail_text) for clue in clues):
            print(f"    Plant 3: unconfirmed schedule skipped: {title}")
            continue
        # Confirm recurrence on the individual page or index.
        day_name = ("tuesday" if weekday == 1 else "wednesday" if weekday == 2 else "friday")
        if day_name not in detail_text and day_name not in text:
            continue
        confirmed.append(title)
        image = ""
        meta = detail.find("meta", attrs={"property": "og:image"})
        if meta:
            candidate = str(meta.get("content", "")).strip()
            if candidate.startswith("http") and not any(x in candidate.casefold() for x in ("logo", "favicon")):
                image = candidate
        for offset in range(56):
            day = today + timedelta(days=offset)
            if day.weekday() != weekday:
                continue
            events.append({
                "title": title, "venue": "Plant 3 Bowden",
                "date": datetime(day.year, day.month, day.day, hour, minute).isoformat(),
                "category": categories, "image": image, "url": root + path,
            })
    print(f"    Plant 3: {len(confirmed)} weekly activities verified; {len(events)} dated sessions")
    return events


# ============================================================
# MOD. (Adelaide) — official events and exhibitions
# ============================================================

def parse_mod_museum():
    """Collect dated MOD. activities without guessing years or daily sessions.

    The official listings occasionally retain old events under 'upcoming'.
    Dates are therefore verified on detail pages, not inferred from cards.
    Exhibitions are one ranged record, not one record per opening day.
    """
    from datetime import date
    from urllib.parse import urlparse

    root = "https://mod.org.au"
    listings = (root + "/whats-on/events/", root + "/whats-on/exhibitions/")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"}
    session = requests.Session()
    session.headers.update(headers)
    today = date.today()
    links = set()
    failed_listings = 0

    def fetch(url):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    for listing in listings:
        try:
            page = fetch(listing)
        except requests.RequestException as exc:
            failed_listings += 1
            print(f"    MOD. listing unavailable: {listing} ({exc})")
            continue
        for a in page.find_all("a", href=True):
            url = urljoin(listing, a["href"]).split("#", 1)[0].split("?", 1)[0]
            parsed = urlparse(url)
            if parsed.netloc.lower() not in ("mod.org.au", "www.mod.org.au"):
                continue
            if re.fullmatch(r"/(?:events|exhibitions)/[^/]+/?", parsed.path, re.I):
                links.add(url.rstrip("/") + "/")

    # This is a currently published exhibition detail page, not an inferred
    # calendar entry. Validate its actual date range before inclusion.
    links.add(root + "/exhibitions/beginnings/")

    def read_date(value):
        value = str(value or "").strip()
        match = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", value)
        if match:
            try:
                return date(*map(int, match.groups()))
            except ValueError:
                return None
        match = re.search(r"\b(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(20\d{2})\b", value, re.I)
        if match:
            months = {"jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,"jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12}
            try:
                return date(int(match.group(3)), months[match.group(2)[:3].lower()], int(match.group(1)))
            except ValueError:
                return None
        return None

    def parse_range(text):
        # '27 Feb - 31 Oct 2026', '13 Jan – 20 Nov 2026'
        m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\s*[-–—]\s*(\d{1,2})\s+([A-Za-z]{3,9})\s+(20\d{2})\b", text)
        if not m:
            return None
        a = read_date(f"{m.group(1)} {m.group(2)} {m.group(5)}")
        b = read_date(f"{m.group(3)} {m.group(4)} {m.group(5)}")
        return (a,b) if a and b and a <= b else None

    def get_metadata(soup, name):
        node = soup.find("meta", attrs={"property":name})
        return str(node.get("content", "")).strip() if node else ""

    events = []
    skipped_past = 0
    skipped_unverified = 0
    page_errors = 0
    for url in sorted(links):
        try:
            soup = fetch(url)
        except requests.RequestException as exc:
            page_errors += 1
            print(f"    MOD. detail unavailable: {url} ({exc})")
            continue
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else ""
        if not title:
            skipped_unverified += 1
            continue
        # Use the main page's event information, not navigation and related
        # event cards. The date/time and location appear directly below h1.
        main = soup.find("main") or soup.find("article") or soup
        heading = main.find("h1")
        section = heading.parent if heading else main
        # Include nearby ancestors so hero metadata is available even when
        # the title and event facts are sibling elements.
        for _ in range(3):
            if section.parent and section.parent is not main:
                section = section.parent
        detail = " ".join(section.stripped_strings)
        # When layout containers are too small, fall back to the main page,
        # but trim before related events to prevent borrowing their dates.
        if len(detail) < 70:
            detail = " ".join(main.stripped_strings)
        detail = re.split(r"\bUpcoming Events\b|\bSee all events\b", detail, maxsplit=1)[0]
        detail = re.split(r"\bPlan your visit\b", detail, maxsplit=1, flags=re.I)[0]
        # Locate the title and inspect the first portion of the event detail.
        idx = detail.find(title)
        if idx >= 0:
            detail = detail[idx + len(title):]
        header = detail[:1100]
        is_exhibition = "/exhibitions/" in url
        span = parse_range(header)
        start = end = None
        if span:
            start, end = span
        else:
            # Explicit year required. MOD. listing cards omit the year and
            # old events sometimes remain published, so never infer it.
            dates = re.findall(r"\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+20\d{2}\b", header, re.I)
            start = read_date(dates[0]) if dates else None
            if is_exhibition and start:
                # A one-day exhibition date is insufficient to assert a run.
                start = None
        if not start:
            skipped_unverified += 1
            continue
        if (end or start) < today:
            skipped_past += 1
            continue

        # Offsite projects are kept at their real venues, not relabelled MOD.
        # A multi-campus project cannot be assigned to one local venue.
        location = "MOD."
        if "beginnings-2100" in url.lower() or re.search(r"Mawson Lakes,? Mount Gambier,? Waite and Whyalla", header, re.I):
            skipped_unverified += 1
            continue
        if re.search(r"\bMOD\. Foyer\b", header, re.I):
            location = "MOD. Foyer"
        elif re.search(r"\bThe Pod Gallery,? MOD\.\b", header, re.I):
            location = "The Pod Gallery, MOD."

        image = get_metadata(soup, "og:image")
        if not image:
            # Prefer first content image near the event title.
            img = section.find("img")
            if img:
                image = img.get("data-src") or img.get("src") or ""
        image = urljoin(url, image) if image and not image.startswith("data:") else ""
        if any(bad in image.lower() for bad in ("favicon", "logo", "placeholder")):
            image = ""
        if is_exhibition:
            category = ["Arts & Culture"]
        else:
            category = categorise_event(title)
            if category == ["Other"]:
                category = ["Talks & Conferences"] if re.search(r"talk|panel|q series|sharing circle|discussion", title, re.I) else ["Arts & Culture"]
        time_match = re.search(r"\b(\d{1,2}):(\d{2})\s*(am|pm)\b", header, re.I)
        clock = "00:00:00"
        if time_match and not is_exhibition:
            hour = int(time_match.group(1)) % 12 + (12 if time_match.group(3).lower() == "pm" else 0)
            clock = f"{hour:02d}:{time_match.group(2)}:00"
        events.append({
            "title": title, "venue": location,
            "date": start.isoformat() + "T" + clock,
            "end_date": end.isoformat() + "T23:59:59" if end and end > start else "",
            "category": category, "image": image, "url": url,
        })

    print(f"    MOD.: {len(links)} detail links, {len(events)} verified current events/exhibitions; "
          f"{skipped_past} past, {skipped_unverified} undated/offsite, "
          f"{page_errors} detail errors")
    if failed_listings == len(listings) and not events:
        raise RuntimeError("Both MOD. listing pages unavailable; preserving existing records")
    return events


# ============================================================
# SAMSTAG MUSEUM OF ART — OFFICIAL ADELAIDE UNIVERSITY WEBSITE
# ============================================================

def parse_samstag_museum():
    """Collect verified, dated exhibitions and events from the official site.

    An exhibition is represented by one start/end range, never a daily event.
    Missing dates are deliberately not guessed. HTTP/TLS failures propagate to
    scrape.py, which preserves the previous records for this source.
    """
    from datetime import date as _date
    from urllib.parse import urlparse
    import html as _html

    root = "https://samstag.adelaide.edu.au"
    paths = ("/current", "/upcoming", "/exhibitions", "/events")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"})

    def fetch(address):
        response = session.get(address, timeout=25)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def tidy(value):
        return " ".join(_html.unescape(str(value or "")).split())

    months = r"January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    date_part = rf"\d{{1,2}}\s+(?:{months})\s+20\d{{2}}"
    date_part_short = rf"\d{{1,2}}\s+(?:{months})"

    def dates(text):
        text = tidy(text).replace("–", "-").replace("—", "-")
        # Full explicit range: 9 October 2026 - 4 December 2026.
        m = re.search(rf"({date_part})\s*(?:-|to|until|through)\s*({date_part})", text, re.I)
        if m:
            return parse_date_text(m.group(1)), parse_date_text(m.group(2))
        # Shared-year range: 9 October - 4 December 2026.
        m = re.search(rf"({date_part_short})\s*(?:-|to|until|through)\s*({date_part})", text, re.I)
        if m:
            end = parse_date_text(m.group(2))
            start = parse_date_text(m.group(1) + " " + end[:4]) if end else ""
            return start, end
        # 9 - 31 October 2026 (same month).
        m = re.search(rf"(\d{{1,2}})\s*-\s*(\d{{1,2}}\s+(?:{months})\s+20\d{{2}})", text, re.I)
        if m:
            end = parse_date_text(m.group(2))
            parts = m.group(2).split()
            start = parse_date_text(m.group(1) + " " + " ".join(parts[1:]))
            return start, end
        # Single explicit date.
        m = re.search(rf"({date_part})", text, re.I)
        if m:
            return parse_date_text(m.group(1)), ""
        # HTML time datetime attributes may be ISO-formatted.
        m = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
        if m:
            return parse_date_text(m.group(1)), ""
        return "", ""

    def artwork(soup, page_url):
        for selector, attribute in (("meta[property='og:image']", "content"),
                                    ("meta[name='twitter:image']", "content"),
                                    ("main img", "src"), ("article img", "src")):
            tag = soup.select_one(selector)
            if tag:
                value = tidy(tag.get(attribute) or tag.get("data-src"))
                if value and not value.startswith("data:") and not any(x in value.lower() for x in ("logo", "favicon", "placeholder")):
                    return urljoin(page_url, value)
        return ""

    listings = []
    listing_errors = []
    for path in paths:
        url = root + path
        try:
            soup = fetch(url)
        except requests.RequestException as exc:
            listing_errors.append((path, str(exc)))
            continue
        listings.append((url, soup))
    if not listings:
        raise RuntimeError("SAMSTAG official listings unavailable: " + "; ".join(f"{path}: {error}" for path,error in listing_errors))

    # Discover detail links from exhibition/event pages, not site-wide menus.
    candidates = {}
    allowed_path = re.compile(r"/(?:exhibitions?|events?|current|upcoming)/[^/?#]+", re.I)
    for listing_url, soup in listings:
        main = soup.select_one("main") or soup
        for anchor in main.select("a[href]"):
            url = urljoin(listing_url, anchor.get("href", "")).split("#")[0]
            parsed = urlparse(url)
            if parsed.hostname != "samstag.adelaide.edu.au" or not allowed_path.search(parsed.path):
                continue
            if parsed.path.rstrip("/") in paths:
                continue
            label = tidy(anchor.get_text(" ", strip=True))
            parent = anchor.find_parent(["article", "li", "section", "div"])
            nearby = tidy(parent.get_text(" ", strip=True)) if parent else label
            if len(nearby) > 1200:
                nearby = label
            candidates.setdefault(url, (label, nearby))

    results = []
    undated = 0
    errors = 0
    today = _date.today().isoformat()
    for url, (listing_title, listing_text) in candidates.items():
        try:
            soup = fetch(url)
        except requests.RequestException:
            errors += 1
            continue
        main = soup.select_one("main") or soup
        heading = main.find("h1")
        title = tidy(heading.get_text(" ", strip=True)) if heading else listing_title
        if not title:
            continue
        # Prefer date information near the heading or marked-up date elements.
        date_chunks = []
        for tag in main.select("time[datetime], time, [class*='date'], [class*='Date']")[:25]:
            value = tidy(tag.get("datetime") or tag.get_text(" ", strip=True))
            if value:
                date_chunks.append(value)
        for tag in main.find_all(["h1", "h2", "h3", "p"], limit=24):
            value = tidy(tag.get_text(" ", strip=True))
            if len(value) <= 280:
                date_chunks.append(value)
        date_chunks.append(listing_text)
        start = end = ""
        for chunk in date_chunks:
            start, end = dates(chunk)
            if start:
                break
        if not start:
            undated += 1
            continue
        if end and end[:10] < start[:10]:
            undated += 1
            continue
        if (end or start)[:10] < today:
            continue
        # A page explicitly naming a different physical venue should not be
        # misrepresented as being at Samstag Museum.
        location = main.select_one("[class*='location'], [class*='venue']")
        location_text = tidy(location.get_text(" ", strip=True)) if location else ""
        if location_text and any(x in location_text.lower() for x in ("other venue", "offsite", "off-site")):
            continue
        results.append({"title": title, "venue": "Samstag Museum of Art",
                        "date": start, "end_date": end,
                        "category": ["Arts & Culture"], "image": artwork(soup, url),
                        "url": url})

    # Some current exhibitions may be presented directly on the listing page,
    # with no separate detail URL. Do not invent them without a dated card.
    unique = {}
    for event in results:
        unique[(event["title"].casefold(), event["date"][:10])] = event
    print(f"    SAMSTAG: {len(listings)} listing pages, {len(candidates)} detail links, "
          f"{len(unique)} verified current/future records; {undated} undated, "
          f"{errors} detail errors")
    return list(unique.values())


# ============================================================
# KERRY PACKER CIVIC GALLERY (ADELAIDE UNIVERSITY)
# ============================================================

def parse_kerry_packer_civic_gallery():
    """Official gallery exhibitions only, with verified date ranges.

    The old unisa.edu.au site is intentionally not requested. Exceptions on
    failed listing fetches let the caller preserve previously saved records.
    """
    from datetime import date as _date
    from urllib.parse import urlparse
    import html as _html

    listing_url = "https://hawkecentre.adelaide.edu.au/kerry-packer-civic-gallery/"
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"})

    def fetch(url):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def tidy(value):
        return " ".join(_html.unescape(str(value or "")).split())

    months = r"January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
    longdate = rf"\d{{1,2}}\s+(?:{months})\s+20\d{{2}}"
    shortdate = rf"\d{{1,2}}\s+(?:{months})"

    def parse_dates(value):
        value = tidy(value).replace("–", "-").replace("—", "-")
        # Explicit years on both ends.
        m = re.search(rf"({longdate})\s*(?:-|to|until)\s*({longdate})", value, re.I)
        if m:
            return parse_date_text(m.group(1)), parse_date_text(m.group(2))
        # Shared year, e.g. 17 September - 8 December 2026.
        m = re.search(rf"({shortdate})\s*(?:-|to|until)\s*({longdate})", value, re.I)
        if m:
            end = parse_date_text(m.group(2))
            return (parse_date_text(m.group(1) + " " + end[:4]) if end else ""), end
        # Listing-card short year: 17 Sep 26 8 Dec 26.
        m = re.search(rf"(\d{{1,2}})\s+({months})\s+([0-9]{{2}})\s+(\d{{1,2}})\s+({months})\s+([0-9]{{2}})", value, re.I)
        if m:
            start = parse_date_text(f"{m.group(1)} {m.group(2)} 20{m.group(3)}")
            end = parse_date_text(f"{m.group(4)} {m.group(5)} 20{m.group(6)}")
            return start, end
        # One-off exhibition with an explicit date.
        m = re.search(rf"({longdate})", value, re.I)
        return (parse_date_text(m.group(1)), "") if m else ("", "")

    def artwork(soup, url):
        for selector, attr in (("meta[property='og:image']", "content"),
                               ("main img", "src"), ("article img", "src")):
            tag = soup.select_one(selector)
            if tag:
                value = tidy(tag.get(attr) or tag.get("data-src"))
                if value and not value.startswith("data:") and not any(
                    bad in value.lower() for bad in ("favicon", "logo", "placeholder")
                ):
                    return urljoin(url, value)
        return ""

    listing = fetch(listing_url)
    main = listing.select_one("main") or listing
    candidates = {}
    for a in main.select("a[href]"):
        url = urljoin(listing_url, a.get("href", "")).split("#", 1)[0]
        parsed = urlparse(url)
        if parsed.hostname != "hawkecentre.adelaide.edu.au":
            continue
        if not re.search(r"/events-and-exhibitions/exhibitions/20\d{2}/[^/]+", parsed.path, re.I):
            continue
        parent = a.find_parent(["article", "li", "section", "div"])
        nearby = tidy(parent.get_text(" ", strip=True)) if parent else ""
        candidates.setdefault(url, nearby[:900])

    results = []
    undated = 0
    failures = 0
    past = 0
    today = _date.today().isoformat()
    for url, listing_text in candidates.items():
        try:
            soup = fetch(url)
        except requests.RequestException as exc:
            failures += 1
            print(f"    Kerry Packer detail unavailable: {url} ({exc})")
            continue
        content = soup.select_one("main") or soup
        heading = content.find("h1")
        title = tidy(heading.get_text(" ", strip=True)) if heading else ""
        if not title:
            undated += 1
            continue
        # Prefer the labelled Event details area or the first few short lines,
        # never arbitrary dates in long exhibition descriptions.
        chunks = []
        for tag in content.select("time, [class*='date'], [class*='Date']")[:20]:
            value = tidy(tag.get("datetime") or tag.get_text(" ", strip=True))
            if value and len(value) < 220:
                chunks.append(value)
        for tag in content.find_all(["h2", "h3", "p"], limit=28):
            value = tidy(tag.get_text(" ", strip=True))
            if 8 <= len(value) < 180:
                chunks.append(value)
        chunks.append(listing_text)
        start = end = ""
        for chunk in chunks:
            start, end = parse_dates(chunk)
            if start:
                break
        if not start or (end and end[:10] < start[:10]):
            undated += 1
            continue
        if (end or start)[:10] < today:
            past += 1
            continue
        # The exhibition section contains historical pages too. Only gallery
        # exhibitions are eligible, never offsite Hawke Centre talks.
        intro = tidy(content.get_text(" ", strip=True))[:1100].lower()
        if "kerry packer civic gallery" not in intro and "kerry packer civic gallery" not in listing_text.lower():
            continue
        results.append({"title": title, "venue": "Kerry Packer Civic Gallery",
                        "date": start, "end_date": end,
                        "category": ["Arts & Culture"],
                        "image": artwork(soup, url), "url": url})

    unique = {(e["title"].casefold(), e["date"][:10]): e for e in results}
    print(f"    Kerry Packer: {len(candidates)} exhibition links, "
          f"{len(unique)} verified current/future; {past} past, "
          f"{undated} undated, {failures} detail errors")
    return list(unique.values())



# Image selection for official event pages. Never use recommendation/footer imagery.
def _official_event_artwork(soup, page_url, title="", allow_venue_photo=False):
    from urllib.parse import urljoin
    import re
    def absolute(raw):
        raw = str(raw or "").strip()
        if not raw or raw.startswith(("data:", "blob:", "javascript:")):
            return ""
        result = urljoin(page_url, raw)
        if any(bad in result.lower() for bad in ("favicon", "placeholder", "logo.", "default-og", "spacer", "pixel")):
            return ""
        if not re.search(r"\.(?:jpe?g|png|webp|gif)(?:[?#]|$)|(?:wixstatic|imgix|cloudinary|lbcdn)\.", result, re.I):
            return ""
        return result
    def src(tag):
        if not tag: return ""
        for key in ("data-src", "data-original", "data-image", "data-lazy-src", "src", "content"):
            val = absolute(tag.get(key))
            if val: return val
        for key in ("srcset", "data-srcset"):
            entries = (tag.get(key) or "").split(",")
            if entries:
                val = absolute(entries[-1].strip().split()[0])
                if val: return val
        return ""
    # Social preview usually describes this exact page, not a related event.
    for selector in ('meta[property="og:image"]', 'meta[name="twitter:image"]', 'meta[property="twitter:image"]'):
        val = src(soup.select_one(selector))
        if val: return val
    # Match the event's own hero/title image, never an arbitrary image.
    if title:
        words = [w for w in re.findall(r"[a-z0-9]+", title.lower()) if len(w) >= 4]
        for tag in soup.select('main img, article img, [class*="hero"] img, [class*="banner"] img'):
            desc = " ".join((tag.get("alt") or "", tag.get("title") or "")).lower()
            if words and sum(w in desc for w in words) >= min(2,len(words)):
                val = src(tag)
                if val: return val
    if allow_venue_photo:
        for selector in ('main img', '[class*="hero"] img', '[class*="banner"] img'):
            val = src(soup.select_one(selector))
            if val: return val
    return ""

# ============================================================
# THE DISTRICT AT SKYCITY — verified dated activities only
# ============================================================
def parse_the_district_skycity():
    """Collect dated official SkyCity events and verified weekly trivia sessions."""
    from datetime import date as _date, timedelta as _timedelta
    from urllib.parse import urljoin, urlparse

    base = "https://skycityadelaide.com.au"
    listing_urls = [
        base + "/eat-and-drink/the-district/whats-on/",
        base + "/eat-and-drink/the-district/music/",
        base + "/whats-on/",
    ]
    # Official event-detail routes are under /whats-on/content/, not under
    # /eat-and-drink/the-district/ as the previous parser assumed.
    known_details = [
        base + "/whats-on/content/22728/8116/wednesday-trivia-at-the-district/",
        base + "/whats-on/content/22728/7296/melbourne-cup-at-the-district/",
    ]
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36"})

    def fetch(url):
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")

    def clean(text):
        return " ".join(str(text or "").split())

    def event_date(soup):
        # Event-specific structured metadata.
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or script.get_text())
            except (ValueError, TypeError):
                continue
            stack = [data]
            while stack:
                item = stack.pop()
                if isinstance(item, list):
                    stack.extend(item)
                elif isinstance(item, dict):
                    stack.extend(v for k, v in item.items() if k in ("@graph", "mainEntity", "itemListElement"))
                    types = item.get("@type", [])
                    types = [types] if isinstance(types, str) else types
                    if any(isinstance(t, str) and (t == "Event" or t.endswith("Event")) for t in types):
                        raw = str(item.get("startDate") or "")
                        if re.match(r"^20\d{2}-\d{2}-\d{2}T\d{2}:\d{2}", raw):
                            return raw[:19]
                        value = parse_date_text(raw)
                        if value:
                            return value
        main = soup.select_one("main") or soup
        for tag in main.select('time[datetime], [itemprop="startDate"][content], [class*="date"], [class*="Date"]')[:30]:
            value = clean(tag.get("datetime") or tag.get("content") or tag.get_text(" ", strip=True))
            if len(value) <= 130:
                parsed = parse_date_text(value)
                if parsed:
                    return parsed
        # Some SkyCity detail pages render dates as "Tuesdays from 03 November 2026".
        # Only inspect a small event heading/intro, never footer or related cards.
        for tag in main.find_all(["h1", "h2", "h3", "p"], limit=18):
            value = clean(tag.get_text(" ", strip=True))
            if len(value) <= 240:
                parsed = parse_date_text(value)
                if parsed:
                    return parsed
        return ""

    def artwork(soup, url, title=""):
        return _official_event_artwork(soup, url, title)

    candidates = set(known_details)
    listings_ok = 0
    for listing_url in listing_urls:
        try:
            soup = fetch(listing_url)
        except requests.RequestException as exc:
            print(f"    The District listing unavailable: {listing_url} ({exc})")
            continue
        listings_ok += 1
        for a in soup.select("a[href]"):
            url = urljoin(listing_url, a.get("href", "")).split("#")[0].split("?")[0]
            parsed = urlparse(url)
            if parsed.hostname not in ("skycityadelaide.com.au", "www.skycityadelaide.com.au"):
                continue
            if not re.match(r"^/whats-on/content/\d+/\d+/[^/]+/?$", parsed.path, re.I):
                continue
            # The general What's On listing includes other SkyCity venues.
            # Check venue text on each detail page before accepting it.
            candidates.add(url)

    if not listings_ok:
        raise RuntimeError("The District listings unavailable; existing records preserved")

    results = []
    undated = past = errors = promos = offsite = 0
    today = _date.today()
    for url in sorted(candidates):
        try:
            soup = fetch(url)
        except requests.RequestException as exc:
            errors += 1
            print(f"    The District detail unavailable: {url} ({exc})")
            continue
        main = soup.select_one("main") or soup
        heading = main.find("h1")
        title = clean(heading.get_text(" ", strip=True)) if heading else ""
        content = clean(main.get_text(" ", strip=True))
        slug = urlparse(url).path.rstrip("/").split("/")[-1].casefold()
        # SkyCity sometimes places the actual event title outside <main>.
        # Use the verified official event slug for the weekly trivia only.
        is_trivia = slug == "wednesday-trivia-at-the-district"
        if is_trivia:
            title = "Wednesday Trivia at The District"
        elif not title:
            og = soup.select_one('meta[property="og:title"]')
            title = clean(og.get("content")) if og else ""
        low = title.casefold()
        # An event's URL and listing association can establish the venue even
        # if SkyCity's <main> omits it. Do not accept unrelated SkyCity events.
        district_confirmed = ("the district" in content.casefold()
                              or "the-district" in slug or "the district" in low)
        if (not title or not district_confirmed or
                "we apologize for the inconvenience" in low or
                "access denied" in low or "page not found" in low):
            offsite += 1
            continue
        if any(term in low for term in (
            "happy hour", "burger & beer", "wings", "fridays at the district",
            "poker", "home of ufc", "english premier league",
            "up late and loud", "live bands at the district"
        )):
            promos += 1
            continue
        image = artwork(soup, url, title)
        if "wednesday trivia at the district" in low or "quiz meisters trivia at the district" in low:
            # Official detail confirms every Wednesday from 30 September,
            # 6pm-8pm. Generate only the next eight confirmed weekly instances.
            first = _date(2026, 9, 30)
            day = max(first, today)
            day += _timedelta(days=(2 - day.weekday()) % 7)
            for week in range(8):
                d = day + _timedelta(weeks=week)
                results.append({
                    "title": "QuizMeisters Trivia at The District",
                    "venue": "The District at SkyCity",
                    "date": d.isoformat() + "T18:00:00",
                    "end_date": d.isoformat() + "T20:00:00",
                    "category": ["Community"],
                    "image": image, "url": url,
                })
            continue
        date = event_date(soup)
        if not date:
            undated += 1
            continue
        if date[:10] < today.isoformat():
            past += 1
            continue
        category = ["Sport"] if "melbourne cup" in low else (
            ["Music"] if any(x in low for x in ("queen", "concert", "music", "band", "dj")) else ["Other"])
        results.append({"title": title, "venue": "The District at SkyCity",
                        "date": date, "end_date": "", "category": category,
                        "image": image, "url": url})

    unique = {(e["title"].casefold(), e["date"][:16]): e for e in results}
    print(f"    The District: {listings_ok} listing pages, {len(candidates)} candidate details, "
          f"{len(unique)} verified upcoming sessions; {past} past, {undated} undated, "
          f"{promos} promotions, {offsite} other venues, {errors} detail errors")
    return list(unique.values())


# ============================================================
# A DAY ON THE GREEN — discover artist tours and venue show pages
# ============================================================

def parse_a_day_on_the_green(soup, source_url):
    """Discover artist tours, then verify each dated South Australian show.

    A tour landing page is not an individual show: its other-state dates must
    never be mistaken for an SA concert. Only venue-specific pages are saved.
    """
    from urllib.parse import urlparse
    from datetime import date

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0 Safari/537.36"})
    host = (urlparse(source_url).hostname or "").removeprefix("www.")
    visited = set()
    candidates = set()
    queue = []
    ignored = {"about", "contact", "faq", "faqs", "news", "privacy", "terms", "login", "register", "signup", "membership", "venues", "transport", "accessibility", "gallery", "search", "subscribe", "home"}

    def add_links(page, base, depth):
        for anchor in page.find_all("a", href=True):
            href = normalise_url(anchor.get("href"), base).split("#", 1)[0].split("?", 1)[0].rstrip("/")
            parsed = urlparse(href)
            if parsed.scheme not in ("http", "https") or (parsed.hostname or "").removeprefix("www.") != host:
                continue
            parts = [x.lower() for x in parsed.path.strip("/").split("/") if x]
            if not parts or len(parts) > 4 or parts[0] in ignored:
                continue
            if any(x.endswith((".pdf", ".jpg", ".png", ".webp")) for x in parts):
                continue
            # Site uses /boyziimen for tour landing and
            # /currenttours/boyziimen/geelong for individual show pages.
            if parts[0] == "currenttours" and len(parts) >= 3:
                candidates.add(href)
            elif depth == 0 and len(parts) <= 2 and not parts[-1].endswith(("-faqs", "-news")):
                queue.append(href)
            elif depth == 1 and parts[0] == "currenttours" and len(parts) >= 3:
                candidates.add(href)

    add_links(soup, source_url, 0)
    # Artist landing pages expose venue-specific detail URLs.
    for url in list(dict.fromkeys(queue))[:45]:
        if url in visited:
            continue
        visited.add(url)
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            add_links(BeautifulSoup(r.text, "lxml"), r.url, 1)
        except requests.RequestException as exc:
            print(f"    A Day on the Green tour page unavailable: {url}: {exc}")

    results = []
    seen = set()
    rejected = 0
    sa_places = ("south australia", "adelaide", "barossa", "mclaren vale", "mclaren flat",
                 "adelaide hills", "seppeltsfield", "tanunda", "nuriootpa", "langhorne creek",
                 "mount barker", "clare valley", "mclaren", "rosemount", "peter lehmann")
    other_states = ("victoria", "new south wales", "queensland", "western australia",
                    "tasmania", "northern territory", "australian capital territory")

    for url in sorted(candidates)[:100]:
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            page = BeautifulSoup(r.text, "lxml")
        except requests.RequestException as exc:
            print(f"    A Day on the Green show page unavailable: {url}: {exc}")
            continue
        # The opening part of an individual show page contains its own date,
        # venue and locality. The lower 'All tour dates' section must not be
        # used to verify a show location.
        heading = page.find("h1")
        if not heading:
            rejected += 1
            continue
        title = " ".join(heading.stripped_strings).strip()
        prelude = []
        for element in page.find_all(["h1", "h2", "h3", "h4", "h5", "time"], limit=35):
            value = " ".join(element.stripped_strings).strip()
            if value:
                prelude.append(value)
        opening = " | ".join(prelude[:12])
        if any(state in opening.casefold() for state in other_states) or re.search(r"\b(?:NSW|VIC|QLD|WA|TAS|NT|ACT)\b", opening):
            rejected += 1
            continue
        if not (any(place in opening.casefold() for place in sa_places) or re.search(r"\bSA\b", opening)):
            rejected += 1
            continue
        date_match = re.search(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*\s+(\d{1,2})\s+([A-Za-z]+)\s+(20\d{2})\b", opening, re.I)
        dt = parse_date_text(" ".join(date_match.groups())) if date_match else ""
        if not dt or dt[:10] < date.today().isoformat():
            rejected += 1
            continue
        # The show page presents the venue in a heading immediately before
        # the locality; don't use a tour name as a venue.
        venue = ""
        headings = [" ".join(x.stripped_strings).strip() for x in page.find_all(["h4", "h5"], limit=20)]
        for i, value in enumerate(headings[:-1]):
            if any(place in headings[i+1].casefold() for place in sa_places) or re.search(r"\bSA\b", headings[i+1]):
                if value and not re.search(r"\b(?:tour|tickets|concert|dates)\b", value, re.I):
                    venue = value
                    break
        if not venue:
            rejected += 1
            continue
        image = ""
        for attr in ({"property": "og:image"}, {"name": "twitter:image"}):
            tag = page.find("meta", attrs=attr)
            if tag and tag.get("content"):
                image = normalise_url(tag["content"], r.url)
                break
        key = (title.casefold(), venue.casefold(), dt[:10])
        if key in seen:
            continue
        seen.add(key)
        results.append({"title": title, "venue": venue, "date": dt,
                        "end_date": "", "category": ["Music"], "image": image, "url": r.url})

    print(f"    A Day on the Green: {len(visited)} tour pages checked, "
          f"{len(candidates)} candidate show pages, {len(results)} verified SA concerts "
          f"({rejected} rejected)")
    return results
