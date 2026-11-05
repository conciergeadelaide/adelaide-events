"""Read-only diagnostics for Oztix event discovery. Does not edit events.json."""
import json
import re
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

S = requests.Session()
S.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36', 'Accept-Language':'en-AU,en;q=0.9'})
URLS = [
 'https://www.oztix.com.au/search/?q=the%20gov&venues%5B0%5D=The%20Gov%20-%20The%20Venue',
 'https://www.oztix.com.au/search/',
 'https://www.moshtix.com.au/v2/venues/the-gov-adelaide/923',
]
for url in URLS:
 print('\nPAGE',url)
 try:
  r=S.get(url,timeout=25)
  print('STATUS',r.status_code,'BYTES',len(r.content),'FINAL',r.url)
  soup=BeautifulSoup(r.text,'html.parser')
  scripts=[urljoin(r.url,x['src']) for x in soup.find_all('script',src=True)]
  print('SCRIPTS',len(scripts))
  for src in scripts[:30]:print(' JS',src)
  print('JSON-LD',len(soup.select('script[type="application/ld+json"]')))
  print('EVENT-LINKS',len({a.get('href') for a in soup.find_all('a',href=True) if re.search(r'event|ticket',a.get('href',''),re.I)}))
  print('PAGE API HINTS',list(dict.fromkeys(re.findall(r'https?[^\s"\']{0,150}(?:api|graphql|search)[^\s"\']{0,100}',r.text,re.I)))[:10])
  if 'oztix.com.au/search/' in r.url:
   for src in scripts[:12]:
    if not src.startswith('https://www.oztix.com.au/') and not src.startswith('https://oztix.com.au/'):
     continue
    try:
     js=S.get(src,timeout=20)
     print(' BUNDLE',js.status_code,len(js.content),src)
     if not js.ok or len(js.content)>3000000:continue
     found=list(dict.fromkeys(re.findall(r'(?i)(?:https?://[^\s"\'`]{5,180}|/[a-z0-9_/-]*(?:graphql|api|search|event)[a-z0-9_/?&=.-]{3,140})',js.text)))
     for match in found[:18]:print('  HINT',match[:180])
    except requests.RequestException as e:print(' BUNDLE ERROR',str(e)[:160])
 except requests.RequestException as e:print('ERROR',str(e)[:250])
print('\nDiagnostic finished; no files modified.')
