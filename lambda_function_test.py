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
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}, {'AttributeName': 'sourceId', 'KeyType': 'RANGE'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}, {'AttributeName': 'sourceId', 'AttributeType': 'S'}],
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

@responses.activate
def test_new_source_saved(mock_dynamodb_articles):
    page_url = "https://www.erewash.gov.uk/news"
    new_article_url = "https://www.erewash.gov.uk/news/new-article"

    responses.add(
        responses.GET,
        page_url,
        body='<html><body><h2><a href="/news/new-article">New Article</a></h2></body></html>',
        status=200,
        content_type='text/html'
    )
    responses.add(
        responses.GET,
        new_article_url,
        body='<html><body><article><p>New article content</p></article></body></html>',
        status=200,
        content_type='text/html'
    )
    responses.add(
        responses.GET,
        f"{page_url}?page=1",
        body='<html><body><h2><a href="/news/test-article">Test Article</a></h2></body></html>',
        status=200,
        content_type='text/html'
    )

    lambda_handler(make_event(), None)

    assert len(responses.calls) == 3

    sources_table = boto3.resource('dynamodb', region_name='eu-west-2').Table('sources')
    result = sources_table.scan()
    assert result['Count'] == 2
    saved_urls = [item['url'] for item in result['Items']]
    assert new_article_url in saved_urls

@responses.activate
def test_new_sources_on_page_1_until_known_article_found(mock_dynamodb_articles):
    page_url = "https://www.erewash.gov.uk/news"
    new_slugs = ['article-a', 'article-b', 'article-c']

    responses.add(
        responses.GET,
        page_url,
        body=''.join(f'<h2><a href="/news/{s}">{s}</a></h2>' for s in new_slugs),
        status=200,
        content_type='text/html'
    )
    for slug in new_slugs:
        responses.add(
            responses.GET,
            f"https://www.erewash.gov.uk/news/{slug}",
            body=f'<html><body><article><p>Content of {slug}</p></article></body></html>',
            status=200,
            content_type='text/html'
        )
    responses.add(
        responses.GET,
        f"{page_url}?page=1",
        body='<html><body><h2><a href="/news/test-article">Test Article</a></h2></body></html>',
        status=200,
        content_type='text/html'
    )

    lambda_handler(make_event(), None)

    assert len(responses.calls) == 5  # page 0 + 3 article details + page 1

    sources_table = boto3.resource('dynamodb', region_name='eu-west-2').Table('sources')
    result = sources_table.scan()
    assert result['Count'] == 4  # 1 original + 3 new
    saved_urls = [item['url'] for item in result['Items']]
    for slug in new_slugs:
        assert f"https://www.erewash.gov.uk/news/{slug}" in saved_urls

@responses.activate
def test_max_pages_reached_no_known_article_found(mock_dynamodb_articles):
    page_url = "https://www.erewash.gov.uk/news"
    page_0_slugs = ['article-a', 'article-b']
    page_1_slugs = ['article-c', 'article-d']

    responses.add(
        responses.GET,
        page_url,
        body=''.join(f'<h2><a href="/news/{s}">{s}</a></h2>' for s in page_0_slugs),
        status=200,
        content_type='text/html'
    )
    for slug in page_0_slugs:
        responses.add(
            responses.GET,
            f"https://www.erewash.gov.uk/news/{slug}",
            body=f'<html><body><article><p>Content of {slug}</p></article></body></html>',
            status=200,
            content_type='text/html'
        )
    responses.add(
        responses.GET,
        f"{page_url}?page=1",
        body=''.join(f'<h2><a href="/news/{s}">{s}</a></h2>' for s in page_1_slugs),
        status=200,
        content_type='text/html'
    )
    for slug in page_1_slugs:
        responses.add(
            responses.GET,
            f"https://www.erewash.gov.uk/news/{slug}",
            body=f'<html><body><article><p>Content of {slug}</p></article></body></html>',
            status=200,
            content_type='text/html'
        )

    lambda_handler(make_event(), None)

    assert len(responses.calls) == 6  # page 0 + 2 details + page 1 + 2 details

    sources_table = boto3.resource('dynamodb', region_name='eu-west-2').Table('sources')
    result = sources_table.scan()
    assert result['Count'] == 5  # 1 original + 4 new
    saved_urls = [item['url'] for item in result['Items']]
    for slug in page_0_slugs + page_1_slugs:
        assert f"https://www.erewash.gov.uk/news/{slug}" in saved_urls


