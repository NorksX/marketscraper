import os
from datetime import datetime
import re
import aiohttp
import asyncio

import psycopg2
from bs4 import BeautifulSoup, NavigableString
import time
from ad import Ad

# === COLOR CONSTANTS ===
RED = '\033[31m'
YELLOW = '\033[33m'
GREEN = '\033[32m'
RESET = '\033[0m'

# === CONFIGURATION ===
START_PAGE = int(os.getenv('START_PAGE', 1))
END_PAGE = int(os.getenv('END_PAGE', 4))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 3))
BASE_URL = "https://forum.it.mk"
ASYNC_TIMEOUT = 2
URL_TEMPLATE = "https://forum.it.mk/oglasnik/categories/prodavam.1/?page={page}"

DB_HOST = os.getenv('DB_HOST', "localhost")
DB_USER = os.getenv('DB_USER', "postgres")
DB_PASSWORD = os.getenv('DB_PASSWORD', 1234)
DB_NAME = os.getenv('DB_NAME', "ad_db")

MONTHS_SHORT = {
    "јануари": "January",
    "февруари": "February",
    "март": "March",
    "април": "April",
    "мај": "May",
    "јуни": "June",
    "јули": "July",
    "август": "August",
    "септември": "September",
    "октомври": "October",
    "ноември": "November",
    "декември": "December"
}
def parse_date(date_str):
    """Convert Macedonian date string to datetime.date object"""
    if not date_str:
        return None
    parts = date_str.split()
    if len(parts) != 3:
        return None
    day, mk_month, year = parts
    eng_month = MONTHS_SHORT.get(mk_month.lower())
    if not eng_month:
        return None
    eng_date_str = f"{day} {eng_month} {year}"
    try:
        dt = datetime.strptime(eng_date_str, "%d %B %Y")
        return dt.date()
    except Exception:
        return None

def split_price_and_currency(price_text):
    match = re.match(r'^(\S+)\s(\S+)$', price_text)
    if match:
        price = match.group(1).replace('.', '')
        currency = match.group(2)
        if currency == "ден.":
            currency = "МКД"
        return price, currency
    return None, None


def sanitize_unicode(text):
    if text is None:
        return None
    return text.encode('utf-8', errors='replace').decode('utf-8')


def extract_description(soup): #FIXME ima redundant new lines for some reason
    try:
        # Try the exact selector first
        desc_container = soup.select_one(
            'div.p-body-main.p-body-main--withSidebar '
            'div.p-body-content '
            'div:nth-child(4) '
            'div div div article div.bbWrapper'
        )

        # Fallback to simpler selector if needed
        if not desc_container:
            desc_container = soup.select_one('article div.bbWrapper')

        if desc_container:
            # Create a copy to avoid modifying original parse tree
            desc_copy = BeautifulSoup(desc_container.decode_contents(), 'html.parser')

            # Replace <br> tags with newlines while preserving multiple breaks
            for br in desc_copy.find_all('br'):
                br.replace_with('\n')

            # Get text with preserved newlines
            text = desc_copy.get_text().strip()
            # Normalize consecutive newlines (2+ become 2 newlines)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return sanitize_unicode(text)
    except Exception as e:
        print(f"{RED}Description extraction error: {e}{RESET}")
    return None

def clean_description(description):
    # Replace 2 or more consecutive blank lines with a single blank line
    cleaned_text = re.sub(r'(\n\s*){2,}', '\n\n', description)
    return cleaned_text.strip()

def extract_phones(description):
    pattern = r'(\+?389\s?0?\d{2}\s?\d{3}\s?\d{3}|\+?389\s?\d{2}\s?\d{3}\s?\d{3}|0\d{2}\s?\d{3}\s?\d{3}|\d{2}\s?\d{3}\s?\d{3})'
    matches = re.findall(pattern, description)
    # Clean up whitespace in matches
    phones = [re.sub(r'\s+', '', m) for m in matches]
    return phones if phones else ["NONE FOUND"]

def normalize_phone_number(phone):
    phone = phone.strip().replace(' ', '')

    # Collapse multiple leading pluses to one
    while phone.startswith('++'):
        phone = phone[1:]

    # Helper for Macedonian numbers
    def macedonian_local_format(ndigits):
        ndigits = re.sub(r'\D', '', ndigits)
        # Add leading zero if number is 8 digits (e.g., '78326371' -> '078326371')
        if len(ndigits) == 8:
            ndigits = '0' + ndigits
        if len(ndigits) == 9:
            return f"{ndigits[:3]} {ndigits[3:6]} {ndigits[6:]}"
        return None

    # +389 or 00389
    if phone.startswith('+389'):
        return macedonian_local_format(phone[4:])
    if phone.startswith('00389'):
        return macedonian_local_format(phone[5:])

    # Foreign number: starts with + but not +389
    if phone.startswith('+'):
        return phone

    # Local number (possibly with leading zero or just 8 digits)
    return macedonian_local_format(phone)

# === FETCHING FUNCTIONS ===
async def fetch_page(session, url, retries=3, delay=2):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.pazar3.mk/",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive"
    }

    for attempt in range(retries):
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    return await response.text()
                print(f"{RED}Attempt {attempt + 1}: Status {response.status} for {url}{RESET}")
        except Exception as e:
            print(f"{RED}Attempt {attempt + 1}: Error fetching {url} - {e}{RESET}")
        if attempt < retries - 1:
            await asyncio.sleep(delay)
    return None


# === MAIN SCRAPING FUNCTION ===
async def scrape_forum_ads():
    all_ads = []
    async with aiohttp.ClientSession() as session:
        for page in range(START_PAGE, END_PAGE + 1):
            page_url = URL_TEMPLATE.format(page=page)
            print(f"{YELLOW}Processing page {page}: {page_url}{RESET}")

            html = await fetch_page(session, page_url)
            if not html:
                continue

            soup = BeautifulSoup(html, 'html.parser')
            ad_containers = soup.select('div.structItem--listing')

            if not ad_containers:
                print(f"{RED}No ads on page {page}{RESET}")
                continue

            # Process each ad container
            for ad in ad_containers:
                try:
                    # Extract basic info
                    title_tag = ad.select_one('div.structItem-title > a')
                    title = sanitize_unicode(title_tag.text.strip()) if title_tag else None
                    link = f"{BASE_URL}{title_tag['href']}" if title_tag else None


                    img_tag = ad.select_one('div.structItem-cell--icon img')
                    image_url = f"{BASE_URL}{img_tag['src']}" if img_tag and img_tag.get('src') else None

                    price_span = ad.select_one('div.structItem-cell--main ul li span')
                    price_text = price_span.text.strip() if price_span else None

                    if price_text and price_text == "ПРОЦЕНКА":
                        price = "По Договор"
                    elif price_text and price_text == "ИСТЕЧЕН":
                        print(f"{RED}ISTECEN{RESET}")
                    else:
                        price, currency = split_price_and_currency(price_text)


                    time_tag = ad.select_one('time.u-dt')
                    date_obj = None
                    if time_tag and 'datetime' in time_tag.attrs:
                        iso_date = time_tag['datetime'][:10]
                        date_obj = datetime.strptime(iso_date, "%Y-%m-%d").date()

                    category_tag = ad.select_one(
                        'div.structItem-cell--main div.structItem-minor ul li:nth-child(3) > a')
                    category = category_tag.text.strip() if category_tag else None  # Extract text

                    # Fetch description from detail page
                    description = None
                    if link:
                        detail_html = await fetch_page(session, link)
                        if detail_html:
                            detail_soup = BeautifulSoup(detail_html, 'html.parser')
                            description = extract_description(detail_soup)
                            description = clean_description(description)

                    phone = extract_phones(description or "")
                    if phone and "NONE FOUND" not in phone:
                        normalized_phones = []
                        for num in phone:
                            norm = normalize_phone_number(num)
                            if norm:
                                normalized_phones.append(norm)
                        phone = normalized_phones if normalized_phones else ["NONE FOUND"]

                    # Create Ad instance
                    ad = Ad(
                        title=title,
                        description=description,
                        link=link,
                        image_url=image_url,
                        date=date_obj,
                        price=price,
                        currency=sanitize_unicode(currency),
                        phone=[sanitize_unicode(num) for num in phone],
                        location="None",
                        category=category,
                        store="forum_it"
                    )

                    # Insert to DB and print
                    #insert_ad_to_db(ad_instance)
                    print(f"{GREEN}Scraped Ad:{RESET}")
                    print(f"Title: {ad.title}")
                    print(f"Price: {ad.price}")
                    print(f"Currency: {ad.currency}")
                    print(f"Date: {ad.date}")
                    print(f"Link: {ad.link}")
                    print(f"Image: {ad.image_url}")
                    print(f"Phone: {ad.phone}")
                    print(f"Description: {description if description else 'N/A'}")
                    print("-" * 60)

                except Exception as e:
                    print(f"{RED}Error processing ad: {e}{RESET}")

                insert_ad_to_db(ad)
                # Small delay between ads
                await asyncio.sleep(2)


def insert_ad_to_db(ad_instance):
    try:
        with psycopg2.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute('''
                         INSERT INTO ads.ads (title, description, link, image_url, category, phone, date, price, currency, location, store)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                     ''', (
                    ad_instance.title,
                    ad_instance.description,
                    ad_instance.link,
                    ad_instance.image_url,
                    ad_instance.category,
                    ad_instance.phone,
                    ad_instance.date,
                    ad_instance.price,
                    ad_instance.currency,
                    ad_instance.location,
                    ad_instance.store
                ))
                print(f"{GREEN}Ad inserted: {ad_instance.title}{RESET}")
    except psycopg2.Error as e:
        print(f"{RED}DB Error: {e}{RESET}")
# === MAIN FUNCTION ===
async def main():
    start_time = time.time()
    await scrape_forum_ads()
    print(f"Total time: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())