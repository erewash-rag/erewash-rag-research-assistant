import requests
from bs4 import BeautifulSoup
import time
import os
import logging
import boto3
from boto3.dynamodb.conditions import Attr
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

client = boto3.client('dynamodb', region_name='eu-west-2')
dynamodb = boto3.resource("dynamodb", region_name='eu-west-2')
table = dynamodb.Table('sources')

def get_latest_source_from_db(source_id):
    response = table.scan(
        FilterExpression=Attr("sourceId").eq(source_id)
    )

    items = response["Items"]

    return max(
        items,
        key=lambda x: x["dateAdded"],
        default=None
    )

DEFAULT_MAX_PAGES = 2

def scrape_erewash_council_news(base_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
    }

    max_pages_prop = get_property('erewash_council_max_pages')
    max_pages = int(max_pages_prop) if max_pages_prop else DEFAULT_MAX_PAGES

    latest_db = get_latest_source_from_db("erewash_council_news")
    latest_url = latest_db.get('url') if latest_db else None
    logger.info("Latest DB article URL: %s", latest_url)

    articles = []

    for page in range(max_pages):
        page_url = f"{base_url}?page={page}" if page > 0 else base_url
        logger.info("Fetching news listing page %d: %s", page, page_url)

        response = requests.get(page_url, headers=headers)
        if response.status_code != 200:
            logger.error("Failed to retrieve news page: HTTP %s", response.status_code)
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        news_links = soup.select('h2 a')
        logger.info("Found %d article links on page %d", len(news_links), page)

        done = False
        for link in news_links:
            href = link.get('href', '')
            full_url = f"https://www.erewash.gov.uk{href}" if href.startswith('/') else href

            if latest_url and full_url == latest_url:
                logger.info("Reached latest known article (%s), stopping scrape", full_url)
                done = True
                break

            articles.append(get_article_text(link, headers))

        if done or not news_links:
            break

    logger.info("Scraped %d articles total", len(articles))
    return articles
        

def get_article_text(link, headers):
    title = link.get_text(strip=True)
    href = link.get('href')
    
    # Ensure the link is a full URL
    if href.startswith('/'):
        full_url = f"https://www.erewash.gov.uk{href}"
    else:
        full_url = href

    logger.info("Scraping article: %s (%s)", title, full_url)
    article_content = scrape_article_content(full_url, headers)
    return article_content, full_url


def scrape_article_content(url, headers):
    try:
        res = requests.get(url, headers=headers)
        article_soup = BeautifulSoup(res.text, 'html.parser')
        
        # 3. Extract the main text
        # Most gov sites put the main body in an <article> or a specific <div>
        content_div = article_soup.find('div', class_='item-page') or article_soup.find('article')
        
        if content_div:
            paragraphs = content_div.find_all('p')
            full_text = "\n".join([p.get_text(strip=True) for p in paragraphs])
            logger.debug("Extracted %d paragraphs from %s", len(paragraphs), url)
            return full_text
        else:
            logger.warning("Could not find article body at %s", url)

    except Exception as e:
        logger.error("Error scraping %s: %s", url, e)

def get_property(key):
    return os.environ.get(key) or get_local_property(key)

def get_local_property(key):
    try:
        with open("properties.txt") as fp:
            for line in fp:
                k, _, v = line.strip().partition(":")
                if k == key:
                    return v
    except FileNotFoundError:
        return None

def lambda_handler(event, _context):
    erewash_council_news_url = event.get('erewash_council_news_url')
    
    if erewash_council_news_url is None:
        erewash_council_news_url = get_property('erewash_council_news_url')

    sources = scrape_erewash_council_news(erewash_council_news_url)
    for content, url in sources:
        table.put_item(Item={
            "id": url,
            "sourceId": "erewash_council_news",
            "dateAdded": datetime.now().strftime("%Y-%m-%d"),
            "url": url,
            "content": content or ""
        })
    logger.info("Added %d sources to the DB", len(sources))


if __name__ == "__main__":
    lambda_handler({}, None)