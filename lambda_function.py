import logging
import os

import db
from config import get_property
from scrapers import SCRAPERS

logger = logging.getLogger(__name__)
logging.getLogger().setLevel(os.environ.get("logging_level", "INFO"))


def lambda_handler(event, _context):
    total_saved = 0
    for scraper in SCRAPERS:
        sources_per_scraper = 0
        logger.info("Scraping from %s...", scraper.SOURCE_ID)
        base_url = event.get(f"{scraper.SOURCE_ID}_url") or get_property(f"{scraper.SOURCE_ID}_url")
        sources = scraper.scrape(base_url)
        for content, url in sources:
            if db.save_source(url, scraper.SOURCE_ID, content):
                sources_per_scraper += 1
                total_saved += 1
        logger.info("%d saved to DB for source %s", scraper.SOURCE_ID)

    logger.info("Added %d sources total to the DB", total_saved)
    return {"statusCode": 200, "body": f"Added {total_saved} sources to the DB"}


if __name__ == "__main__":
    lambda_handler({}, None)
