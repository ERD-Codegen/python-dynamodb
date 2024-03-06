import boto3
from moto import mock_aws
import pytest

import sys, os

sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from src import user


@pytest.fixture
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-2"


@pytest.fixture
def dynamodb_client(aws_credentials):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-2")
        yield dynamodb
