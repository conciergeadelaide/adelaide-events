"""Read-only Rhino Room gig-guide inspection. Does not touch events.json."""
import sys, re, json
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

BASE='https://rhinoroom.com.au/gig-guide/'
s=requests.Session()
s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36','Accept-Language':'en-AU,en;q=0.9'})

def inspect(url, detail=False):
    print('\n'+'='*75+'\nURL:',url)
    try:
        r=s.get(url,timeout=35); print('HTTP:',r.status_code,'FINAL:',r.url,'BYTES:',len(r.content)); r.raise_for_status()
    except Exception as exc:
        print('REQUEST ERROR:',repr(exc)); return []
    soup=BeautifulSoup(r.text,'html.parser')
    print('TITLE:',soup.title.get_text(' ',strip=True) if soup.title else '')
    for h in soup.find_all(['h1','h2','h3','h4'],limit=55):
        print('HEADING:',h.name,repr(h.get_text(' ',strip=True)[:180]),'class=',h.get('class'))
    print('\nDATE ELEMENTS:')
    for el in soup.select('time,[datetime],[class*=date],[class*=time]')[:70]:
        print(el.name,repr(el.get_text(' ',strip=True)[:150]),'datetime=',el.get('datetime'),'class=',el.get('class'))
    print('\nEVENT-LIKE LINKS:')
    links=[]; seen=set()
    for a in soup.find_all('a',href=True):
        href=urljoin(r.url,a['href']); label=a.get_text(' ',strip=True)[:110]
        if href in seen: continue
        seen.add(href)
        if urlparse(href).netloc.endswith('rhinoroom.com.au') or any(x in href.lower() for x in ('ticket','event','humanitix','moshtix','oztix','eventbrite','trybooking')):
            print(repr(label),'|',href)
            links.append((label,href))
            if len(links)>=110: break
    print('\nEVENT CONTAINERS / CARD SAMPLES:')
    for selector in ['article','.event','.event-card','.tribe-events-calendar-list__event','.ecs-event','.gig','.gig-card','.elementor-post','.wp-block-query article']:
        matches=soup.select(selector)
        if matches:
            print('SELECTOR:',selector,'COUNT:',len(matches))
            for item in matches[:4]:
                print('TEXT:',repr(item.get_text(' ',strip=True)[:650]))
                print('HTML:',str(item)[:2700])
    print('\nSTRUCTURED DATA:')
    for tag in soup.select('script[type="application/ld+json"]')[:12]:
        print((tag.string or tag.get_text())[:4000])
    print('\nIMAGES:')
    for img in soup.find_all('img')[:35]:
        print('ALT:',repr(img.get('alt','')[:70]),'SRC:',img.get('src'),'DATA:',img.get('data-src'),'SRCSET:',str(img.get('srcset') or img.get('data-srcset') or '')[:180])
    print('\nPAGINATION:')
    for a in soup.find_all('a',href=True):
        if any(x in (' '.join(a.get('class',[]))+' '+a.get_text(' ',strip=True)+' '+a['href']).lower() for x in ('next','page/','paged=','pagination','older')):
            print(a.get_text(' ',strip=True)[:90],urljoin(r.url,a['href']))
    return links

print('RHINO ROOM GIG GUIDE INSPECTION — READ ONLY')
links=inspect(BASE)
possible=[]
for label,url in links:
    path=urlparse(url).path.lower()
    if (url.rstrip('/')!=BASE.rstrip('/') and ('/event' in path or '/gig' in path or '/show' in path or '/comedy' in path)):
        possible.append(url)
print('\nDETAIL PAGES TO INSPECT:',possible[:4])
for url in possible[:4]: inspect(url,True)
print('\nINSPECTION COMPLETE')
