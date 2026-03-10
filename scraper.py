import cloudscraper
from bs4 import BeautifulSoup

_scraper = cloudscraper.create_scraper()


def search(word: str) -> list[dict]:
    url = f"https://tureng.com/tr/turkce-ingilizce/{word.strip()}"
    response = _scraper.get(url, timeout=10)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("table", id="englishResultsTable")
    if not tables:
        return []

    results = []
    for table in tables[:2]:  # first two: direct + reverse direction
        for row in table.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) != 5:
                continue

            category = tds[1].get_text(strip=True)
            en_anchor = tds[2].find("a")
            tr_anchor = tds[3].find("a")
            type_tag = tds[2].find("i")

            if not en_anchor or not tr_anchor:
                continue

            results.append({
                "category": category,
                "en": en_anchor.get_text(strip=True),
                "tr": tr_anchor.get_text(strip=True),
                "type": type_tag.get_text(strip=True) if type_tag else "",
            })

    return results
