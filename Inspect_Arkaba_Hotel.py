"""Read-only diagnostic for Arkaba Hotel events. Does not edit project files."""
import json
import sys
# Force UTF-8 when output is redirected in Windows Command Prompt.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

URL = 'https://www.arkabahotel.com.au/whats-on/'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36'}

def describe(soup, page_url, max_items=45):
    print('\nPAGE TITLE:', soup.title.get_text(' ', strip=True) if soup.title else '')
    print('\nHEADINGS (first 70):')
    for h in soup.find_all(re.compile(r'^h[1-6]$'))[:70]:
        print(h.name, repr(h.get_text(' ', strip=True)[:170]), 'class=', h.get('class'))
    print('\nEVENT-LIKE LINKS (first 100):')
    links = []
    seen = set()
    for a in soup.find_all('a', href=True):
        href = urljoin(page_url, a['href'])
        text = a.get_text(' ', strip=True)[:120]
        if href in seen or href.startswith(('mailto:', 'tel:')):
            continue
        if any(x in (href + ' ' + text).lower() for x in ('event', 'what', 'gig', 'show', 'ticket', 'book', 'music', 'comedy', 'arkaba')):
            seen.add(href)
            links.append((text, href))
    for text, href in links[:100]:
        print(repr(text), '|', href)
    print('\nDATE/TIME ELEMENTS (first 75):')
    pattern = re.compile(r'\b(?:20\d{2}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2})\b', re.I)
    found = 0
    for tag in soup.find_all(['time','h2','h3','h4','h5','h6','span','p','div']):
        if tag.name == 'div' and tag.find(['div','p','time','h2','h3','h4','h5','h6']):
            continue
        value = tag.get_text(' ', strip=True)
        if len(value) < 200 and pattern.search(value):
            print(tag.name, repr(value), 'datetime=', tag.get('datetime'), 'class=', tag.get('class'))
            found += 1
            if found >= 75: break
    print('\nJSON-LD (first 20 scripts, 2500 chars each):')
    for script in soup.find_all('script', type='application/ld+json')[:20]:
        print((script.string or script.get_text() or '')[:2500])
    print('\nIMAGES (first 35):')
    for img in soup.find_all('img')[:35]:
        print('alt=',repr(img.get('alt','')[:90]),'src=',str(img.get('src',''))[:250], 'data-src=',str(img.get('data-src',''))[:200])
    return links

print('ARKABA HOTEL INSPECTION — READ ONLY')
print('Source:', URL)
try:
    response = requests.get(URL, headers=HEADERS, timeout=40)
    print('STATUS:', response.status_code, 'BYTES:', len(response.content), 'FINAL URL:', response.url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'lxml')
    links = describe(soup, response.url)
    print('\nDETAIL PAGE SAMPLES (up to 4 same-site event pages):')
    selected = []
    for title, href in links:
        host = (urlparse(href).hostname or '').lower()
        path = urlparse(href).path.lower()
        if 'arkabahotel.com.au' in host and href.rstrip('/') != response.url.rstrip('/') and any(x in path for x in ('/event','/what','/gig','/show')):
            if href not in selected:
                selected.append(href)
        if len(selected) >= 4: break
    for href in selected:
        print('\n---',href,'---')
        try:
            detail = requests.get(href, headers=HEADERS, timeout=25)
            print('STATUS:', detail.status_code, 'BYTES:',len(detail.content))
            if detail.ok:
                d = BeautifulSoup(detail.text, 'lxml')
                print('TITLE:', d.title.get_text(' ',strip=True) if d.title else '')
                for h in d.find_all(['h1','h2','h3','time'])[:20]: print(h.name,repr(h.get_text(' ',strip=True)[:180]),'datetime=',h.get('datetime'))
                for m in d.find_all('meta',attrs={'property':re.compile('og:image|og:title')})[:5]:print('META',m.get('property'),m.get('content'))
                for s in d.find_all('script',type='application/ld+json')[:5]: print('JSON-LD', (s.string or s.get_text() or '')[:2500])
        except Exception as exc:print('DETAIL ERROR:',str(exc))
except Exception as exc:
    print('INSPECTION ERROR:',type(exc).__name__,str(exc))
print('\nINSPECTION COMPLETE')
