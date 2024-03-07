import pytest
import logging
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src import article, user


@pytest.fixture
def article1():
    return {
        "title": "title1",
        "description": "description1",
        "body": "body1",
    }


@pytest.fixture
def article2():
    return {
        "title": "title2",
        "description": "description2",
        "body": "body2",
    }


@pytest.fixture
def user1Token(users_table):
    user1 = {
        "username": "john doe",
        "email": "johndoe@gmail.com",
        "password": "password123",
    }
    eventbody = {"user": user1}
    event = {"body": eventbody}
    ret = user.create_user(event, {})
    return ret["body"]["user"]["token"]


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
