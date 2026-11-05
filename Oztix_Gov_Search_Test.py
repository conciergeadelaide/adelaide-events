"""Read-only diagnostic for publicly exposed Oztix event-search data."""
import json
import re
import requests

bundle_url = 'https://www.oztix.com.au/js/app.abc3f3e0.js'
s = requests.Session()
s.headers.update({'User-Agent': 'Mozilla/5.0'})
try:
    r = s.get(bundle_url, timeout=30)
    r.raise_for_status()
    js = r.text
    def config(name):
        match = re.search(r'\b' + re.escape(name) + r':"([^"]+)"', js)
        if not match:
            raise ValueError('Missing public site configuration: ' + name)
        return match.group(1)
    app_id = config('ALGOLIA_APPLICATION_ID')
    api_key = config('ALGOLIA_PERSONALISATION_API_KEY')
    endpoint = 'https://' + app_id.lower() + '-dsn.algolia.net/1/indexes/*/queries'
    headers = {
        'X-Algolia-Application-Id': app_id,
        'X-Algolia-API-Key': api_key,
        'Content-Type': 'application/json',
    }
    payload = {'requests': [
        {'indexName': 'prod_oztix_eventguide', 'params': 'query=the%20gov&hitsPerPage=5'},
        {'indexName': 'prod_oztix_eventguide', 'params': 'query=&hitsPerPage=5&facetFilters=%5B%5B%22Venues%3AThe%20Gov%20-%20The%20Venue%22%5D%5D'},
    ]}
    response = s.post(endpoint, headers=headers, json=payload, timeout=30)
    print('ALGOLIA STATUS:', response.status_code)
    print('RESPONSE BYTES:', len(response.content))
    if not response.ok:
        print('ERROR:', response.text[:1500])
    else:
        result = response.json()
        for i, section in enumerate(result.get('results', []), 1):
            print('\nQUERY', i, '| total hits:', section.get('nbHits'), '| pages:', section.get('nbPages'))
            for hit in section.get('hits', [])[:5]:
                clean = {k: v for k, v in hit.items() if not k.startswith('_')}
                print(json.dumps(clean, ensure_ascii=False)[:3000])
except Exception as exc:
    print('DIAGNOSTIC ERROR:', type(exc).__name__, str(exc))
print('\nRead-only test complete. No project files changed.')
