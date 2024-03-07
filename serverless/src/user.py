import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
import jwt
import bcrypt
from src.util import *

dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
users_table = dynamodb.Table("dev-users")


# create user
def create_user(event, context):
    body = event["body"]
    # input validation
    if "user" not in body:
        return envelop("User must be specified.", 422)
    user = body["user"]
    if "username" not in user:
        logging.error("Validation Failed")
        return envelop("Username must be specified.", 422)
    if "email" not in user:
        logging.error("Validation Failed")
        return envelop("Email must be specified.", 422)
    if "password" not in user:
        logging.error("Validation Failed")
        return envelop("Password must be specified.", 422)

    # Verify username is not taken
    user_exists = get_user_by_username(user["username"])
    if user_exists:
        logging.error("Validation Failed")
        return envelop(f"Username already taken: {user['username']}", 422)

    # Verify email is not taken
    email_exists = get_user_by_email(user["email"])
    if email_exists["Count"]:
        logging.error("Validation Failed")
        return envelop(f"Email already taken: {user['email']}", 422)

    # Add new entry to usersTable
    encryptedPassword = bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt())
    item = {
        "username": user["username"],
        "email": user["email"],
        "password": encryptedPassword,
    }
    users_table.put_item(Item=item)

    # Return user info with jwt token
    user = {
        "email": user["email"],
        "token": mint_token(user["username"]),
        "username": user["username"],
        "bio": "",
        "image": "",
    }

    return envelop({"user": user})


def mint_token(a_username):
    payload = {"username": a_username, "exp": datetime.utcnow() + timedelta(days=2)}
    jwt_token = jwt.encode(payload, JWT_SECRET_KEY, JWT_ALGORITHM)
    return jwt_token


def get_user_by_username(username):
    try:
        response = users_table.get_item(Key={"username": username})["Item"]
    except Exception as e:
        response = None
    return response


def get_user_by_email(a_email):
    response = users_table.query(
        IndexName="email",
        KeyConditionExpression="email= :email",
        ExpressionAttributeValues={
            ":email": a_email,
        },
        Select="ALL_ATTRIBUTES",
    )
    return response


# login user
def login_user(event, context):
    body = event["body"]

    # input validation
    if "user" not in body:
        logging.error("Validation Failed")
        return envelop("User must be specified.", 422)
    user = body["user"]
    if "email" not in user:
        logging.error("Validation Failed")
        return envelop("Email must be specified.", 422)
    if "password" not in user:
        logging.error("Validation Failed")
        return envelop("Password must be specified.", 422)

    # Get user with this email
    user_with_this_email = get_user_by_email(user["email"])
    if user_with_this_email["Count"] == 0:
        return envelop(f"Email not found: {user['email']}.", 422)

    # Check password
    if not bcrypt.checkpw(
        user["password"].encode(), bytes(user_with_this_email["Items"][0]["password"])
    ):
        return envelop("Wrong password.", 422)

    # Return user with jwt token
    authenticated_user = {
        "email": user["email"],
        "token": mint_token(user_with_this_email["Items"][0]["username"]),
        "username": user_with_this_email["Items"][0]["username"],
        "bio": user_with_this_email["Items"][0].get("bio", ""),
        "image": user_with_this_email["Items"][0].get("image", ""),
    }

    return envelop({"user": authenticated_user})


# get user
def get_user(event, context):
    authenticated_user = authenticate_and_get_user(event)
    if authenticated_user is None:
        return envelop("Token not present or invalid.", 422)
    user = {
        "email": authenticated_user["email"],
        "token": get_token_from_event(event),
        "username": authenticated_user["username"],
        "bio": authenticated_user.get("bio", ""),
        "image": authenticated_user.get("image", ""),
    }

    return envelop({"user": user})


def update_user(event, context):
    authenticated_user = authenticate_and_get_user(event)
    if not authenticated_user:
        return envelop("Token not present or invalid.", 422)
    updated_user = authenticated_user

    if "user" not in event["body"]:
        logging.error("Validation Failed")
        return envelop("User must be specified.", 422)
    user = event["body"]["user"]

    if "email" in user:
        # Verify email is not taken
        user_with_this_email = get_user_by_email(user["email"])
        if user_with_this_email["Count"] != 0:
            return envelop(f"Email already taken: {user['email']}", 422)
        updated_user["email"] = user["email"]

    if "password" in user:
        updated_user["password"] = bcrypt.hashpw(
            user["password"].encode(), bcrypt.gensalt()
        )

    if "image" in user:
        updated_user["image"] = user["image"]

    if "bio" in user:
        updated_user["bio"] = user["bio"]

    users_table.put_item(Item=updated_user)

    del updated_user["password"]
    updated_user["token"] = get_token_from_event(event)

    return envelop({"user": updated_user})


def get_profile(event, context):
    username = event["pathParameters"]["username"]
    authenticated_user = authenticate_and_get_user(event)
    profile = get_profile_by_username(username, authenticated_user)

    if profile is None:
        return envelop(f"User not found: {username}", 422)

    return envelop({"profile": profile})


def follow(event, context):
    authenticated_user = authenticate_and_get_user(event)
    if authenticated_user is None:
        return envelop("Token not present or invalid.", 422)

    username = event["pathParameters"]["username"]
    user = get_user_by_username(username)
    should_follow = event["httpMethod"] != "DELETE"

    # Update "followers" field on followed user
    if should_follow:
        if (
            "followers" in user
            and authenticated_user["username"] not in user["followers"]
        ):
            user["followers"].append(authenticated_user["username"])
        else:
            user.setdefault("followers", [authenticated_user["username"]])
    else:
        if "followers" in user and authenticated_user["username"] in user["followers"]:
            user["followers"].remove(authenticated_user["username"])

            # delete followers if list is empty
            if len(user["followers"]) == 0:
                del user["followers"]

    users_table.put_item(Item=user)

    # Update "following" field on follower user
    if should_follow:
        if (
            "following" in authenticated_user
            and username not in authenticated_user["following"]
        ):
            authenticated_user["following"].append(username)
        else:
            authenticated_user.setdefault("following", [username])
    else:
        if (
            "following" in authenticated_user
            and username in authenticated_user["following"]
        ):
            authenticated_user["following"].remove(username)

            # delete following if list is empty
            if len(authenticated_user["following"]) == 0:
                del authenticated_user["following"]

    users_table.put_item(Item=authenticated_user)

    profile = {
        "username": username,
        "bio": user.get("bio", ""),
        "image": user.get("image", ""),
        "following": should_follow,
    }

    return envelop({"profile": profile})


def get_followed_users(a_username):
    user = users_table.get_item(Key={"username": a_username})
    if "Item" not in user:
        return envelop("User not found", 422)
    user = user["Item"]
    return user.get("following", [])


def get_token_from_event(event):
    return event["headers"]["Authorization"].split(" ")[1]


def get_profile_by_username(a_username, a_authenticated_user):
    user = get_user_by_username(a_username)
    if user is None:
        return None
    profile = {
        "username": user["username"],
        "bio": user.get("bio", ""),
        "image": user.get("image", ""),
        "following": False,
    }

    # If user is authenticated, set following bit
    if "followers" in user and a_authenticated_user:
        profile["following"] = a_authenticated_user["username"] in user["followers"]

    return profile


def authenticate_and_get_user(event):
    try:
        token = get_token_from_event(event)
        decoded = jwt.decode(token, JWT_SECRET_KEY, JWT_ALGORITHM)
        username = decoded["username"]
        authenticated_user = get_user_by_username(username)
        return authenticated_user
    except Exception as e:
        return None
