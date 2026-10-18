"""Read-only test of the Tourism Commission parser. Does not edit events.json."""
from parsers import parse_south_australia_tourism

results = parse_south_australia_tourism(None, "https://southaustralia.com/destinations/adelaide/what-s-on")
print("Eligible tourism events:", len(results))
for event in results[:20]:
    print(event["date"], "|", event["title"], "|", event["venue"])
