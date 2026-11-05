"""Read-only inspection of UniBar ADL event listings for the Adelaide events scraper."""
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re

URL = 'https://www.unibaradl.com.au/'
print('UniBar ADL source inspection', flush=True)
try:
    response = requests.get(URL, headers={'User-Agent': 'Mozilla/5.0 (compatible; AdelaideEvents/1.0)'}, timeout=35)
    print('HTTP status:', response.status_code, 'HTML bytes:', len(response.content))
    response.raise_for_status()
except Exception as exc:
    print('FETCH ERROR:', repr(exc))
    raise SystemExit(1)
soup = BeautifulSoup(response.text, 'html.parser')
for tag in soup(['script','style','noscript']):
    if tag.name != 'script' or tag.get('type') != 'application/ld+json':
        tag.decompose()
print('\nHEADINGS:')
for h in soup.find_all(re.compile('^h[1-6]$'))[:110]:
    print(h.name, repr(h.get_text(' ', strip=True)[:180]), 'class=', h.get('class'))
print('\nLINKS NEAR EVENTS (first 110):')
links=[]
for a in soup.find_all('a',href=True):
    href=urljoin(URL,a['href']); title=a.get_text(' ',strip=True)
    if any(k in href.lower() for k in ['moshtix','ticket','unibaradl.com.au/','event','gig']) or re.search(r'2026|2027|tickets',title,re.I):
        links.append((title[:100],href, str(a.get('class',''))[:120]))
for item in links[:110]: print(*item, sep=' | ')
print('\nIMAGES (first 35):')
for im in soup.find_all('img')[:35]:
    print('alt=',repr(im.get('alt')), 'src=',str(im.get('src'))[:200], 'data-src=',str(im.get('data-src'))[:200], 'parent=',im.parent.name)
print('\nDATE-CONTAINING TEXT (first 65):')
for node in soup.find_all(string=re.compile(r'\b(?:Oct|Nov|Dec|Jan|Feb|Mar|2026|2027)\b',re.I))[:65]:
    print(repr(str(node).strip()[:180]),'parent=',node.parent.name,'class=',node.parent.get('class'))
print('\nJSON-LD:')
for x in soup.find_all('script',type='application/ld+json')[:5]: print(x.get_text(' ',strip=True)[:900])
print('\nINSPECTION COMPLETE')
