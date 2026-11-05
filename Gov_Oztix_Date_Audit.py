"""Read-only audit of The Gov Oztix records. Does not modify project files."""
import sys
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
sys.path.insert(0, str(Path('Scraper').resolve()))
import requests
import parsers

hits = []
old_post = requests.Session.post

def capture(self, url, *args, **kwargs):
    response = old_post(self, url, *args, **kwargs)
    if 'algolia.net/1/indexes/' in url and response.ok:
        for block in response.json().get('results', []):
            hits.extend(block.get('hits', []))
    return response

requests.Session.post = capture
try:
    parsed = parsers.parse_the_gov()
finally:
    requests.Session.post = old_post

try:
    from zoneinfo import ZoneInfo
    tz = ZoneInfo('Australia/Adelaide')
except Exception:
    # Only the date is needed. UTC+10:30 is correct during late October.
    tz = timezone(timedelta(hours=10, minutes=30))

today = datetime.now().date()
counts = Counter()
future = []
past = []
for h in hits:
    title = str(h.get('EventName') or '').strip()
    try:
        stamp = int(h.get('DateStartUnix') or 0)
        date = datetime.fromtimestamp(stamp, timezone.utc).astimezone(tz).date() if stamp > 0 else None
    except (ValueError, TypeError, OverflowError):
        date = None
    venue = h.get('Venue') or {}
    vid = str(venue.get('Id') or '') if isinstance(venue, dict) else ''
    if vid not in ('2437', '4633'):
        reason = 'wrong venue'
    elif h.get('IsCancelled'):
        reason = 'cancelled'
    elif h.get('IsPostponed'):
        reason = 'postponed'
    elif h.get('IsApproved') is False:
        reason = 'unapproved'
    elif not title:
        reason = 'missing title'
    elif date is None:
        reason = 'missing date'
    elif date < today:
        reason = 'past date'
    elif urlparse(str(h.get('EventUrl') or '')).hostname not in {'tickets.oztix.com.au', 'www.oztix.com.au', 'oztix.com.au'}:
        reason = 'invalid URL host'
    elif not (h.get('EventGuid') or h.get('EventId')):
        reason = 'missing event ID'
    else:
        reason = 'eligible upcoming'
    counts[reason] += 1
    item = (str(date or 'UNKNOWN'), title, vid, str(h.get('EventGuid') or h.get('EventId') or ''))
    if reason == 'eligible upcoming':
        future.append(item)
    elif reason == 'past date':
        past.append(item)

print('\n=== GOV OZTIX DATE AUDIT ===')
print('Today (computer date):', today)
print('Raw hits:', len(hits))
print('Parser results (including Moshtix):', len(parsed))
print('\nExclusive reason counts:')
for key, value in counts.most_common():
    print(f'  {key}: {value}')
print('\nALL ELIGIBLE UPCOMING OZTIX EVENTS:')
for d, title, vid, guid in sorted(future):
    print(f'  {d} | {title} | venue {vid} | {guid}')
print('\nMOST RECENT 12 PAST OZTIX EVENTS:')
for d, title, vid, guid in sorted(past, reverse=True)[:12]:
    print(f'  {d} | {title} | venue {vid}')
print('\nFINAL PARSER EVENTS (Oztix and Moshtix):')
for e in sorted(parsed, key=lambda e: str(e.get('date') or '')):
    print(f"  {e.get('date','')} | {e.get('title','')} | {e.get('url','')}")
print('\nRead-only audit complete. No project files modified.')
