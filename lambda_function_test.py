from moto import mock_aws
import pytest
from lambda_function import lambda_handler
import boto3
import responses

def make_event():
    return {
        'erewash_council_news_url': "https://www.erewash.gov.uk/news"
    }

@pytest.fixture
def mock_dynamodb_articles():
    with mock_aws():
        # Set up DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-2')
        table = dynamodb.create_table(
            TableName='sources',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 1, 'WriteCapacityUnits': 1}
        )
        table.wait_until_exists()
        # Insert test data
        table.put_item(Item={"id": "1", "sourceId": "erewash_council_news", "dateAdded": "2026-06-08", "url": "https://www.erewash.gov.uk/news/test-article"})
        yield

@responses.activate
def test_retrieved_source_already_saved(mock_dynamodb_articles):

    page_url = "https://www.erewash.gov.uk/news"

    responses.add(
        responses.GET,
        page_url,
        body='<html><body><h2><a href="/news/test-article">Test Article</a></h2></body></html>',
        status=200,
        content_type='text/html'
    )

    lambda_handler(make_event(), None)

    assert len(responses.calls) == 1

    sources_table = boto3.resource('dynamodb', region_name='eu-west-2').Table('sources')
    result = sources_table.scan()
    assert result['Count'] == 1

