import logging

import requests
from bs4 import BeautifulSoup

from config import get_property
from db import get_latest_source

logger = logging.getLogger(__name__)

SOURCE_ID = "derbyshire_live"
_DEFAULT_MAX_PAGES = 1
_BASE_DOMAIN = "https://www.derbytelegraph.co.uk/news/"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    )
}

def scrape(base_url):
    max_pages_prop = 1 #get_property('derbyshire_live_max_pages')
    max_pages = int(max_pages_prop) if max_pages_prop else _DEFAULT_MAX_PAGES

    latest_db = None #get_latest_source(SOURCE_ID)
    latest_url = latest_db.get('url') if latest_db else None
    logger.debug("Latest DB article URL: %s", latest_url)

    articles = []

    for page in range(max_pages):
        page_url = f"{base_url}?pageNumber={page}" if page > 1 else base_url
        logger.debug("Fetching news listing page %d: %s", page, page_url)

        response = requests.get(page_url, headers=_HEADERS)
        if response.status_code != 200:
            logger.error("Failed to retrieve \"%s\" page: HTTP %s", page_url, response.status_code)
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        news_links = soup.select('div.teaser-text a')
        logger.debug("Found %d article links on page %d", len(news_links), page)

        done = False
        for link in news_links:
            href = link.get('href', '')
            full_url = f"{_BASE_DOMAIN}{href}" if href.startswith('/') else href

            if latest_url and full_url == latest_url:
                logger.debug("Reached latest known article (%s), stopping scrape", full_url)
                done = True
                break

            articles.append(_get_article(link))

        if done or not news_links:
            break

    logger.debug("Scraped %d articles total", len(articles))
    return articles


def _get_article(link):
    href = link.get('href')
    full_url = f"{_BASE_DOMAIN}{href}" if href.startswith('/') else href
    logger.debug("Scraping article: %s (%s)", link.get_text(strip=True), full_url)
    content = _scrape_article_content(full_url)
    return content, full_url


def _scrape_article_content(url):
    try:
        res = requests.get(url, headers=_HEADERS)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.find('article', id='article-body') or soup.find('div', class_='article-body')
        if content:
            paragraphs = content.find_all('p')
            logger.debug("Extracted %d paragraphs from %s", len(paragraphs), url)
            return "\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            logger.warning("Could not find article body at %s", url)
    except Exception as e:
        logger.error("Error scraping %s: %s", url, e)


scrape(_BASE_DOMAIN)