import logging
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Attr

logger = logging.getLogger(__name__)

dynamodb = boto3.resource("dynamodb", region_name='eu-west-2')
table = dynamodb.Table('sources')


def get_latest_source(source_id):
    response = table.scan(
        FilterExpression=Attr("sourceId").eq(source_id)
    )
    items = response["Items"]
    return max(items, key=lambda x: x["dateAdded"], default=None)


def save_source(url, source_id, content):
    """Returns True if saved, False if already existed."""
    get_item_response = table.get_item(Key={"id": url, "sourceId": source_id})
    if "Item" in get_item_response and get_item_response["Item"] is not None:
        return False
    table.put_item(Item={
        "id": url,
        "sourceId": source_id,
        "dateAdded": datetime.now().strftime("%Y-%m-%d"),
        "url": url,
        "content": content or "",
        "writtenAbout": False
    })
    logger.debug("Saved source to DB: %s", url)
    return True
