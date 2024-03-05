import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
import jwt
import bcrypt
from src.util import *

dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')
users_table = dynamodb.Table("dev-users")


# create user
def create_user(event, context):

    # input validation
    if "user" not in event:
        raise Exception("User must be specified.", 422)
    user = event['user']
    if 'username' not in user:
        logging.error("Validation Failed")
        raise Exception("Username must be specified.", 422)
    if 'email' not in user:
        logging.error("Validation Failed")
        raise Exception("Email must be specified.", 422)
    if 'password' not in user:
        logging.error("Validation Failed")
        raise Exception("Password must be specified.", 422)

    # Verify username is not taken
    user_exists = get_user_by_username(user['username'])
    if "Item" in user_exists:
        logging.error("Validation Failed")
        raise Exception(f"Username already taken: {user['username']}", 422)

    # Verify email is not taken
    email_exists = get_user_by_email(user['email'])
    if email_exists["Count"]:
        logging.error("Validation Failed")
        raise Exception(f"Email already taken: {user['email']}", 422)
    
    # Add new entry to usersTable
    encryptedPassword = bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt())
    item = {
        'username': user['username'],
        'email': user['email'],
        'password': encryptedPassword,
    }
    users_table.put_item(Item=item)
    
    # Return user info with jwt token
    user = {
        'email': user['email'],
        'token': mint_token(user['username']),
        'username': user['username'],
        'bio': '',
        'image': ''
    }
    return envelop({"user": user})


def mint_token(a_username):
    payload = {
        'username': a_username,
        'exp': datetime.utcnow() + timedelta(days=2)
    }
    jwt_token = jwt.encode(payload, JWT_SECRET_KEY, JWT_ALGORITHM)
    return jwt_token


def get_user_by_username(username):
    print(f"REQ:{username}")
    try:
        response = users_table.get_item(
            Key={
                'username': username
            }
        )
    except Exception as e:
        response = None
    print(f"RESP:{response}")
    return response


def get_user_by_email(a_email):
    response = users_table.query(
        IndexName='email',
        KeyConditionExpression='email= :email',
        ExpressionAttributeValues={
            ':email': a_email,
        },
        Select='ALL_ATTRIBUTES',
    )
    print(f"EMAIL:{response}")
    return response


# login user
def login_user(event, context):
    user = event['user']
    
    # input validation
    if not user:
        logging.error("Validation Failed")
        raise Exception("User must be specified.", 422)
    if 'email' not in user:
        logging.error("Validation Failed")
        raise Exception("Email must be specified.", 422)
    if 'password' not in user:
        logging.error("Validation Failed")
        raise Exception("Password must be specified.", 422)

    # Get user with this email
    user_with_this_email = get_user_by_email(user['email'])
    if user_with_this_email['Count'] != 1:
        raise Exception(f"Email not fount: {user['email']}.", 422)
        
    # Check password
    if not bcrypt.checkpw(user["password"].encode(), user_with_this_email['Items'][0]['password'].encode()):
        raise Exception("Wrong password.", 422)

    # Return user with jwt token
    authenticated_user = {
        'email': user['email'],
        'token': mint_token(user_with_this_email['Items'][0]['username']),
        'username': user_with_this_email['Items'][0]['username'],
        'bio': user_with_this_email['Items'][0].get("bio", ""),
        'image': user_with_this_email['Items'][0].get("image", "")
    }

    return envelop({"user": authenticated_user})


# get user
def get_user(event, context):
    authenticated_user = authenticate_and_get_user(event)
    if not authenticated_user:
        raise Exception('Token not present or invalid.', 422)

    user = {
        'email': authenticated_user['email'],
        'token': get_token_from_event(event),
        'username': authenticated_user['username'],
        'bio': authenticated_user.get("bio", ""),
        'image':  authenticated_user.get("image", "")
    }

    return envelop({"user": user})


def update_user(event, context):
    authenticated_user = authenticate_and_get_user(event)
    if not authenticated_user:
        raise Exception('Token not present or invalid.', 422)

    user = event["user"]
    if not user:
        logging.error("Validation Failed")
        raise Exception("User must be specified.", 422)

    updated_user = authenticated_user

    if user['email']:
        # Verify email is not taken
        user_with_this_email = get_user_by_email(user['email'])
        if user_with_this_email['Count'] != 0:
            return Exception(f"Email already taken: {user['email']}", 422)
        updated_user['email'] = user['email']

    if user['password']:
        updated_user['password'] = bcrypt.hashpw(user["password"].encode(), bcrypt.gensalt())

    if user['image']:
        updated_user['image'] = user['image']

    if user['bio']:
        updated_user['bio'] = user['bio']

    print(f"UPDATE: {updated_user}")


    users_table.put_item(Item=updated_user)

    del updated_user['password']
    updated_user['token'] = get_token_from_event(event)

    return envelop({"user": updated_user})


def get_profile(event, context):
    username = event['pathParameters']['username']
    authenticated_user = authenticate_and_get_user(event)
    profile = get_profile_by_username(username, authenticated_user);
    print(f"PROFILE: {profile}")
    if not profile:
        raise Exception(f"User not found: ${username}", 422)

    response = {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        "profile": profile
    }
    return response


def follow(event, context):
    authenticated_user = authenticate_and_get_user(event, context)
    if not authenticated_user:
        raise Exception('Token not present or invalid.', 422)
    username = event['pathParameters']['username']
    user = (get_user_by_username(username))['Item']
    should_follow = (not event['httpMethod'] == 'DELETE')

    # Update "followers" field on followed user
    if should_follow:
        if user['followers'] and authenticated_user['username'] not in user['followers']:
            pass
            user['followers'].append(authenticated_user['username'])
        else:
            user['followers'] = [authenticated_user['username']]
    else:
        if user['followers'] and authenticated_user['username'] in user['followers']:
            # create new list of follower except authenticated user
            follow_result = filter(lambda x: x != authenticated_user['username'], user['followers'])
            user['followers'] = list(follow_result)

            # delete followers if list is empty
            if not len(user['followers']):
                print("In Delete condition")
                del user['followers']

    table = dynamodb.Table('dev-users')
    table.put_item(Item=user)

    # Update "following" field on follower user
    if should_follow:
        if authenticated_user['following'] and authenticated_user['following'] not in username:
            authenticated_user['following'].append(username)
        else:
            authenticated_user['following'] = [username]
    else:
        if authenticated_user['following'] and authenticated_user['following'] in username:
            # create new list of following except username
            result = filter(lambda x: x != username, authenticated_user['following'])
            authenticated_user['following'] = list(result)

            # delete following if list is empty
            if not len(authenticated_user['following']):
                del authenticated_user['following']

    table.put_item(Item=authenticated_user)

    profile = {
        'username': username,
        'bio': user['bio'] if user['bio'] else '',
        'image': user['image'] if user['bio'] else '',
        'following': should_follow
    }

    response = {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        "profile": profile
    }

    return response


# create followed users
def get_followed_users(a_username):
    table = dynamodb.Table('dev-users')
    user = table.get_item(
        Key={
            'username': a_username
        }
    )['Item']

    return user['following'] or user['following']== []


def get_token_from_event(event):
    return event['headers']['authorization'].replace('Token', '')


def get_profile_by_username(a_username, a_authenticated_user):
    user = get_user_by_username(a_username)['Item']
    print(f"PROFILE USER: {user}")
    if not user:
        return None

    profile = {
        'username': user['username'],
        'bio': user.get("bio", ""),
        'image': user.get("image", ""),
        'following': False,
    }

    # If user is authenticated, set following bit
    if user['followers'] and a_authenticated_user:
        profile['following'] = user['followers'] in a_authenticated_user['username']

    return profile


def authenticate_and_get_user(event):
    try:
        token = get_token_from_event(event)
        decoded = jwt.decode(token, JWT_SECRET_KEY, JWT_ALGORITHM),
        username = decoded.username,
        authenticated_user = get_user_by_username(username)
        return authenticated_user
    except Exception as e:
        return None