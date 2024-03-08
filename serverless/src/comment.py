import json
import boto3
import logging
import uuid
from datetime import datetime
from boto3.dynamodb.conditions import Key, Attr
import src.user as User
import src.article as Article
from src.util import *

dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
comments_table = dynamodb.Table("dev-comments")


def create(event, context):
    authenticatedUser = User.authenticate_and_get_user(event)
    if authenticatedUser is None:
        return envelop("Must be logged in", 422)

    body = json.loads(event["body"])
    if "comment" not in body:
        return envelop("Comment must be specified", 422)

    comment_val = body["comment"]

    slug = event.get("pathParameters", {}).get("slug")
    if slug is None:
        return envelop("Article slug must be specified", 422)
    article = Article.get_article_by_slug(slug)
    if article is None:
        return envelop(f"Article not found", 422)

    timestamp = int(datetime.utcnow().timestamp())
    timeformated = datetime.utcfromtimestamp(timestamp).isoformat() + ".000Z"
    comment = {
        "id": str(uuid.uuid4()),
        "slug": slug,
        "body": comment_val["body"],
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "author": authenticatedUser["username"],
    }
    comments_table.put_item(Item=comment)
    comment["createdAt"] = timeformated
    comment["updatedAt"] = timeformated
    comment["author"] = {
        "username": authenticatedUser["username"],
        "bio": authenticatedUser.get("bio", ""),
        "image": authenticatedUser.get("image", ""),
        "following": False,
    }
    return envelop({"comment": comment})


def get(event, context):
    authenticated_user = User.authenticate_and_get_user(event)
    slug = event.get("pathParameters", {}).get("slug")
    if slug is None:
        return envelop("Article slug must be specified", 422)
    article = Article.get_article_by_slug(slug)
    if article is None:
        return envelop(f"Article not found", 422)

    comments = comments_table.query(
        IndexName="article",
        KeyConditionExpression=Key("slug").eq(slug),
    )
    comments = comments.get("Items", [])
    for comment in comments:
        comment["author"] = User.get_profile_by_username(
            comment["author"], authenticated_user
        )
        comment["createdAt"] = (
            datetime.utcfromtimestamp(comment["createdAt"]).isoformat() + ".000Z"
        )
        comment["updatedAt"] = (
            datetime.utcfromtimestamp(comment["updatedAt"]).isoformat() + ".000Z"
        )
    return envelop({"comments": comments})


def delete(event, context):
    authenticated_user = User.authenticate_and_get_user(event)
    if authenticated_user is None:
        return envelop("Must be logged in", 422)

    comment_id = event.get("pathParameters", {}).get("id")
    if comment_id is None:
        return envelop("Comment id must be specified", 422)

    comment = comments_table.query(
        KeyConditionExpression=Key("id").eq(comment_id),
    )
    logging.info(comment)

    if comment["Count"] == 0:
        return envelop(f"Comment not found", 422)
    comment = comment.get("Items", [])[0]

    if comment["author"] != authenticated_user["username"]:
        return envelop(f"Cannot delete other user's comment", 422)

    comments_table.delete_item(Key={"id": comment_id})
    return envelop({})
