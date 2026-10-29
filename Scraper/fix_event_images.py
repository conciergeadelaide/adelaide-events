"""One-time safe repair of existing SkyCity, Plant 4 and ASO card images.
Run from repository root: python Scraper\fix_event_images.py
Never deletes records, changes dates, or overwrites existing good images.
"""
import json
import os
import sys
import shutil
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
    from parsers import _official_event_artwork
except ImportError as exc:
    raise SystemExit(f"Missing scraper dependency: {exc}")

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "events.json"
GOVERNMENT_IMAGE = "https://www.governor.sa.gov.au/assets/_1400x846_crop_center-center_none/13610/Government-House-Adelaide-March-2023.webp"

def main():
    if not PATH.exists():
        raise SystemExit("events.json not found in the repository root")
    original = PATH.read_bytes()
    data = json.loads(original.decode("utf-8-sig"))
    if not isinstance(data, list):
        raise SystemExit("Unexpected events.json structure: no changes made")
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0 Safari/537.36"})
    cache = {}
    changed = []
    for event in data:
        source = str(event.get("source", "")).lower()
        venue = str(event.get("venue", "")).lower()
        title = str(event.get("title", ""))
        url = str(event.get("link") or event.get("url") or "")
        if source == "government house" or venue == "government house":
            if event.get("image") != GOVERNMENT_IMAGE:
                event["image"] = GOVERNMENT_IMAGE
                changed.append((title, "Government House photo"))
            continue
        skycity = source == "the district at skycity" or venue == "the district at skycity"
        plant = source == "plant 4 bowden" or venue == "plant 4 bowden"
        aso = source == "adelaide symphony orchestra"
        if not (skycity or plant or aso):
            continue
        # Do not overwrite existing artwork: we cannot confirm from URL alone
        # whether the photograph is wrong. Only repair empty or animated GIF.
        existing = str(event.get("image") or "")
        if existing and not (aso and urlparse(existing).path.lower().endswith(".gif")):
            continue
        if not url.startswith("https://"):
            continue
        key = (url, "" if (skycity or plant) else title)
        if key not in cache:
            try:
                response = session.get(url, timeout=18)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "lxml")
                cache[key] = _official_event_artwork(soup, response.url, title if aso else "", allow_venue_photo=plant)
            except requests.RequestException as exc:
                print(f"Could not inspect {url}: {exc}")
                cache[key] = ""
        image = cache[key]
        if image and image != existing and not (aso and urlparse(image).path.lower().endswith(".gif")):
            event["image"] = image
            changed.append((title, image))
    print(f"Records: {len(data)}; images repaired: {len(changed)}")
    for title, img in changed[:25]:
        print(f"  {title}: {img[:105]}")
    if not changed:
        print("No verified changes. events.json left untouched.")
        return
    # Never alter record count or other fields.
    if len(data) != len(json.loads(original.decode("utf-8-sig"))):
        raise SystemExit("Record count changed unexpectedly; aborting")
    backup = PATH.with_name("events.backup-before-image-fix.json")
    if not backup.exists():
        shutil.copy2(PATH, backup)
    temporary = PATH.with_name("events.image-fix.tmp")
    try:
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        json.loads(temporary.read_text(encoding="utf-8"))
        os.replace(temporary, PATH)
    finally:
        if temporary.exists(): temporary.unlink()
    print("Saved events.json; original backup: " + backup.name)

if __name__ == "__main__":
    main()
