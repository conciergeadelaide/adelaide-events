"""Read-only diagnostic for The Gov's Oztix records. Run from adelaide-events root.
Writes no files and does not change events.json. Redirect output to a .txt file.
"""
import sys
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path('Scraper').resolve()))
import requests
import parsers

captured = []
original_post = requests.Session.post

def observe_post(self, url, *args, **kwargs):
    response = original_post(self, url, *args, **kwargs)
    if 'algolia.net/1/indexes/' in url and response.ok:
        try:
            for result in response.json().get('results', []):
                captured.extend(result.get('hits', []))
        except (ValueError, TypeError):
            pass
    return response

requests.Session.post = observe_post
try:
    events = parsers.parse_the_gov()
finally:
    requests.Session.post = original_post

print('\n' + '=' * 65)
print('OZTIX FILTER DIAGNOSTIC')
print('=' * 65)
print('Total raw Oztix hits:', len(captured))
print('Events returned by Gov parser (Oztix + Moshtix):', len(events))
if not captured:
    print('No Algolia records captured. Check the scraper output above.')
    sys.exit(0)

reasons = Counter()
examples = {}
now = datetime.now().date()
for hit in captured:
    title = str(hit.get('EventName') or '')
    venue = hit.get('Venue') or {}
    venue_id = venue.get('Id') if isinstance(venue, dict) else None
    url = str(hit.get('EventUrl') or '')
    stamp = hit.get('DateStartUnix')
    reason = 'passed core checks'
    if not isinstance(venue, dict) or str(venue_id) not in ('2437', '4633'):
        reason = 'venue missing / unexpected ID'
    elif hit.get('IsCancelled'):
        reason = 'cancelled'
    elif hit.get('IsPostponed'):
        reason = 'postponed'
    elif hit.get('IsApproved') is False:
        reason = 'not approved'
    elif not title:
        reason = 'missing title'
    elif re.search(r'\b(gift card|gift voucher|membership)\b', title, re.I):
        reason = 'non-event product'
    else:
        try:
            ts = int(stamp or 0)
            if ts <= 0:
                reason = 'missing / zero DateStartUnix'
            elif datetime.fromtimestamp(ts, timezone.utc).date() < now.replace(day=max(1, now.day - 2)) and datetime.fromtimestamp(ts, timezone.utc).date() < now:
                reason = 'past UTC date (approximate)'
        except (ValueError, TypeError, OverflowError):
            reason = 'invalid DateStartUnix'
        if reason == 'passed core checks' and urlparse(url).hostname not in {'tickets.oztix.com.au', 'www.oztix.com.au', 'oztix.com.au'}:
            reason = 'URL hostname not allowed'
        if reason == 'passed core checks' and not (hit.get('EventGuid') or hit.get('EventId')):
            reason = 'missing event GUID/ID'
    reasons[reason] += 1
    if len(examples.get(reason, [])) < 5:
        examples.setdefault(reason, []).append({
            'title': title[:100], 'venue_id': venue_id,
            'date_start_unix': stamp, 'date_start': hit.get('DateStart'),
            'event_url': url[:160], 'event_guid': hit.get('EventGuid'),
            'event_id': hit.get('EventId'),
            'cancelled': hit.get('IsCancelled'), 'postponed': hit.get('IsPostponed'),
            'approved': hit.get('IsApproved'),
        })

print('\nRejection / acceptance breakdown:')
for reason, count in reasons.most_common():
    print(f'  {reason}: {count}')
for reason, samples in examples.items():
    print('\nSAMPLES:', reason)
    for sample in samples:
        print(' ', json.dumps(sample, ensure_ascii=False))
print('\nFIRST HIT FIELD NAMES:', ', '.join(sorted(captured[0].keys())))
print('\nDiagnostic complete. No project files modified.')
