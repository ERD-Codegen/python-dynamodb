import json
import boto3
import logging
import uuid
from datetime import datetime
from slugify import slugify
from boto3.dynamodb.conditions import Key, Attr
import user
from util import *

dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
articles_table = dynamodb.Table("dev-articles")


def create_article(event, context):
    authenticatedUser = user.authenticate_and_get_user(event)
    if authenticatedUser is None:
        return envelop("Must be logged in", 422)

    body = event["body"]
    if article not in body:
        return envelop("Article must be specified", 422)

    article = body["article"]
    for field in ["title", "description", "body"]:
        if field not in article:
            return envelop(f"{field} must be specified", 422)

    timestamp = str(datetime.utcnow().timestamp())
    slug = slugify(article["title"]) + "-" + str(uuid.uuid4())

    item = {
        "slug": slug,
        "title": article["title"],
        "description": article["description"],
        "body": article["body"],
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "author": authenticatedUser["username"],
        "dummy": "OK",
    }

    if "tagList" in article:
        item["tagList"] = article["tagList"]

    articles_table.put_item(Item=item)

    del item["dummy"]
    item["tagList"] = article.get("tagList", [])
    item["favorited"] = False
    item["favoritesCount"] = 0
    item["author"] = {
        "username": authenticatedUser["username"],
        "bio": authenticatedUser.get("bio", ""),
        "image": authenticatedUser.get("image", ""),
        following: False,
    }

    return envelop({"article": item})


def get_article(event, context):
    if "slug" not in event["pathParameters"]:
        return envelop("Slug must be specified", 422)

    slug = event["pathParameters"]["slug"]
    result = articles_table.get_item(Key={"slug": slug})
    if "Item" not in result:
        return envelop(f"Article not found: {slug}", 422)

    article = result["Item"]
    authenticated_user = user.authenticate_and_get_user(event)
    return envelop(transform_retrieved_article(article, authenticated_user))


def transform_retrieved_article(article, authenticated_user):
    del article["dummy"]
    article["tagList"] = article.get("tagList", [])
    article["favoritesCount"] = article.get("favoritesCount", 0)
    article["favorited"] = false
    if "favoritedBy" in article:
        if authenticated_user:
            article["favorited"] = (
                authenticated_user["username"] in article["favoritedBy"]
            )
        del article["favoritedBy"]
    article["author"] = user.get_profile_by_username(
        article["author"], authenticated_user
    )
    return article


def update_article(event, context):

    body = event["body"]
    if "article" not in body:
        return envelop("Article must be specified", 422)
    article_mutation = body["article"]

    if all(item not in article_mutation for item in ["title", "description", "body"]):
        return envelop(
            "At least one field must be specified: [title, description, body].", 422
        )

    authenticated_user = user.authenticate_and_get_user(event)
    if authenticated_user is None:
        return envelop("Must be logged in", 422)

    slug = event["pathParameters"].get("slug")

    if slug is None:
        return envelop("Slug must be specified", 422)

    article = articles_table.get_item(Key={"slug": slug}).get("Item")
    if article is None:
        return envelop(f"Article not found: {slug}", 422)

    if article["author"] != authenticated_user["username"]:
        return envelop(
            f"Article can only be updated by author: {article['author']}", 422
        )

    for field in ["title", "description", "body"]:
        if field in article_mutation:
            article[field] = article_mutation[field]
    article["updatedAt"] = str(datetime.utcnow().timestamp())
    articles_table.put_item(Item=article)

    return envelop(
        {"article": transform_retrieved_article(article, authenticated_user)}
    )


def delete_article(event, context):
    authenticated_user = user.authenticate_and_get_user(event)
    if authenticated_user is None:
        return envelop("Must be logged in", 422)
    slug = event["pathParameters"].get("slug")
    if slug is None:
        return envelop("Slug must be specified", 422)

    article = articles_table.get_item(Key={"slug": slug}).get("Item")
    if article is None:
        return envelop(f"Article not found: {slug}", 422)
    if article["author"] != authenticated_user["username"]:
        return envelop(
            f"Article can only be deleted by author: {article['author']}", 422
        )
    articles_table.delete_item(Key={"slug": slug})
    return envelop({})
