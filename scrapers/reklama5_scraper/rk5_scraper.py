# Created by Milos Smiljkovikj, Boris Manev
# Github: https://github.com/milos55, https://github.com/NorksX
# Date: 08/02/2025
import os
from zoneinfo import ZoneInfo

import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime
import psycopg2
from ad import Ad
import time
import re


# CONFIG

DB_HOST = os.getenv('POSTGRES_HOST', "localhost")
DB_USER = os.getenv('POSTGRES_USER', "postgres")
DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 1234)
DB_NAME = os.getenv('POSTGRES_DB', "ad_db")

DB_CONFIG = {
    "user": DB_USER,
    "password": DB_PASSWORD,
    "database": DB_NAME,
    "host": DB_HOST,
    "port": 5432,
}

# === COLOR CONSTANTS FOR ERROR PRINTS ===
RED = '\033[31m'
RESET = '\033[0m'
YELLOW = '\033[33m'
GREEN = '\033[32m'

# Made config parameters in seperate block for readability and scalability

START_PAGE = int(os.getenv('START_PAGE', 1))
END_PAGE = int(os.getenv('END_PAGE', 4))
BATCH_SIZE = int(os.getenv('BATCH_SIZE', 3))
URL = "https://www.reklama5.mk/Search?city=&cat=0&q="
ASYNC_TIMEOUT = 2

ADMIN_NUMBERS = []  # List of admin numbers to be used for notifications or checks, currently empty, haven't checked


# MAIN CODE

async def fetch_page(session, URL, retries=3, delay=2):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.reklama5.mk",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Accept-Language": "en-US,en-GB,en;q=0.9",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
    }

    for attempt in range(retries):
        try:
            async with session.get(URL, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    print(f"Attempt {attempt + 1}: Failed to fetch {URL} (status {response.status})")

        except Exception as e:
            print(f"Attempt {attempt + 1}: Error fetching {URL} - {e}")

        if attempt < retries - 1:
            await asyncio.sleep(delay)  # Wait before retrying

    print(f"Giving up on {URL} after {retries} attempts.")
    return None


def parse_date(date_str):
    if not date_str or date_str.strip() == "N/A":
        return None

    # Ensure UTF-8 handling if input is bytes
    if isinstance(date_str, bytes):
        date_str = date_str.decode("utf-8")

    tz = ZoneInfo("Europe/Skopje")

    # Replace "Денес" with today's date in Skopje timezone
    if "Денес" in date_str:
        today_str = datetime.now(tz).strftime("%d.%m.%Y")
        date_str = date_str.replace("Денес", today_str)

    if "Today" in date_str:
        today_str = datetime.now(tz).strftime("%d.%m.%Y")
        date_str = date_str.replace("Today", today_str)

    # Try full datetime
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        return dt.replace(tzinfo=tz)
    except ValueError:
        pass

    # Try date only
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y")
        return dt.replace(tzinfo=tz)
    except ValueError:
        return None


def normalize_phone_number(
        phone):
    phone = phone.strip().replace(' ', '')  #

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

def sanitize_unicode(text):
    if text is None:
        return None
    return text.encode('utf-8', errors='replace').decode('utf-8')


async def fetch_ads(URL, START_PAGE, END_PAGE, BATCH_SIZE):
    baseurl = "https://www.reklama5.mk"
    ads = []

    async with aiohttp.ClientSession() as session:
        for batch_start in range(START_PAGE, END_PAGE + 1, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE - 1, END_PAGE)
            print(f"Scraping pages {batch_start} to {batch_end}")

            tasks = [fetch_page(session, f"{URL}&page={page}") for page in range(batch_start, batch_end + 1)]
            pages_responses = await asyncio.gather(*tasks)

            for page_num, page_content in zip(range(batch_start, batch_end + 1), pages_responses):
                if page_content is None:
                    continue

                soup = BeautifulSoup(page_content, "html.parser")
                helper = soup.find_all('div', class_='ad-desc-div col-lg-6 text-left')
                image_helper = soup.find_all('div', class_='ad-image-div col-lg-4 text-left')

                if not helper or not image_helper:
                    print(f"No ads found on page {page_num}.")
                    continue

                for ad, image_ad in zip(helper, image_helper):
                    try:
                        title = ad.find('a', class_='SearchAdTitle').text.strip()
                        price_text = ad.find('span', class_='search-ad-price').text.strip().replace('\r\n', '').replace(
                            ' ', '')
                        category = ad.find('a', class_='text-secondary').find('small').text if ad.find('a',
                                                                                                       class_='text-secondary').find(
                            'small') else None
                        link = baseurl + ad.find('a', class_='SearchAdTitle')['href']

                        image_url = image_ad.find("div", class_="ad-image")["style"].split("url(")[-1].split(")")[
                            0].strip("'\"")
                        image_url = "https:" + image_url if image_url.startswith("//") else image_url

                        location_span = ad.find('span', class_='city-span')
                        if location_span:
                            location_text = location_span.text.strip()  # Extract text from the span
                            location_text = location_text.replace('•', '').strip()  # Remove unwanted characters
                        else:
                            location_text = None

                        pos = next((i for i, c in enumerate(price_text) if not (c.isdigit() or c == '.')),
                                   len(price_text))
                        price_str = price_text[:pos].replace('.', '')
                        price = int(price_str) if price_str else 0
                        currency = price_text[pos:]

                        store = "reklama5"



                        ad_response = await fetch_page(session, link)
                        if ad_response:
                            ad_soup = BeautifulSoup(ad_response, "html.parser")
                            description = ad_soup.find('p', class_='mt-3').text.strip() if ad_soup.find('p',
                                                                                                           class_='mt-3') else None

                            # Get raw phone number(s)
                            raw_phone = ad_soup.find('h6').get_text(strip=True) if ad_soup.find('h6') else None

                            # Format and filter phone numbers
                            if raw_phone:
                                phone = [normalize_phone_number(raw_phone)]
                            else:
                                phone = {"NONE FOUND"}

                            date_element = ad_soup.find_all('div', class_='col-4 align-self-center')
                            date = parse_date(date_element[2].find('span').text.strip()) if len(
                                date_element) > 2 else None


                        if not location_text:
                            print(f"{RED}Skipping ad (missing location): {link}{RESET}")  # Location error
                        if not phone:
                            print(f"{YELLOW}Missing phone number: {link}{RESET}")  # Phone error
                        if not description:
                            print(f"{RED}Skipping ad (missing description): {link}{RESET}")  # Description error

                        ad = Ad(
                            title=sanitize_unicode(title),
                            description=sanitize_unicode(description),
                            link=link,
                            image_url=image_url,  #
                            category=category,
                            phone=[sanitize_unicode(num) for num in phone],
                            date=date,
                            price=str(price) if price else None,
                            currency=sanitize_unicode(currency),
                            location=sanitize_unicode(location_text),
                            store="reklama5"
                        )
                        print("=" * 80)
                        print(ad.to_tuple())
                        print("=" * 30)
                        if not ad.date:
                            print(
                                f"{RED}[DEBUG] Missing parsed date! Raw input: {date_element[2].find('span').text.strip()}{RESET}")
                        insert_ad_to_db(ad)



                    # Check page on which an error occured
                    except Exception as e:
                        print(f"Error processing ad on page {page_num}: {e}")

            print(f"Finished scraping pages {batch_start} to {batch_end}")
            await asyncio.sleep(ASYNC_TIMEOUT)




# Updated to work with class ad
def insert_ad_to_db(ad):
    try:
        with psycopg2.connect(
                host=DB_HOST,
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME
        ) as conn:
            with conn.cursor() as cursor:

                # Handle price
                ad_price = "По Договор" if ad.price == 0 else str(ad.price)

                cursor.execute('''
                    INSERT INTO ads.ads (title, description, link, image_url, category, phone, date, price, currency, location, store)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    ad.title,
                    ad.description,
                    ad.link,
                    ad.image_url,
                    ad.category,
                    ad.phone,
                    ad.date,
                    ad_price,
                    ad.currency,
                    ad.location,
                    ad.store
                ))
                print(f"{GREEN}Ad '{ad.title}' inserted into the database.{RESET}")
    except psycopg2.Error as e:
        print(f"{RED}Error inserting ad: {e}{RESET}")


# === MODIFIED MAIN FUNCTION ===
async def main():
    start_time = time.time()
    await fetch_ads(URL, START_PAGE, END_PAGE, BATCH_SIZE)
    total_time = time.time() - start_time
    print(f"Total time: {total_time:.2f} seconds")


# REMOVED PARAMS IN MAIN BECAUSE THEY ARE GLOBAL
if __name__ == "__main__":
    asyncio.run(main())