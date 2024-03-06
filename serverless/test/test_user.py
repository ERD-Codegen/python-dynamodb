import pytest
import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src import user


@pytest.fixture
def users_table(dynamodb_client):
    table = dynamodb_client.create_table(
        TableName="dev-users",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "username", "AttributeType": "S"},
            {"AttributeName": "email", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "email",
                "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            }
        ],
    )
    yield table


def test_create_user(users_table, dynamodb_client):
    user1 = {
        "username": "john doe",
        "email": "johndoe@gmail.com",
        "password": "password123",
    }

    event = {"user": user1}
    ret = user.create_user(event, {})
    assert ret["body"]["user"]["username"] == "john doe"
    print(ret)
