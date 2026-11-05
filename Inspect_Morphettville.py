"""Read-only Morphettville page structure inspector. Does not modify project files."""
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

URLS = [
    'https://morphettville.com.au/',
    'https://morphettville.com.au/racing/',
    'https://morphettville.com.au/about/race-day-calendar/',
    'https://morphettville.com.au/upcoming-events/',
    'https://morphettville.com.au/whats-on/',
    'https://morphettville.com.au/spring-carnival/',
]
s = requests.Session()
s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36'})
for url in URLS:
    print('\n' + '='*75 + '\nPAGE:',url)
    try:
        r=s.get(url,timeout=25)
        print('HTTP:',r.status_code,'HTML bytes:',len(r.content),'Final URL:',r.url)
        r.raise_for_status()
    except requests.RequestException as exc:
        print('ERROR:',exc)
        continue
    soup=BeautifulSoup(r.text,'lxml')
    print('TITLE:',soup.title.get_text(' ',strip=True) if soup.title else '')
    print('EVENT JSON-LD:')
    for script in soup.select('script[type="application/ld+json"]')[:8]:
        value=script.get_text(' ',strip=True)
        print(' ',value[:650])
    print('RELEVANT HEADINGS / NEARBY TEXT:')
    for h in soup.select('h1,h2,h3,h4'):
        t=h.get_text(' ',strip=True)
        if not t:continue
        par=h.parent
        print(' ',h.name,repr(t[:100]),'| parent:',par.name,repr(' '.join(par.get('class',[])))[:90], '| text:',repr(par.get_text(' ',strip=True)[:240]))
    print('EVENT / BOOKING LINKS (up to 45):')
    seen=set()
    for a in soup.select('a[href]'):
        label=a.get_text(' ',strip=True)
        href=urljoin(r.url,a.get('href',''))
        if (href,label) in seen:continue
        seen.add((href,label))
        if not (re.search(r'event|race|book|ticket|festival|calendar|carnival|showman|cup|day',label+' '+href,re.I)):continue
        img=a.find('img')
        imgurl=urljoin(r.url,img.get('data-src') or img.get('src') or '') if img else ''
        parent=a.parent
        print(' ',repr(label[:95]),'|',href[:175], '| IMG',imgurl[:160], '| PARENT',parent.name,repr(' '.join(parent.get('class',[]))))
        if len(seen)>300:break
    print('DATE TAGS (up to 35):')
    for tag in soup.select('time[datetime], [data-date], [data-event-date], [itemprop="startDate"]')[:35]:
        print(' ',str(tag)[:300])
print('\nFinished. No project files changed.')
