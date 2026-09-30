import requests
from bs4 import BeautifulSoup

url = "https://www.adelaidecc.com.au/events/"

headers = {
    "User-Agent": "Mozilla/5.0"
}

response = requests.get(
    url,
    headers=headers,
    timeout=30
)

soup = BeautifulSoup(response.text, "lxml")

keywords = [
    "MICHELIN",
    "Phil Hoffmann",
    "Starlit Christmas",
    "Interstellar"
]

for keyword in keywords:

    matches = soup.find_all(
        string=lambda text: text and keyword.lower() in text.lower()
    )

    for match in matches:

        element = match.parent

        if element.name not in ["h2"]:
            continue

        print("\n======================================")
        print("EVENT:", element.get_text(" ", strip=True))
        print("======================================")

        # Find the containing event card
        container = element

        for _ in range(5):
            if container.parent:
                container = container.parent

            text = container.get_text(" ", strip=True)

            if "Learn more" in text:
                break

        print("\nCONTAINER:")
        print(container.prettify()[:12000])