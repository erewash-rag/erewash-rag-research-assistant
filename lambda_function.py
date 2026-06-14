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
        base_url = event.get(f"{scraper.SOURCE_ID}_url") or get_property(f"{scraper.SOURCE_ID}_url")
        sources = scraper.scrape(base_url)
        for content, url in sources:
            if db.save_source(url, scraper.SOURCE_ID, content):
                total_saved += 1

    logger.info("Added %d sources to the DB", total_saved)
    return {"statusCode": 200, "body": f"Added {total_saved} sources to the DB"}


if __name__ == "__main__":
    lambda_handler({}, None)
