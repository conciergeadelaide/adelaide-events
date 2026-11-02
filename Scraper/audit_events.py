"""Read-only quality audit for the What's On Adelaide events.json file.
Run from repository root: python Scraper\audit_events.py
Outputs a CSV and text summary in reports/; never edits events.json.
"""
import csv
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'events.json'
REPORT_DIR = ROOT / 'reports'
FIELDS = ['priority', 'issue', 'title', 'venue', 'datetime', 'end_datetime', 'source', 'link', 'notes']


def clean(value):
    return ' '.join(str(value or '').casefold().split())


def main():
    if not DATA.is_file():
        raise SystemExit(f'Cannot find {DATA}. Put this script in the Scraper folder.')
    with DATA.open(encoding='utf-8') as handle:
        events = json.load(handle)
    if not isinstance(events, list):
        raise SystemExit('events.json must contain a JSON list; nothing changed.')
    today = date.today()
    issues = []
    source_counts = Counter()
    groups = defaultdict(list)

    def flag(event, priority, issue, notes=''):
        issues.append({'priority': priority, 'issue': issue,
                       'title': str(event.get('title') or ''),
                       'venue': str(event.get('venue') or ''),
                       'datetime': str(event.get('datetime') or ''),
                       'end_datetime': str(event.get('end_datetime') or ''),
                       'source': str(event.get('source') or ''),
                       'link': str(event.get('link') or event.get('url') or ''),
                       'notes': notes})

    for index, event in enumerate(events, 1):
        if not isinstance(event, dict):
            flag({}, 'HIGH', 'Invalid record', f'Item {index} is not an object')
            continue
        source = str(event.get('source') or '')
        source_counts[source or '(unknown)'] += 1
        title = str(event.get('title') or '').strip()
        venue = str(event.get('venue') or '').strip()
        raw_start = str(event.get('datetime') or '').strip()
        raw_end = str(event.get('end_datetime') or '').strip()
        link = str(event.get('link') or event.get('url') or '').strip()
        if not title or not venue or not raw_start or not link:
            flag(event, 'HIGH', 'Missing essential field',
                 'Check title, venue, datetime and link')
        start = None
        if raw_start:
            try:
                start = datetime.fromisoformat(raw_start)
            except ValueError:
                flag(event, 'HIGH', 'Invalid start date', 'Cannot parse datetime')
        if raw_end:
            try:
                end = datetime.fromisoformat(raw_end)
                if start and end < start:
                    flag(event, 'HIGH', 'End before start', 'Check date range')
            except ValueError:
                flag(event, 'HIGH', 'Invalid end date', 'Cannot parse end_datetime')
        if start:
            if start.date() < today and not raw_end:
                flag(event, 'MEDIUM', 'Past start date without end date',
                     'May be an expired listing or an ongoing event; verify')
            if start.strftime('%H:%M') == '00:00':
                flag(event, 'MEDIUM', 'Midnight / unknown start time',
                     'May be a placeholder or a genuine all-day event; verify before publishing a time')
            groups[(clean(title), clean(venue), start.date().isoformat())].append(event)
        if not str(event.get('image') or '').strip():
            flag(event, 'LOW', 'Missing image', 'Check whether an official image is available')
        if source == 'Adelaide Festival Centre':
            flag(event, 'MEDIUM', 'Manual review: Adelaide Festival Centre',
                 'Automated source is blocked; check current date, time, cancellation and link')

    for key, members in groups.items():
        if len(members) < 2:
            continue
        exact_times = Counter(str(e.get('datetime') or '') for e in members)
        if any(n > 1 for n in exact_times.values()):
            flag(members[0], 'MEDIUM', 'Possible duplicate performance',
                 f'{len(members)} records share title/venue/date; at least two share a start time. Check before removing.')
        else:
            flag(members[0], 'INFO', 'Multiple performances on one day',
                 f'{len(members)} different start times; likely legitimate sessions. Do not merge automatically.')

    priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2, 'INFO': 3}
    issues.sort(key=lambda x: (priority_order.get(x['priority'], 9), x['issue'], x['datetime'], x['title']))
    REPORT_DIR.mkdir(exist_ok=True)
    csv_path = REPORT_DIR / 'event_audit.csv'
    with csv_path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(issues)
    issue_counts = Counter(x['issue'] for x in issues)
    lines = [f"WHAT'S ON ADELAIDE - READ-ONLY AUDIT", f'Audit date: {today.isoformat()}',
             f'Events checked: {len(events)}', f'Flags raised: {len(issues)}',
             '', 'FLAGS BY TYPE:']
    lines += [f'  {name}: {count}' for name, count in issue_counts.most_common()]
    lines += ['', 'EVENTS BY SOURCE:']
    lines += [f'  {name}: {count}' for name, count in source_counts.most_common()]
    lines += ['', 'NOTE: Flags are review candidates, not confirmed errors.',
              'No event records were changed. No website data was published.']
    summary_path = REPORT_DIR / 'event_audit_summary.txt'
    summary_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines[:5]))
    print(f'\nExcel report: {csv_path}')
    print(f'Text summary: {summary_path}')


if __name__ == '__main__':
    main()
