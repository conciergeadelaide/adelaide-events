import requests
from bs4 import BeautifulSoup

url = "https://www.adelaidefestivalcentre.com.au/whats-on"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}

response = requests.get(url, headers=headers, timeout=30)

soup = BeautifulSoup(response.text, "lxml")

target = soup.find(
    "a",
    href="https://www.adelaidefestivalcentre.com.au/whats-on/death-of-a-salesman"
)

if not target:
    print("Death of a Salesman link was not found.")
else:
    print("FOUND EVENT")
    print("=" * 60)

    parent = target

    for i in range(5):
        if parent.parent:
            parent = parent.parent

    print(parent.prettify()[:12000])