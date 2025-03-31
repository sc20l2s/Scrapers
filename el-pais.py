import asyncio
import aiohttp
import re
import os
import sys
import calendar
import random
from tqdm.asyncio import tqdm_asyncio
from bs4 import BeautifulSoup
from urllib.parse import urljoin

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Base URL for El País Archive
ARCHIVE_URL = "https://elpais.com/hemeroteca/elpais/{year}/{month}/{day}/{edition}/portada.html"
ALT_ARCHIVE_URL = "https://static.elpais.com/hemeroteca/elpais/{year}/{month}/{day}/{edition}/portada.html" # Inconsistently formatted links, how naughty
EDITIONS = ["m", "t", "n"]  # morning afternoon and night

CONCURRENCY_LIMIT = 50  # Adjust based on politeness
semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

# Headers to avoid bot detection 
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

# Ensure a valid filename
def valid_filename(filename, default="elpais_archive.txt"):
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

async def fetch_page(session, url, alt_url=None, max_retries=5, base_delay=3):
    retries = 0
    while retries < max_retries:
        await asyncio.sleep(random.uniform(2, 5))  # Random delay between requests to evade bot detection
        try:
            async with session.get(url, headers=HEADERS, timeout=30) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status in [429, 503]:  # Server overloaded or too many requests
                    await asyncio.sleep(base_delay * (2 ** retries)) # Throttle our requests
                    retries += 1
                elif response.status in [403, 404] and alt_url:  # Switch to ALT URL, won't loop forever if alt url fails
                    return await fetch_page(session, alt_url, max_retries=max_retries)  # Recursive call to alt URL
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

        for edition in EDITIONS:
            url = ARCHIVE_URL.format(year=year, month=f"{month:02d}", day=f"{day:02d}", edition=edition)
            alt_url = ALT_ARCHIVE_URL.format(year=year, month=f"{month:02d}", day=f"{day:02d}", edition=edition)
            html = await fetch_page(session, url, alt_url)

            if not html:
                continue  # Skip

            soup = BeautifulSoup(html, "html.parser")

            for tag in soup.find_all(["h1", "h2", "h3"]):  # Scrape multiple headline levels
                link_tag = tag.find("a", href=True)
                if link_tag:
                    headline = link_tag.get_text(strip=True)
                    link = link_tag["href"]
                    
                    # Ensure absolute URL
                    if not link.startswith("http"):
                        link = urljoin("https://elpais.com", link)

                    if not keywords or any(keyword in headline.lower() for keyword in keywords): # Filter by keywords
                        articles.append({"headline": headline, "link": link})

        return articles

async def main():
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
        results = await tqdm_asyncio.gather(*tasks, desc="Scraping progress...")

    # Flatten list of lists and remove duplicates
    all_articles = { (article["headline"], article["link"]) for day_articles in results for article in day_articles }
    all_articles = [{"headline": headline, "link": link} for headline, link in all_articles]

    # Save results to a file
    with open(filename, "w", encoding="utf-8") as f:
        f.write(f"--== Extracted {len(all_articles)} articles from El País ({year}) ==--\n\n")
        for article in all_articles:
            f.write(f"{article['headline']}\n{article['link']}\n\n")

    print(f"Collected {len(all_articles)} articles. Results saved to {filename}")
    input("Press any key to exit.")

# Run the scraper
asyncio.run(main())