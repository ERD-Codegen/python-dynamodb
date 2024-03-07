import json
import boto3
import logging
import uuid
from datetime import datetime
from slugify import slugify
from boto3.dynamodb.conditions import Key, Attr
import src.user as user
from src.util import *

dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
articles_table = dynamodb.Table("dev-articles")


def create_article(event):
    authenticatedUser = user.authenticate_and_get_user(event)
    if authenticatedUser is None:
        return envelop("Must be logged in", 422)

    body = event["body"]
    if "article" not in body:
        return envelop("Article must be specified", 422)

    article = body["article"]
    for field in ["title", "description", "body"]:
        if field not in article:
            return envelop(f"{field} must be specified", 422)

    timestamp = int(datetime.utcnow().timestamp())
    slug = slugify(article["title"]) + "-" + str(uuid.uuid4())

    item = {
        "slug": slug,
        "title": article["title"],
        "description": article["description"],
        "body": article["body"],
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "author": authenticatedUser["username"],
        "dummy": "partition",
        "favoritesCount": 0,
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
        "following": False,
    }

    return envelop({"article": item})


def get_article(event):
    if "slug" not in event["pathParameters"]:
        return envelop("Slug must be specified", 422)

    slug = event["pathParameters"]["slug"]
    result = articles_table.get_item(Key={"slug": slug})
    if "Item" not in result:
        return envelop(f"Article not found: {slug}", 422)

    article = result["Item"]
    authenticated_user = user.authenticate_and_get_user(event)
    return envelop(
        {"article": transform_retrieved_article(article, authenticated_user)}
    )


def transform_retrieved_article(article, authenticated_user):
    del article["dummy"]
    article["tagList"] = article.get("tagList", [])
    article["favoritesCount"] = article.get("favoritesCount", 0)
    article["favorited"] = False
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


def update_article(event):

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
    article["updatedAt"] = int(datetime.utcnow().timestamp())
    articles_table.put_item(Item=article)

    return envelop(
        {"article": transform_retrieved_article(article, authenticated_user)}
    )


def delete_article(event):
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


def favorite_article(event):
    authenticated_user = user.authenticate_and_get_user(event)
    if authenticated_user is None:
        return envelop("Must be logged in", 422)
    slug = event["pathParameters"].get("slug")
    if slug is None:
        return envelop("Slug must be specified", 422)

    article = articles_table.get_item(Key={"slug": slug}).get("Item")
    if article is None:
        return envelop(f"Article not found: {slug}", 422)

    shouldFavorite = event["httpMethod"] != "DELETE"
    if shouldFavorite:
        article.setdefault("favoritedBy", [])
        if authenticated_user["username"] not in article["favoritedBy"]:
            article["favoritedBy"].append(authenticated_user["username"])
            article["favoritesCount"] += 1
    elif (
        "favoritedBy" in article
        and authenticated_user["username"] in article["favoritedBy"]
    ):
        article["favoritedBy"].remove(authenticated_user["username"])
        article["favoritesCount"] -= 1
        if len(article["favoritedBy"]) == 0:
            del article["favoritedBy"]
            article["favoritesCount"] = 0

    articles_table.put_item(Item=article)

    return envelop(
        {"article": transform_retrieved_article(article, authenticated_user)}
    )


def list_articles(event):
    authenticated_user = user.authenticate_and_get_user(event)
    params = event.get("queryStringParameters", {})
    limit = int(params.get("limit", 20))
    offset = int(params.get("offset", 0))
    if sum(item in params for item in ["tag", "author", "favorited"]) > 1:
        return envelop("Use only one of tag, author, or favorited", 422)
    queryParams = {
        "KeyConditionExpression": "dummy = :dummy",
        "ExpressionAttributeValues": {":dummy": "partition"},
        "ScanIndexForward": False,
        "IndexName": "createdAt",
    }
    if "tag" in params:
        queryParams["FilterExpression"] = "contains(tagList, :tag)"
        queryParams["ExpressionAttributeValues"] = {":tag": params["tag"]}
    elif "author" in params:
        queryParams["FilterExpression"] = "author = :author"
        queryParams["ExpressionAttributeValues"] = {":author": params["author"]}
    elif "favorited" in params:
        queryParams["FilterExpression"] = "contains(favoritedBy, :favorited)"
        queryParams["ExpressionAttributeValues"] = {":favorited": params["favorited"]}

    return envelop(
        {
            "articles": queryEnoughArticles(
                queryParams, authenticated_user, limit, offset
            )
        }
    )


def get_article_by_author(author, authenticated_user):
    queryParams = {
        "ScanIndexForward": False,
        "IndexName": "author",
        "keyConditionExpression": "author = :author",
        "ExpressionAttributeValues": {":author": author},
    }
    queryResult = articles_table.query(queryParams)
    return queryResult.get("Items", [])


def get_feed(event):
    authenticated_user = user.authenticate_and_get_user(event)
    if authenticated_user is None:
        return envelop("Must be logged in", 422)

    limit = int(event.get("queryStringParameters", {}).get("limit", 20))
    offset = int(event.get("queryStringParameters", {}).get("offset", 0))
    follow_list = user.get_followed_users(authenticated_user["username"])

    articles_ret = []
    for username in follow_list:
        articles_ret.extend(get_article_by_author(username, authenticated_user))
    articles_ret.sort(key=lambda x: x["createdAt"], reverse=True)
    return envelop({"articles": articles_ret[offset : offset + limit]})


def get_tags(event):
    uniqTags = set()
    scanParam = {
        AttibutesToGet: ["tagList"],
    }
    while True:
        scanResult = articles_table.scan(scanParam)
        for item in scanResult["Items"]:
            uniqTags.update(item["tagList"])
        if "LastEvaluatedKey" not in scanResult:
            break
        scanParam["ExclusiveStartKey"] = scanResult["LastEvaluatedKey"]
    return envelop({"tags": list(uniqTags)})


def queryEnoughArticles(queryParams, authenticatedUser, limit, offset):
    queryResultItems = []
    while len(queryResultItems) < limit + offset:
        print(queryParams)
        queryResult = articles_table.query(**queryParams)
        queryResultItems.extend(queryResult["Items"])
        if "LastEvaluatedKey" not in queryResult:
            break
        else:
            queryParams["ExclusiveStartKey"] = queryResult["LastEvaluatedKey"]
    articleRet = []
    for article in queryResultItems[offset : offset + limit]:
        articleRet.append(transform_retrieved_article(article, authenticatedUser))
    return articleRet
