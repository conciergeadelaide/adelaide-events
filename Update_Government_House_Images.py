"""Run from the adelaide-events repository root. Updates only Government House images."""
import json
import shutil
from datetime import datetime
from pathlib import Path

root = Path(__file__).resolve().parent
path = root / 'events.json'
image = 'https://www.governor.sa.gov.au/assets/_1400x846_crop_center-center_none/13610/Government-House-Adelaide-March-2023.webp'
if not path.is_file():
    raise SystemExit('ERROR: events.json not found. Put this file in the adelaide-events folder.')
with path.open('r', encoding='utf-8-sig') as f:
    data = json.load(f)
if not isinstance(data, list):
    raise SystemExit('ERROR: Expected events.json to contain a list. Nothing changed.')
updated = 0
for event in data:
    if not isinstance(event, dict):
        continue
    venue = str(event.get('venue', '')).strip().casefold()
    if venue == 'government house' and event.get('image') != image:
        event['image'] = image
        updated += 1
if updated:
    backup = root / ('events.json.before-government-house-images-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.bak')
    shutil.copy2(path, backup)
    with path.open('w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print('Backup:', backup.name)
print('Government House images updated:', updated)
print('Total event records preserved:', len(data))
print('Done. No other event details changed.')
