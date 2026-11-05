"""Read-only Oztix public JavaScript search integration diagnostic."""
import re
import requests

URL = 'https://www.oztix.com.au/js/app.abc3f3e0.js'
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; event-feed-diagnostic/1.0)'}
print('Oztix search integration investigation')
try:
    r = requests.get(URL, headers=HEADERS, timeout=40)
    print('Bundle HTTP:', r.status_code, '| bytes:', len(r.content))
    r.raise_for_status()
    js = r.text
except requests.RequestException as exc:
    print('Could not retrieve JavaScript:', exc)
    raise SystemExit(1)

patterns = [
    ('Algolia calls', r'algoliasearch|instantsearch|searchClient|search-client|applicationID|applicationId|appId|apiKey|indexName|indices'),
    ('Oztix search references', r'algolia|oztix|searchResults|search-results|facetFilters|facetName|venues|The Gov'),
]
for heading, pat in patterns:
    print('\n###', heading)
    matches = list(re.finditer(pat, js, re.I))
    print('Total matches:', len(matches))
    for match in matches[:35]:
        start = max(0, match.start() - 200)
        end = min(len(js), match.end() + 250)
        snippet = js[start:end].replace('\n', ' ')
        # Public client-side keys are not needed for this diagnostic.
        snippet = re.sub(r'(?i)(apiKey|searchKey|applicationId|appId)(["\']?\s*[:=]\s*["\'])[A-Za-z0-9_-]{12,}', r'\1\2[REDACTED]', snippet)
        print('OFFSET', match.start(), '|', snippet[:500])
print('\nDone. No project files were modified.')
