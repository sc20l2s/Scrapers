import asyncio
import aiohttp
import re
import os
import sys
import calendar
import random
from bs4 import BeautifulSoup
from urllib.parse import urljoin

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

CONCURRENCY_LIMIT = 5  # Adjust based on politeness
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# Base URL for lemonde Archive
ARCHIVE_URL = "https://www.lemonde.fr/archives-du-monde/{day}-{month}-{year}/{page}/"

USER_AGENTS = [ # France's defenses are formidable, need to randomise our user agent
    # Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:114.0) Gecko/20100101 Firefox/114.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.89 Safari/537.36",

    # macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36",

    # Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",

    # Android
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.6045.134 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.5938.144 Mobile Safari/537.36",

    # iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.1"
]


HEADERS = {
    "User-Agent": random.choice(USER_AGENTS),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

# Ensure a valid filename
def valid_filename(filename, default="lemonde_archive.txt"): # sounds like lemon in my head
    folder = "scrape_results"
    os.makedirs(folder, exist_ok=True)  # Create the folder if it doesn't exist

    if not filename.strip():
        filename = default
    else:
        filename = re.sub(r'[<>:"/\\|?*]', "", filename).strip()
        filename = filename.replace(".", "") + ".txt"

    filepath = os.path.join(folder, filename)

    # Create the file if it doesn’t exist
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("")
    
    return filepath

async def fetch_page(session, url, max_retries=5, base_delay=3):
    retries = 0
    while retries < max_retries:
        await asyncio.sleep(random.uniform(5, 10))  # Random delay between requests to evade bot detection
        try:
            async with session.get(url, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status in [429, 503]:  # Server overloaded or too many requests
                    await asyncio.sleep(base_delay * (2 ** retries))  # Throttle our requests
                    retries += 1
                elif response.status == 404:  # If page doesn't exist, skip
                    print(f"Page not found: {url}")
                    return None
                else:
                    print(f"Failed to fetch {url} (Status: {response.status})")
                    return None
        except asyncio.TimeoutError:
            await asyncio.sleep(base_delay * (2 ** retries))  # Throttle our requests
            retries += 1
        except aiohttp.ClientError as e:
            print(f"Network error fetching {url}: {e}")
            return None
    print(f"Failed after {max_retries} retries: {url}")
    return None

# Scrape articles in parallel
async def scrape_archive(session, year, month, day, keywords):
    async with semaphore:
        articles = []
        page = 1

        while True:
            url = ARCHIVE_URL.format(day=f"{day:02d}", month=f"{month:02d}", year=year, page=page)
            html = await fetch_page(session, url)

            if not html:
                break  # Stop on 404 or error

            soup = BeautifulSoup(html, "html.parser")
            teasers = soup.find_all("a", class_="teaser__link")

            if not teasers:
                break  # Stop if no article links found (could be an empty page)

            for teaser in teasers:
                headline_tag = teaser.find("h3", class_="teaser__title")
                if headline_tag:
                    headline = headline_tag.text.strip()
                    link = teaser["href"]
                    if not link.startswith("http"):
                        link = urljoin("https://www.lemonde.fr", link)
                    if not keywords or any(kw in headline.lower() for kw in keywords):
                        articles.append({"headline": headline, "link": link})

            page += 1  # Go to next page

        return articles

async def main():
    print("The French have strong defenses! This one takes a looong time ")
    kw = input("Enter keywords separated by commas (empty for all articles): ").strip()
    keywords = None if not kw else [word.strip().lower() for word in kw.split(",") if word.strip()]
    filename = valid_filename(input("Enter file to save results (empty for default): "))

    year = input("Enter year to scrape (be aware some years have pages missing): ").strip()
    if not year.isdigit():
        print("Invalid year.")
        return

    year = int(year)
    async with aiohttp.ClientSession() as session:
        tasks = [
            scrape_archive(session, year, month, day, keywords)
            for month in range(1, 13)  # Iterate through months
            for day in range(1, calendar.monthrange(year, month)[1] + 1)  # Iterate through days
        ]
        results = await asyncio.gather(*tasks)

    # Flatten list of lists and remove duplicates
    all_articles = { (article["headline"], article["link"]) for day_articles in results for article in day_articles }
    all_articles = [{"headline": headline, "link": link} for headline, link in all_articles]

    # Save results to a file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"--== Extracted {len(all_articles)} articles from Lemonde ({year}) ==--\n\n")
        for article in all_articles:
            f.write(f"{article['headline']}\n{article['link']}\n\n")

    print(f"Collected {len(all_articles)} articles. Results saved to {filename}")
    input("Press any key to exit.")

# Run the scraper
asyncio.run(main())
