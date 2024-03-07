import logging

JWT_SECRET_KEY = "sample_secret_key"
JWT_ALGORITHM = "HS256"


def envelop(content, statusCode=200):
    if statusCode == 200:
        body = content
    else:
        logging.error(content)
        body = {"errors": {"body": [content]}}

    response = {
        "statusCode": statusCode,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        },
        "body": body,
    }
    return response
