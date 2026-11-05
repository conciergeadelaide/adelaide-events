"""Read-only Jive gig-guide inspector. Does not change project files."""
import json, re
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

BASE='https://www.jivevenue.com/whats-on'
s=requests.Session(); s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0 Safari/537.36'})

def inspect(url, detail=False):
 print('\n'+'='*75+'\nURL:',url)
 try:
  r=s.get(url,timeout=30);print('STATUS:',r.status_code,'FINAL:',r.url,'BYTES:',len(r.content));r.raise_for_status()
 except Exception as e:print('REQUEST ERROR:',repr(e));return []
 soup=BeautifulSoup(r.text,'html.parser')
 print('TITLE:',soup.title.get_text(' ',strip=True) if soup.title else '')
 for tag in soup.select('script[type="application/ld+json"]')[:5]:print('JSON-LD:',tag.get_text(' ',strip=True)[:1800])
 print('WEBFLOW ELEMENTS:',[(x.get('class'),x.get('id')) for x in soup.select('[class*="collection-list"], [class*="w-dyn-item"], [class*="pagination"]')[:16]])
 print('DATE/TIME NODES:')
 for x in soup.find_all(['time','h1','h2','h3','h4'])[:45]:print(' ',x.name,'class=',x.get('class'),'datetime=',x.get('datetime'),'text=',x.get_text(' ',strip=True)[:140])
 print('EVENT CANDIDATE LINKS:')
 links=[]; seen=set()
 for a in soup.find_all('a',href=True):
  href=urljoin(r.url,a['href']);txt=a.get_text(' ',strip=True)
  if urlparse(href).netloc.endswith('jivevenue.com') and href not in seen and href.rstrip('/')!=BASE:
   seen.add(href); links.append(href)
   if len(links)<=65:
    parent=a
    for _ in range(3):
     if parent.parent:parent=parent.parent
    print(' LINK:',repr(txt[:100]),href)
    print('  PARENT:',str(parent)[:900].replace('\n',' '))
 print('IMAGES:',[(i.get('src','')[:150],i.get('data-src','')[:100],i.get('alt','')[:100]) for i in soup.select('img')[:18]])
 print('PAGINATION LINKS:',[(a.get_text(' ',strip=True),urljoin(r.url,a['href'])) for a in soup.select('a[href]') if any(k in (a.get('href') or '').lower() for k in ['page=','pagination','?page','?b'])][:30])
 if detail:
  print('PAGE TEXT:',soup.get_text(' ',strip=True)[:6500])
 return links

print('JIVE READ-ONLY INSPECTION')
links=inspect(BASE)
possible=[u for u in links if ('/event' in urlparse(u).path or '/whats-on/' in urlparse(u).path or '/show' in urlparse(u).path)]
print('\nDETAIL CANDIDATES:',len(possible))
for u in possible[:3]:inspect(u,detail=True)
print('\nINSPECTION COMPLETE - no files changed')
