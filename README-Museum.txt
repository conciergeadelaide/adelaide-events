South Australian Museum source update.

Copy the Scraper folder into your existing adelaide-events repository, replacing the three Python files. Do not change events.json yet.

First test in CMD:
python Scraper\scrape.py --only "South Australian Museum"

Then:
python Scraper\scrape.py --quick --preview

Review results before running a live scrape or committing. This update has been syntax-tested, but live requests could not be executed in the build environment.
