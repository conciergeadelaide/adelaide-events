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
