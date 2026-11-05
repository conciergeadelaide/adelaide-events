"""Read-only image diagnostic for Norwood Concert Hall event pages.
Run in adelaide-events project root: python Inspect_Norwood_Images.py
Does not modify any file.
"""
import json, re, html
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

path=Path('events.json')
if not path.exists():
    print('ERROR: Run this from your adelaide-events project folder.'); raise SystemExit(1)
events=json.loads(path.read_text(encoding='utf-8-sig'))
items=[e for e in events if e.get('venue','').casefold()=='norwood concert hall' and 'norwoodconcerthall.com.au' in e.get('link','')]
print(f'Total events: {len(events)}; official Norwood records: {len(items)}')
s=requests.Session();s.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36'})
for e in items:
    u=e['link']; print('\n'+'='*70+'\n'+e.get('title','')+'\n'+u)
    try:
        r=s.get(u,timeout=25); print('HTTP:',r.status_code,'HTML bytes:',len(r.content));r.raise_for_status()
        soup=BeautifulSoup(r.text,'html.parser'); candidates=[]
        def add(kind,url):
            if not url:return
            url=html.unescape(str(url).strip())
            if url.startswith('data:'):return
            url=urljoin(u,url)
            if url not in [v for _,v in candidates]:candidates.append((kind,url))
        for m in soup.find_all('meta'):
            if 'image' in (m.get('property','')+' '+m.get('name','')).lower():add('META '+str(m.get('property') or m.get('name')),m.get('content'))
        for tag in soup.find_all(['img','source']):
            for attr in ('src','data-src','data-original','data-lazy-src','srcset','data-srcset'):
                val=tag.get(attr,'')
                if val:
                    for entry in val.split(',')[:5]:add(tag.name+' '+attr,entry.strip().split(' ')[0])
        for tag in soup.find_all(style=True):
            for match in re.findall(r'url\([\'\"]?([^\)\'\"]+)',tag['style'],re.I):add('inline background',match)
        for match in re.findall(r'https?[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)(?:\?[^\s"\'<>]*)?',r.text,re.I):add('HTML image URL',match)
        for kind,url in candidates[:18]:print(' ',kind+':',url[:230])
        if not candidates:print(' NO IMAGE CANDIDATES FOUND')
    except Exception as exc:print(' ERROR:',type(exc).__name__,str(exc)[:240])
print('\nDone. events.json has NOT been modified.')
