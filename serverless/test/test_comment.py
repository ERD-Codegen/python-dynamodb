import pytest
import logging
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src import article as Article, user as User, comment as Comment


def test_create(article1Slug, comments_table, user2Token):
    header = {"Authorization": f"Token {user2Token}"}
    comment = {"body": "comment1"}
    body = {"comment": comment}
    event = {"headers": header, "body": body, "pathParameters": {"slug": article1Slug}}
    ret = Comment.create(event, {})
    print(ret)
    assert ret["statusCode"] == 200
    assert ret["body"]["comment"]["body"] == "comment1"
    assert ret["body"]["comment"]["author"]["username"] == "jane doe"
    assert ret["body"]["comment"]["author"]["bio"] == ""


def test_get(article1Slug, comments_table, user2Token):
    header = {"Authorization": f"Token {user2Token}"}
    comment = {"body": "comment1"}
    body = {"comment": comment}
    event = {"headers": header, "body": body, "pathParameters": {"slug": article1Slug}}
    ret = Comment.create(event, {})
    assert ret["statusCode"] == 200

    event = {"pathParameters": {"slug": article1Slug}}
    ret = Comment.get(event, {})
    assert ret["statusCode"] == 200
    assert len(ret["body"]["comments"]) == 1
    assert ret["body"]["comments"][0]["body"] == "comment1"
    assert ret["body"]["comments"][0]["author"]["username"] == "jane doe"


def test_create_no_comment(article1Slug, comments_table, user2Token):
    header = {"Authorization": f"Token {user2Token}"}
    body = {}
    event = {"headers": header, "body": body, "pathParameters": {"slug": article1Slug}}
    ret = Comment.create(event, {})
    assert ret["statusCode"] == 422
    assert ret["body"] == {"errors": {"body": ["Comment must be specified"]}}


def test_delete(article1Slug, comments_table, user2Token):
    header = {"Authorization": f"Token {user2Token}"}
    comment = {"body": "comment1"}
    body = {"comment": comment}
    event = {"headers": header, "body": body, "pathParameters": {"slug": article1Slug}}
    ret = Comment.create(event, {})
    assert ret["statusCode"] == 200

    comment_id = ret["body"]["comment"]["id"]
    event = {
        "pathParameters": {"slug": article1Slug, "id": comment_id},
        "headers": header,
    }
    ret = Comment.delete(event, {})
    assert ret["statusCode"] == 200

    event = {"pathParameters": {"slug": article1Slug}}
    ret = Comment.get(event, {})

    assert ret["statusCode"] == 200
    assert len(ret["body"]["comments"]) == 0


def test_delete_invalid_comment_id(article1Slug, comments_table, user2Token):
    header = {"Authorization": f"Token {user2Token}"}
    comment = {"body": "comment1"}
    body = {"comment": comment}
    event = {"headers": header, "body": body, "pathParameters": {"slug": article1Slug}}
    ret = Comment.create(event, {})
    assert ret["statusCode"] == 200

    comment_id = "invalid"
    event = {
        "pathParameters": {"slug": article1Slug, "id": comment_id},
        "headers": header,
    }
    ret = Comment.delete(event, {})
    assert ret["statusCode"] == 422
    assert ret["body"] == {"errors": {"body": ["Comment not found"]}}
