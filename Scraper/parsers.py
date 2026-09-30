import re
import json
from datetime import datetime
from urllib.parse import urljoin


def parse_json_ld(soup):
    events = []

    for script in soup.find_all(
        "script",
        type="application/ld+json"
    ):
        try:
            data = json.loads(
                script.string or script.get_text()
            )

        except Exception:
            continue

        items = data if isinstance(data, list) else [data]

        for item in items:

            if not isinstance(item, dict):
                continue

            item_type = item.get("@type")

            if item_type not in [
                "Event",
                ["Event"]
            ]:
                continue

            title = item.get("name")

            if not title:
                continue

            start_date = item.get(
                "startDate",
                ""
            )

            if not start_date:
                continue

            location_data = item.get(
                "location",
                {}
            )

            if isinstance(location_data, dict):

                venue = location_data.get(
                    "name",
                    ""
                )

                address = location_data.get(
                    "address",
                    {}
                )

                if isinstance(address, dict):

                    location = address.get(
                        "addressLocality",
                        "Adelaide"
                    )

                else:

                    location = "Adelaide"

            else:

                venue = ""
                location = "Adelaide"

            image = item.get(
                "image",
                ""
            )

            if isinstance(image, list):

                image = (
                    image[0]
                    if image
                    else ""
                )

            events.append({
                "title": title,
                "venue": venue,
                "location": location,
                "datetime": start_date,
                "category": "Other",
                "image": image,
                "url": item.get(
                    "url",
                    ""
                )
            })

    return events


def parse_adelaide_festival_centre(soup):
    events = []

    cards = soup.find_all(
        "article",
        class_="card"
    )

    for card in cards:

        title_element = card.find(
            "h3"
        )

        if not title_element:
            continue

        title = title_element.get_text(
            " ",
            strip=True
        )

        link = card.find(
            "a",
            href=True
        )

        if not link:
            continue

        url = urljoin(
            "https://www.adelaidefestivalcentre.com.au",
            link["href"]
        )

        time_element = card.find(
            "time",
            datetime=True
        )

        if not time_element:
            continue

        date_value = time_element.get(
            "datetime",
            ""
        )

        if not date_value:
            continue

        if len(date_value) == 10:

            datetime_value = (
                f"{date_value}T00:00:00"
            )

        else:

            datetime_value = date_value

        venue = ""

        paragraphs = card.find_all(
            "p"
        )

        for paragraph in paragraphs:

            text = paragraph.get_text(
                " ",
                strip=True
            )

            if text:
                venue = text
                break

        image = ""

        image_element = card.find(
            "img"
        )

        if image_element:

            image = (
                image_element.get(
                    "data-srcset",
                    ""
                )
                or image_element.get(
                    "src",
                    ""
                )
            )

            if "," in image:

                image = (
                    image.split(",")[0]
                    .strip()
                )

                if " " in image:

                    image = (
                        image.split(" ")[0]
                    )

        title_lower = title.lower()

        if "family" in title_lower:

            category = "Family"

        elif any(
            word in title_lower
            for word in [
                "comedy",
                "comedian"
            ]
        ):

            category = "Comedy"

        elif any(
            word in title_lower
            for word in [
                "concert",
                "music",
                "live"
            ]
        ):

            category = "Music"

        elif any(
            word in title_lower
            for word in [
                "theatre",
                "theater",
                "salesman",
                "play"
            ]
        ):

            category = "Theatre"

        elif any(
            word in title_lower
            for word in [
                "talk",
                "lecture",
                "conversation"
            ]
        ):

            category = "Talks"

        elif any(
            word in title_lower
            for word in [
                "market",
                "food",
                "festival"
            ]
        ):

            category = "Festival"

        else:

            category = "Other"

        events.append({
            "title": title,
            "venue": venue,
            "location": "Adelaide",
            "datetime": datetime_value,
            "category": category,
            "image": image,
            "url": url
        })

    return events


def parse_adelaide_oval(soup):
    events = []

    current_date = datetime.now().date()

    event_links = []

    for link in soup.find_all(
        "a",
        href=True
    ):

        text = link.get_text(
            " ",
            strip=True
        )

        if "Event info" not in text:
            continue

        if "/events/" not in link["href"]:
            continue

        event_links.append(
            link
        )

    seen_urls = set()

    for link in event_links:

        url = urljoin(
            "https://www.adelaideoval.com.au",
            link["href"]
        )

        if url in seen_urls:
            continue

        seen_urls.add(url)

        text = link.get_text(
            " ",
            strip=True
        )

        text = re.sub(
            r"\s*Event info\s*$",
            "",
            text,
            flags=re.IGNORECASE
        )

        date_match = re.search(
            r"([A-Z][a-z]+day\s+)?"
            r"(\d{1,2})\s+"
            r"([A-Z][a-z]+),?\s+"
            r"(\d{1,2}:\d{2}\s*[ap]m)",
            text,
            flags=re.IGNORECASE
        )

        if not date_match:
            continue

        day = int(
            date_match.group(2)
        )

        month_name = date_match.group(3)

        time_value = date_match.group(4)

        try:

            month_number = datetime.strptime(
                month_name,
                "%B"
            ).month

        except ValueError:

            continue

        year = current_date.year

        if month_number < current_date.month:

            year += 1

        try:

            event_datetime = datetime.strptime(
                f"{day} {month_name} "
                f"{year} {time_value}",
                "%d %B %Y %I:%M %p"
            )

        except ValueError:

            continue

        datetime_value = event_datetime.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )

        title = text[
            :date_match.start()
        ].strip()

        title = re.sub(
            r"^\d{1,2}\s+\w+\s+",
            "",
            title
        ).strip()

        if not title:
            continue

        title_lower = title.lower()

        if any(
            word in title_lower
            for word in [
                "robbie williams",
                "concert",
                "music",
                "tour"
            ]
        ):

            category = "Music"

        else:

            category = "Sport"

        events.append({
            "title": title,
            "venue": "Adelaide Oval",
            "location": "North Adelaide",
            "datetime": datetime_value,
            "category": category,
            "image": "",
            "url": url
        })

    return events


def parse_adelaide_convention_centre(soup):
    events = []

    containers = []

    # Standard event cards
    containers.extend(
        soup.select(".event-card")
    )

    # Featured event
    containers.extend(
        soup.select(".archive-featured-event")
    )

    seen_urls = set()

    for container in containers:

        title_element = container.select_one(
            ".event-card__title, "
            ".archive-featured-event__title"
        )

        if not title_element:
            continue

        title = title_element.get_text(
            " ",
            strip=True
        )

        if not title:
            continue

        date_element = container.select_one(
            ".event-card__date, "
            ".archive-featured-event__date"
        )

        if not date_element:
            continue

        date_text = date_element.get_text(
            " ",
            strip=True
        )

        # Find the event link.
        link = container.find(
            "a",
            href=True
        )

        if not link:

            parent = container.parent

            for _ in range(5):

                if not parent:
                    break

                link = parent.find(
                    "a",
                    href=True
                )

                if link:
                    break

                parent = parent.parent

        if not link:
            continue

        url = urljoin(
            "https://www.adelaidecc.com.au",
            link["href"]
        )

        if url in seen_urls:
            continue

        seen_urls.add(url)

        # ----------------------------------
        # Extract date
        # ----------------------------------

        range_date = re.search(
            r"(\d{1,2})\s*&\s*(\d{1,2})\s+"
            r"([A-Za-z]+)\s+"
            r"(\d{4})",
            date_text
        )

        single_date = re.search(
            r"(\d{1,2})\s+"
            r"([A-Za-z]+)\s+"
            r"(\d{4})",
            date_text
        )

        if range_date:

            day = int(
                range_date.group(1)
            )

            month = range_date.group(3)

            year = int(
                range_date.group(4)
            )

        elif single_date:

            day = int(
                single_date.group(1)
            )

            month = single_date.group(2)

            year = int(
                single_date.group(3)
            )

        else:

            continue

        try:

            event_date = datetime.strptime(
                f"{day} {month} {year}",
                "%d %B %Y"
            )

        except ValueError:

            continue

        datetime_value = event_date.strftime(
            "%Y-%m-%dT00:00:00"
        )

        # ----------------------------------
        # Category
        # ----------------------------------

        title_lower = title.lower()

        if any(
            word in title_lower
            for word in [
                "christmas",
                "festival"
            ]
        ):

            category = "Festival"

        elif any(
            word in title_lower
            for word in [
                "restaurant",
                "food",
                "dining"
            ]
        ):

            category = "Food & Beverage"

        elif any(
            word in title_lower
            for word in [
                "concert",
                "music",
                "orchestra",
                "live"
            ]
        ):

            category = "Music"

        elif any(
            word in title_lower
            for word in [
                "expo",
                "conference",
                "workshop"
            ]
        ):

            category = (
                "Conferences/Workshops/Expos"
            )

        else:

            category = "Other"

        # ----------------------------------
        # Image
        # ----------------------------------

        image = ""

        image_element = container.find(
            "img"
        )

        if image_element:

            image = (
                image_element.get(
                    "src",
                    ""
                )
                or image_element.get(
                    "data-src",
                    ""
                )
                or image_element.get(
                    "data-lazy-src",
                    ""
                )
            )

        events.append({
            "title": title,
            "venue": "Adelaide Convention Centre",
            "location": "Adelaide CBD",
            "datetime": datetime_value,
            "category": category,
            "image": image,
            "url": url
        })

    return events