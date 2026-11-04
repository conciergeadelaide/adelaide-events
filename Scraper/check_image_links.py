"""Read-only image availability audit for the Adelaide events website.

Run from repository root: python Scraper/check_image_links.py
Requires requests (already used by the scraper). Does not modify events.json.
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

ROOT = Path(__file__).resolve().parent.parent
SITE_HOST = 'conciergeadelaide.github.io'
SITE_PREFIX = '/adelaide-events/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; AdelaideEventsImageAudit/1.0)', 'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'}
IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg', '.avif', '.bmp')


def local_file(url):
    parsed = urlparse(url)
    if parsed.scheme in ('http', 'https'):
        if parsed.hostname != SITE_HOST or not parsed.path.startswith(SITE_PREFIX):
            return None
        relative = unquote(parsed.path[len(SITE_PREFIX):])
    elif not parsed.scheme and not parsed.netloc:
        relative = unquote(parsed.path).lstrip('/')
    else:
        return None
    candidate = (ROOT / relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return False
    return candidate


def check_one(url, timeout):
    if not url:
        return 'MISSING', '', 'No image URL'
    if url.startswith('data:image/'):
        return 'EMBEDDED', '', 'Embedded image; not an external URL'
    local = local_file(url)
    if local is False:
        return 'INVALID', '', 'Local path escapes repository'
    if local is not None:
        return ('OK_LOCAL', '', str(local.relative_to(ROOT))) if local.is_file() and local.stat().st_size else ('BROKEN_LOCAL', '', str(local.relative_to(ROOT)))
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        return 'INVALID', '', 'Not an HTTP(S) image URL'
    # A GET with streaming avoids downloading large artwork while verifying the response.
    try:
        with requests.get(url, headers=HEADERS, timeout=(5, timeout), stream=True, allow_redirects=True) as response:
            status = response.status_code
            ctype = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
            if status in (401, 403, 407, 429):
                return 'BLOCKED', str(status), 'Access restriction or rate limit; browser check needed'
            if status in (404, 410):
                return 'BROKEN_HTTP', str(status), 'Image not found or gone'
            if status >= 500:
                return 'SERVER_ERROR', str(status), 'Remote server error; retry later'
            if status >= 400:
                return 'HTTP_ERROR', str(status), 'HTTP error; review manually'
            if not (200 <= status < 300):
                return 'UNEXPECTED', str(status), 'Unexpected HTTP status'
            if ctype.startswith('image/'):
                return 'OK', str(status), ctype
            if ctype in ('text/html', 'application/xhtml+xml', 'application/json', 'text/plain'):
                return 'NOT_IMAGE', str(status), 'Returned ' + ctype
            # Some image CDNs omit Content-Type; avoid falsely flagging them as broken.
            return 'UNCERTAIN', str(status), 'Missing or unusual Content-Type: ' + (ctype or '(none)')
    except requests.exceptions.Timeout:
        return 'TIMEOUT', '', 'Request timed out; not proof image is broken'
    except requests.exceptions.RequestException as exc:
        return 'NETWORK_ERROR', '', str(exc)[:180]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workers', type=int, default=8, help='Concurrent requests (default 8)')
    parser.add_argument('--timeout', type=int, default=12, help='Read timeout seconds (default 12)')
    parser.add_argument('--limit', type=int, default=0, help='Test first N distinct URLs (0=all)')
    args = parser.parse_args()
    data_file = ROOT / 'events.json'
    if not data_file.exists():
        raise SystemExit('Cannot find events.json beside index.html. Run from a complete repository.')
    events = json.loads(data_file.read_text(encoding='utf-8-sig'))
    if not isinstance(events, list):
        raise SystemExit('Expected events.json to contain a list of events.')
    by_url = defaultdict(list)
    for event in events:
        url = str(event.get('image') or '').strip()
        by_url[url].append(event)
    urls = list(by_url)
    if args.limit > 0:
        urls = urls[:args.limit]
    print(f'Events in file: {len(events)}')
    print(f'Distinct image URLs: {len(by_url)}')
    print(f'Checking: {len(urls)} URLs with {max(1, min(args.workers, 16))} workers')
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 16))) as executor:
        futures = {executor.submit(check_one, url, max(3, args.timeout)): url for url in urls}
        for i, future in enumerate(as_completed(futures), 1):
            url = futures[future]
            try:
                results[url] = future.result()
            except Exception as exc:
                results[url] = ('ERROR', '', repr(exc)[:180])
            if i % 100 == 0 or i == len(urls):
                print(f'Checked {i}/{len(urls)}')
    report = ROOT / 'image-health-report.csv'
    with report.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['status', 'http_status', 'reason', 'title', 'date', 'source', 'image_url', 'event_link'])
        for url in urls:
            status, http, reason = results[url]
            for event in by_url[url]:
                writer.writerow([status, http, reason, event.get('title', ''), event.get('datetime', ''), event.get('source', ''), url, event.get('link', '')])
    counts = Counter(result[0] for result in results.values())
    print('\nDistinct URLs by result:')
    for key, count in counts.most_common():
        print(f'  {key}: {count}')
    problems = {'BROKEN_LOCAL', 'BROKEN_HTTP', 'NOT_IMAGE', 'INVALID', 'MISSING', 'HTTP_ERROR'}
    print('\nConfirmed / likely problems (up to 30 URLs):')
    shown = 0
    for url in urls:
        status, http, reason = results[url]
        if status in problems and shown < 30:
            event = by_url[url][0]
            print(f'  {status}: {event.get("title", "?")} | {event.get("source", "?")} | {url[:140]}')
            shown += 1
    print(f'\nReport saved: {report}')
    print('Note: BLOCKED, TIMEOUT, NETWORK_ERROR and SERVER_ERROR are inconclusive; do not auto-replace these images.')
    print('This script does not modify events.json or scraper files.')


if __name__ == '__main__':
    main()
