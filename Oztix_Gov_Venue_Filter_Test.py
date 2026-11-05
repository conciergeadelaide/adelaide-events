"""Read-only Oztix venue-filter diagnostic. Does not touch project files."""
import json,re,requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlencode
s=requests.Session();s.headers.update({'User-Agent':'Mozilla/5.0'})
try:
 r=s.get('https://www.oztix.com.au/search/',timeout=30);r.raise_for_status()
 soup=BeautifulSoup(r.text,'html.parser')
 js=next(urljoin(r.url,t['src']) for t in soup.select('script[src]') if '/js/app.' in t['src'])
 code=s.get(js,timeout=40).text
 def setting(k):return re.search(r'\b'+k+r':"([^"]+)"',code).group(1)
 app=setting('ALGOLIA_APPLICATION_ID');key=setting('ALGOLIA_PERSONALISATION_API_KEY')
 endpoint=f'https://{app.lower()}-dsn.algolia.net/1/indexes/*/queries'
 h={'X-Algolia-Application-Id':app,'X-Algolia-API-Key':key,'Content-Type':'application/json'}
 tests=[('Baseline: the gov',{'query':'the gov'}),('Venue ID filter 2437',{'query':'','filters':'Venue.Id=2437'}),('Venue ID filter 4633',{'query':'','filters':'Venue.Id=4633'}),('Venue name facet main',{'query':'','facetFilters':json.dumps(['Venue.Name:The Gov - The Venue'])}),('Venue name facet Gibson',{'query':'','facetFilters':json.dumps(['Venue.Name:The Gov - The Gibson Stage'])}),('Venue names in query',{'query':'The Gov - The Venue'}),('Hindmarsh query',{'query':'Hindmarsh'})]
 for label,params in tests:
  params.update(hitsPerPage=5,page=0)
  try:
   x=s.post(endpoint,headers=h,json={'requests':[{'indexName':'prod_oztix_eventguide','params':urlencode(params)}]},timeout=35)
   j=x.json();res=(j.get('results') or [{}])[0]
   print('\nTEST',label,'HTTP',x.status_code,'HITS',res.get('nbHits'),'PAGES',res.get('nbPages'),'ERROR',res.get('message',''))
   for hit in res.get('hits',[])[:3]:print(' ',hit.get('EventName'), '|', (hit.get('Venue') or {}).get('Name'), '|',hit.get('DateStart'))
  except Exception as e:print('ERROR',str(e))
except Exception as e:print('SETUP ERROR',repr(e))
print('\nNo project files modified.')
