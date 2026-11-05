import requests,re
from bs4 import BeautifulSoup,Tag
u='https://www.unibaradl.com.au/'
r=requests.get(u,timeout=45,headers={'User-Agent':'Mozilla/5.0'})
s=BeautifulSoup(r.text,'html.parser')
print('STATUS',r.status_code,'BYTES',len(r.content))
print('EVENT STRUCTURE, each dated heading:')
for h in s.find_all(re.compile('^h[1-6]$')):
 date=h.get_text(' ',strip=True)
 if not re.fullmatch(r'\d{1,2}\s+[A-Za-z]{3,9}\s+20\d{2}',date):continue
 print('\n'+'='*60,'\nDATE',date)
 for depth in (1,2,3,4,5,6):
  p=h
  for _ in range(depth):p=p.parent if p else None
  if not p:break
  txt=p.get_text(' ',strip=True)
  a=p.find_all('a',href=True)
  imgs=p.find_all('img')
  print('ANCESTOR',depth,'tag',p.name,'class',str(p.get('class'))[:140], 'TEXT',repr(txt[:260]),'LINKS',len(a),'IMAGES',len(imgs))
  if a and imgs and len(txt)<800:
   print('LINKS',[(x.get_text(' ',strip=True)[:50],x.get('href','')[:170]) for x in a[:3]])
   print('IMAGES',[(x.get('src') or x.get('data-src') or '')[:230] for x in imgs[:3]])
   break
 print('PREVIOUS TEXT:')
 for p in list(h.find_all_previous(['h1','h2','h3','h4','h5','h6','p'],limit=5)):
  print(' ',p.name,repr(p.get_text(' ',strip=True)[:150]))
