import logging
import json

JWT_SECRET_KEY = "sample_secret_key"
JWT_ALGORITHM = "HS256"


def envelop(content, statusCode=200):
    if statusCode == 200:
        body = json.dumps(content, default=int)
    else:
        body = json.dumps({"errors": {"body": [content]}})
        logging.error(body)

    response = {
        "statusCode": statusCode,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
        "body": body,
    }
    return response
