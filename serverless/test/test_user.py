import pytest
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src import user


@pytest.fixture
def user1():
    return {
        "username": "john doe",
        "email": "johndoe@gmail.com",
        "password": "password123",
    }


@pytest.fixture
def user2():
    return {
        "username": "kim doe",
        "email": "kimdoe@gmail.com",
        "password": "password321",
    }


def test_create_user(users_table, user1):

    eventbody = {"user": user1}
    event = {"body": eventbody}
    ret = user.create_user(event, {})
    assert ret["body"]["user"]["username"] == "john doe"
    print(ret)


def test_login_user(users_table, user1):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    ret = user.create_user(event, {})

    eventbody = {"user": {"email": "johndoe@gmail.com", "password": "password123"}}
    event = {"body": eventbody}
    ret = user.login_user(event, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["user"]["username"] == "john doe"
    assert ret["body"]["user"]["email"] == "johndoe@gmail.com"
    assert "token" in ret["body"]["user"]


def test_invalid_login_user(users_table, user1):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    user.create_user(event, {})

    eventbody2 = {"user": {"email": "johndoe@gmail.com", "password": "invalidpassword"}}
    event2 = {"body": eventbody2}
    ret = user.login_user(event2, {})
    assert ret["statusCode"] == 422
    assert ret["body"] == {"errors": {"body": ["Wrong password."]}}


def test_get_user(users_table, user1):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    ret = user.create_user(event, {})

    event2 = {"headers": {"Authorization": "Bearer " + ret["body"]["user"]["token"]}}
    ret = user.get_user(event2, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["user"]["username"] == "john doe"


def test_get_user_invalid_token(users_table, user1):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    ret = user.create_user(event, {})

    event2 = {
        "headers": {
            "Authorization": "Bearer " + ret["body"]["user"]["token"] + "invalid"
        }
    }
    ret = user.get_user(event2, {})
    assert ret["statusCode"] == 422
    assert ret["body"] == {"errors": {"body": ["Token not present or invalid."]}}


def test_update_user(users_table, user1):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    created = user.create_user(event, {})

    event2 = {
        "headers": {"Authorization": "Bearer " + created["body"]["user"]["token"]},
        "body": {
            "user": {
                "email": "altered@gmail.com",
                "password": "altered123",
                "bio": "I love python and lambda!",
                "image": "https://image.com",
            }
        },
    }

    user.update_user(event2, {})
    event3 = {
        "headers": {"Authorization": "Bearer " + created["body"]["user"]["token"]}
    }
    ret = user.get_user(event3, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["user"]["email"] == "altered@gmail.com"
    assert ret["body"]["user"]["bio"] == "I love python and lambda!"
    assert ret["body"]["user"]["image"] == "https://image.com"


def test_get_profile(users_table, user1):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    created = user.create_user(event, {})

    event2 = {"pathParameters": {"username": "john doe"}}
    ret = user.get_profile(event2, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["profile"]["username"] == "john doe"
    assert ret["body"]["profile"]["following"] == False


def test_get_profile2(users_table, user2Token):
    event2 = {"pathParameters": {"username": "jane doe"}}
    ret = user.get_profile(event2, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["profile"]["username"] == "jane doe"
    assert ret["body"]["profile"]["following"] == False


def test_get_profile_nonexisting(users_table, user1):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    created = user.create_user(event, {})

    event2 = {"pathParameters": {"username": "nonexisting"}}
    ret = user.get_profile(event2, {})
    assert ret["statusCode"] == 422
    assert ret["body"] == {"errors": {"body": ["User not found: nonexisting"]}}


def test_follow_user(users_table, user1, user2):
    eventbody = {"user": user1}
    event = {"body": eventbody}
    created1 = user.create_user(event, {})

    eventbody = {"user": user2}
    event = {"body": eventbody}
    created2 = user.create_user(event, {})

    event2 = {
        "headers": {"Authorization": "Bearer " + created2["body"]["user"]["token"]},
        "httpMethod": "POST",
        "pathParameters": {"username": "john doe"},
    }
    ret = user.follow(event2, {})
    assert ret["statusCode"] == 200
    assert ret["body"]["profile"]["username"] == "john doe"

    event3 = {
        "headers": {"Authorization": "Bearer " + created2["body"]["user"]["token"]},
        "httpMethod": "GET",
        "pathParameters": {"username": "john doe"},
    }

    profile = user.get_profile(event2, {})
    assert profile["statusCode"] == 200
    assert profile["body"]["profile"]["following"] == True
