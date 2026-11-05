"""Batch 8 read-only diagnostic for Botanic Gardens of South Australia.
Does not write or change events.json, parsers.py, or scrape.py.
Run from repository root: python Scraper\diagnose_botanic_gardens.py
Optional: python Scraper\diagnose_botanic_gardens.py https://.../whats-on/
"""
import collections
import re
import sys
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

URL = sys.argv[1] if len(sys.argv) > 1 else 'https://www.botanicgardens.sa.gov.au/whats-on/'
PATTERN = re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+20\d{2}\b', re.I)
RANGE = re.compile(r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d{2}\s*[-–—]\s*\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+20\d{2}\b', re.I)


def main():
    print('Batch 8 - Botanic Gardens READ-ONLY diagnostic')
    print('URL:', URL)
    response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36'}, timeout=35)
    print('HTTP:', response.status_code, 'Final URL:', response.url, 'HTML bytes:', len(response.content))
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    host = urlparse(response.url).hostname
    links = {}
    for a in soup.select('a[href]'):
        href = urljoin(response.url, a['href']).split('#')[0]
        parsed = urlparse(href)
        if parsed.hostname != host or '/whats-on/' not in parsed.path.lower() or parsed.path.rstrip('/').lower() == '/whats-on':
            continue
        links.setdefault(href, ' '.join(a.stripped_strings)[:120])
    print('Unique internal /whats-on/ detail links:', len(links))
    print('H3 headings:', len(soup.select('h3')))
    print('Links with nearby strict date ranges:', end=' ')
    strict = 0
    any_date = 0
    examples = []
    for url, title in links.items():
        link = soup.find('a', href=lambda h: bool(h) and urljoin(response.url, h).split('#')[0] == url)
        if not link:
            continue
        node = link
        found_range = False
        found_date = False
        for _ in range(6):
            node = node.parent
            if node is None:
                break
            txt = ' '.join(node.stripped_strings)
            if len(txt) > 1300:
                break
            found_range |= bool(RANGE.search(txt))
            found_date |= bool(PATTERN.search(txt))
        strict += found_range
        any_date += found_date
        if len(examples) < 20:
            examples.append((title, found_range, found_date, url))
    print(strict)
    print('Links with nearby at least one dated value:', any_date)
    print('Pagination-like links:')
    for a in soup.select('a[href]'):
        href = urljoin(response.url, a['href'])
        label = ' '.join(a.stripped_strings)
        if re.search(r'\b(next|load more|page\s*\d+)\b', label, re.I) or re.search(r'[?&](page|p|offset)=', href, re.I):
            print(' ', label[:65], '|', href[:180])
    print('Sample event links (strict-range, any-date):')
    for title, is_range, is_date, url in examples:
        print(' ', repr(title), is_range, is_date, url)
    print('READ ONLY: no project files changed.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Diagnostic failed:', type(exc).__name__, str(exc))
        sys.exit(1)
