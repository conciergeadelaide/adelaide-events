"""Public Humanitix event discovery for Adelaide and nearby SA regions.

Uses public HTML and Event JSON-LD only. No private API or credentials.
Site layout may change: inspect dry-run counts before publishing.
"""
import json
import html
import re
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36"}
HOST_URL = "https://events.humanitix.com/host/nineteentenadl"
DIRECTORIES = [
    "https://humanitix.com/au/events/au--sa--adelaide",
    "https://humanitix.com/au/events/au--south-australia",
    "https://humanitix.com/au/events/au--sa--mclaren-vale",
    "https://humanitix.com/au/events/au--sa--glenelg",
    "https://humanitix.com/au/events/au--sa--hahndorf",
]
# South Australian towns/suburbs, with conservative checks for regional listings.
SA_PLACES = (
    'adelaide','north adelaide','glenelg','brighton','henley beach','semaphore',
    'port adelaide','unley','norwood','prospect','kent town','thebarton',
    'hindmarsh','bowden','woodville','modbury','marion','morphett vale',
    'noarlunga','victor harbor','victor harbour','mclaren vale','mclaren flat',
    'willunga','aldinga','maslin beach','barossa','tanunda','nuriootpa',
    'angaston','lyndoch','greenock','seppeltsfield','gawler','rowland flat',
    'hahndorf','mount barker','mt barker','stirling','aldgate','bridgewater',
    'crafers','lobethal','woodside','balhannah','birdwood','gumeracha',
    'littlehampton','mount lofty','mt lofty','belair','blackwood','mitcham',
    'goodwood','fullarton','wayville','morphettville','torrensville',
    'west lakes','findon','northfield','magill','payneham','walkerville',
    'beaumont','burnside','parkside','mile end','fulham','plympton',
    'south australia',' sa ','sa 5','sa 50','sa 51','sa 52','sa 53',
)
EXCLUDED = ('online event','online only','virtual event','webinar','zoom meeting')
EVENT_LINK = re.compile(r'^https://events\.humanitix\.com/[^/?#]+/?$', re.I)
RESERVED_SLUGS = {'host', 'hosts', 'event', 'events', 'login', 'signup',
                  'register', 'search', 'help', 'contact', 'about', 'privacy',
                  'terms', 'checkout', 'organiser', 'organizer'}
# The region directories below are discovery entry points, not comprehensive indexes.
# Only add verified URLs: the previous Adelaide Hills/Barossa slugs returned 404.



def _fetch(session,url):
    response=session.get(url,timeout=25,allow_redirects=True)
    response.raise_for_status()
    return BeautifulSoup(response.text,'lxml')


def _valid_event_url(raw, base):
    url = urljoin(base, html.unescape(str(raw)).replace('\\/', '/'))
    parts = urlsplit(url)
    if parts.scheme not in ('http', 'https') or (parts.hostname or '').lower() != 'events.humanitix.com':
        return ''
    slug = parts.path.strip('/')
    if not slug or '/' in slug or slug.lower() in RESERVED_SLUGS:
        return ''
    clean = f'https://events.humanitix.com/{slug}'
    return clean if EVENT_LINK.fullmatch(clean) else ''


def _event_links(soup, base):
    links = set()
    for anchor in soup.find_all('a', href=True):
        url = _valid_event_url(anchor['href'], base)
        if url:
            links.add(url)
    # Include URLs embedded in JSON and other page data, excluding host routes.
    markup = str(soup).replace('\\/', '/')
    for match in re.finditer(r'https?://events\.humanitix\.com/[^\s"\'<>?#\\]+', markup, re.I):
        url = _valid_event_url(match.group(0), base)
        if url:
            links.add(url)
    return links


def _json_events(soup):
    def walk(obj):
        if isinstance(obj,list):
            for x in obj:yield from walk(x)
        elif isinstance(obj,dict):
            t=obj.get('@type',[])
            types=t if isinstance(t,list) else [t]
            if any(str(v).lower().endswith('event') for v in types) and obj.get('startDate'):
                yield obj
            for k in ('@graph','itemListElement'):
                if k in obj:yield from walk(obj[k])
            if 'item' in obj:yield from walk(obj['item'])
    for script in soup.find_all('script',type='application/ld+json'):
        try:yield from walk(json.loads(script.string or script.get_text()))
        except (ValueError,TypeError):continue


def _image(value):
    if isinstance(value,list):return _image(value[0]) if value else ''
    if isinstance(value,dict):return str(value.get('url') or value.get('contentUrl') or '')
    return str(value or '')


def _location(loc):
    if isinstance(loc,list):return _location(loc[0]) if loc else ('','')
    if isinstance(loc,str):return loc,''
    if not isinstance(loc,dict):return '',''
    name=html.unescape(str(loc.get('name') or ''))
    address=loc.get('address') or {}
    if isinstance(address,dict):
        address=' '.join(str(address.get(k) or '') for k in ('streetAddress','addressLocality','addressRegion','postalCode','addressCountry'))
    return name,html.unescape(str(address))


def _in_scope(venue,address,host_only=False):
    if host_only:return True
    combined=' '+re.sub(r'\s+',' ',(venue+' '+address).lower())+' '
    if any(x in combined for x in EXCLUDED):return False
    # Match complete place phrases, not fragments within unrelated words.
    return any(re.search(r'(?<![a-z])'+re.escape(place.strip())+r'(?![a-z])',combined) for place in SA_PLACES if place.strip())


def _date_reason(value):
    if not value:
        return 'missing start date'
    try:
        start = datetime.fromisoformat(str(value).strip().replace('Z', '+00:00'))
        # Compare against the desk PC's local date (Adelaide) without requiring tzdata.
        if start.date() < datetime.now().date():
            return 'past date'
        return ''
    except (ValueError, TypeError):
        return 'invalid start date'


def _date_is_future(value):
    return not _date_reason(value)


def _category(title):
    lower = title.casefold()
    if any(k in lower for k in ('burlesque', 'drag', 'cabaret', 'theatre', 'opera', 'circus')):
        return ['Theatre']
    if any(k in lower for k in ('music', 'concert', 'dj ', 'live band', 'gig', 'jazz')):
        return ['Music']
    if any(k in lower for k in ('wine', 'food', 'dinner', 'tasting')):
        return ['Food & Beverage']
    if any(k in lower for k in ('workshop', 'class', 'masterclass')):
        return ['Conferences/Workshops/Expos']
    return ['Other']


def _event_decision(item, url, host_only):
    title = html.unescape(str(item.get('name') or '')).strip()
    start = str(item.get('startDate') or '').strip()
    venue, address = _location(item.get('location'))
    detail = f'title={title or "(none)"!r}, date={start or "(none)"!r}, venue={venue or "(none)"!r}, address={address or "(none)"!r}'
    if not title:
        return None, 'missing title', detail
    reason = _date_reason(start)
    if reason:
        return None, reason, detail
    if host_only:
        # A Humanitix host may advertise events held elsewhere.
        physical = venue + ' ' + address
        if not re.search(r'\b(?:nineteen\s*ten|19\s*ten)\b', physical, re.I):
            return None, 'venue is not confirmed as Nineteen Ten', detail
        venue = 'Nineteen Ten'
    elif not _in_scope(venue, address):
        return None, 'outside target area or online-only', detail
    if not venue:
        venue = address.split(',')[0].strip()
    if not venue:
        return None, 'missing venue', detail
    event = {'title': title, 'venue': venue, 'date': start,
             'end_date': str(item.get('endDate') or ''),
             'category': _category(title),
             'image': _image(item.get('image')), 'url': url}
    return event, '', detail


def _parse_page(soup, url, host_only=False):
    return [event for item in _json_events(soup)
            for event, reason, detail in [_event_decision(item, url, host_only)]
            if event is not None]


def _next_directory_link(soup, current_url):
    """Follow only explicit pagination links on the same Humanitix directory."""
    current=urlsplit(current_url)
    for a in soup.find_all('a',href=True):
        label=' '.join(a.stripped_strings).casefold()
        rel=' '.join(a.get('rel') or []).casefold()
        aria=str(a.get('aria-label') or '').casefold()
        if not ('next' in rel or 'next' in aria or label in ('next','next page','›','→')):
            continue
        candidate=urljoin(current_url,a['href'])
        parts=urlsplit(candidate)
        if parts.hostname != current.hostname or parts.path.rstrip('/') != current.path.rstrip('/'):
            continue
        if candidate != current_url:
            return candidate
    return ''


def scrape_humanitix(host_only=False,max_event_pages=350):
    """Collect publicly discoverable upcoming events with safe diagnostics.

    This does not guarantee a complete Humanitix catalogue. It follows only
    directory pagination explicitly exposed in the HTML, up to five pages.
    """
    sources=[HOST_URL] if host_only else DIRECTORIES
    urls=set()
    reachable=0
    with requests.Session() as session:
        session.headers.update(HEADERS)
        for base in sources:
            page_url=base
            seen_pages=set()
            for page_no in range(1,6):
                if not page_url or page_url in seen_pages:
                    break
                seen_pages.add(page_url)
                try:
                    soup=_fetch(session,page_url)
                    reachable+=1
                    found=_event_links(soup,page_url)
                    new=found-urls
                    urls.update(found)
                    print(f'    Humanitix listing: {len(found)} links, {len(new)} new ({page_url})')
                    page_url=_next_directory_link(soup,page_url)
                except requests.RequestException as exc:
                    print(f'    Humanitix listing unavailable: {page_url} ({exc})')
                    break
        if reachable==0:
            raise RuntimeError('No Humanitix listing pages reachable')
        if not urls:
            print('    Humanitix: no event links discovered')
            return []
        results = []
        failures = 0
        no_event_data = 0
        excluded = 0
        rejected_examples = []
        rejection_counts = {}
        for index, url in enumerate(sorted(urls)[:max_event_pages]):
            try:
                soup = _fetch(session, url)
                structured = list(_json_events(soup))
                if not structured:
                    no_event_data += 1
                    reason = 'no Event JSON-LD'
                    rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
                    rejected_examples.append((reason, url, ''))
                else:
                    accepted_on_page = 0
                    for item in structured:
                        event, reason, detail = _event_decision(item, url, host_only)
                        if event is not None:
                            results.append(event)
                            accepted_on_page += 1
                        else:
                            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
                            rejected_examples.append((reason, url, detail))
                    if not accepted_on_page:
                        excluded += 1
            except requests.RequestException as exc:
                failures += 1
                reason = 'fetch failed'
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
                rejected_examples.append((reason, url, str(exc)[:130]))
            time.sleep(0.12)
        unique={}
        for e in results:
            unique[(e['title'].casefold(),e['venue'].casefold(),e['date'])]=e
        print(f'    Humanitix: {len(urls)} links, {len(unique)} verified events, {failures} page failures')
        print(f'    Humanitix diagnostics: {no_event_data} without Event JSON-LD, {excluded} filtered event pages')
        for reason, count in sorted(rejection_counts.items()):
            print(f'      Rejection reason: {reason}: {count}')
        # Print all host diagnostics, with a bounded regional sample.
        max_examples = 100 if host_only else 25
        for reason, url, detail in rejected_examples[:max_examples]:
            print(f'      Skipped ({reason}): {url}')
            if detail:
                print(f'        {detail}')
        if len(rejected_examples) > max_examples:
            print(f'      ... {len(rejected_examples)-max_examples} additional rejected items not displayed')
        if len(urls)>max_event_pages:
            print(f'    Humanitix: capped at {max_event_pages} event pages; directory coverage incomplete')
        return list(unique.values())
