import pytest
import logging
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src import article, user


def test_create_article(articles_table, article1, user1Token):
    eventbody = {"article": article1}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}

    ret = article.create_article(event, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["article"]["title"] == "title1"


def test_get_article(articles_table, article1, user1Token):
    eventbody = {"article": article1}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    ret = article.create_article(event, {})

    slug = ret["body"]["article"]["slug"]
    event = {"pathParameters": {"slug": slug}}
    ret = article.get_article(event, {})
    logging.info(ret)
    assert ret["statusCode"] == 200
    assert ret["body"]["article"]["title"] == "title1"
    assert ret["body"]["article"]["slug"] == slug
    assert ret["body"]["article"]["favorited"] == False
    assert ret["body"]["article"]["favoritesCount"] == 0
    assert ret["body"]["article"]["author"]["following"] == False
    assert ret["body"]["article"]["author"]["image"] == ""
    assert ret["body"]["article"]["author"]["bio"] == ""
    assert ret["body"]["article"]["author"]["username"] == "john doe"


def test_update_article(articles_table, article1, user1Token):
    eventbody = {"article": article1}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    ret = article.create_article(event, {})

    slug = ret["body"]["article"]["slug"]
    event = {
        "headers": headers,
        "pathParameters": {"slug": slug},
        "body": {
            "article": {
                "title": "title1 altered",
                "description": "description1 altered",
                "body": "body1 altered",
            }
        },
    }
    ret = article.update_article(event, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["article"]["title"] == "title1 altered"
    assert ret["body"]["article"]["description"] == "description1 altered"
    assert ret["body"]["article"]["body"] == "body1 altered"
    assert ret["body"]["article"]["slug"] == slug
    assert ret["body"]["article"]["favorited"] == False
    assert ret["body"]["article"]["favoritesCount"] == 0
    assert ret["body"]["article"]["author"]["following"] == False
    assert ret["body"]["article"]["author"]["image"] == ""
    assert ret["body"]["article"]["author"]["bio"] == ""
    assert ret["body"]["article"]["author"]["username"] == "john doe"


def test_delete_article(articles_table, article1, user1Token):
    eventbody = {"article": article1}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    ret = article.create_article(event, {})

    slug = ret["body"]["article"]["slug"]
    event = {
        "headers": headers,
        "pathParameters": {"slug": slug},
    }
    article.delete_article(event, {})
    ret = article.get_article(event, {})
    assert ret["statusCode"] == 422


def test_favorite_article(articles_table, article1, user1Token):
    eventbody = {"article": article1}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    ret = article.create_article(event, {})

    slug = ret["body"]["article"]["slug"]
    event = {
        "httpMethod": "POST",
        "headers": headers,
        "pathParameters": {"slug": slug},
    }
    article.favorite_article(event, {})
    event = {
        "headers": headers,
        "pathParameters": {"slug": slug},
    }
    ret = article.get_article(event, {})
    assert ret["body"]["article"]["favorited"] == True
    assert ret["body"]["article"]["favoritesCount"] == 1


def test_list_articles(articles_table, article1, article2, user1Token):
    eventbody = {"article": article2}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    ret = article.create_article(event, {})

    eventbody = {"article": article1}
    event = {"headers": headers, "body": eventbody}
    ret = article.create_article(event, {})

    queryStringParameters = {"limit": 1, "offset": 1}
    event = {
        "headers": headers,
        "queryStringParameters": queryStringParameters,
    }
    ret = article.list_articles(event, {})
    assert ret["statusCode"] == 200
    assert len(ret["body"]["articles"]) == 1
    article_ret = ret["body"]["articles"][0]
    assert article_ret["title"] == "title2"


def test_get_article_by_author(
    articles_table, article1, article2, article3, user1Token, user2Token
):
    eventbody = {"article": article2}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    article.create_article(event, {})

    eventbody = {"article": article1}
    event = {"headers": headers, "body": eventbody}
    article.create_article(event, {})

    eventbody = {"article": article3}
    headers = {"Authorization": f"Token {user2Token}"}
    event = {"headers": headers, "body": eventbody}
    article.create_article(event, {})

    queryStringParameters = {"author": "john doe"}
    event = {
        "headers": headers,
        "queryStringParameters": queryStringParameters,
    }
    ret = article.list_articles(event, {})
    assert ret["statusCode"] == 200
    assert len(ret["body"]["articles"]) == 2
    article_ret = ret["body"]["articles"][0]
    assert article_ret["title"] == "title1"
    article_ret = ret["body"]["articles"][1]
    assert article_ret["title"] == "title2"


def test_get_feed(articles_table, article1, article2, article3, user1Token, user2Token):
    eventbody = {"article": article2}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    article.create_article(event, {})

    eventbody = {"article": article3}
    headers2 = {"Authorization": f"Token {user2Token}"}
    event = {"headers": headers2, "body": eventbody}
    article.create_article(event, {})

    pathParameters = {"username": "john doe"}
    httpMethod = "POST"
    event = {
        "headers": headers2,
        "pathParameters": pathParameters,
        "httpMethod": httpMethod,
    }
    user.follow(event, {})

    event = {
        "headers": headers2,
    }
    ret = article.get_feed(event, {})
    assert ret["statusCode"] == 200
    assert len(ret["body"]["articles"]) == 1
    article_ret = ret["body"]["articles"][0]
    assert article_ret["title"] == "title2"
    assert article_ret["author"]["username"] == "john doe"
    assert article_ret["author"]["following"] == True


def test_get_tags(articles_table, article1, article2, article3, user1Token, user2Token):
    eventbody = {"article": article2}
    headers = {"Authorization": f"Token {user1Token}"}
    event = {"headers": headers, "body": eventbody}
    article.create_article(event, {})

    eventbody = {"article": article3}
    headers2 = {"Authorization": f"Token {user2Token}"}
    event = {"headers": headers2, "body": eventbody}
    article.create_article(event, {})

    ret = article.get_tags({}, {})
    assert ret["statusCode"] == 200
    assert set(ret["body"]["tags"]) == {"tag2", "tag1"}
