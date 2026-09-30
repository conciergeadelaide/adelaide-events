import requests
from bs4 import BeautifulSoup

url = "https://www.adelaideoval.com.au/whats-on/"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}

response = requests.get(
    url,
    headers=headers,
    timeout=30
)

print("Status:", response.status_code)
print("Downloaded:", len(response.text), "characters")

soup = BeautifulSoup(response.text, "lxml")

print("\nPAGE TITLE:")
print(soup.title.get_text(strip=True) if soup.title else "None")

print("\nJSON-LD BLOCKS:")
scripts = soup.find_all("script", type="application/ld+json")
print("Found:", len(scripts))

for script in scripts[:10]:
    print("\n--- JSON-LD ---")
    print(script.get_text(strip=True)[:2000])

print("\nLINKS CONTAINING EVENT/CONCERT/GAME:")
count = 0

for link in soup.find_all("a", href=True):
    text = link.get_text(" ", strip=True)

    if any(
        word in text.lower()
        for word in [
            "event",
            "concert",
            "game",
            "match",
            "show",
            "2026"
        ]
    ):
        print(text[:150], "|", link["href"])
        count += 1

        if count >= 30:
            break