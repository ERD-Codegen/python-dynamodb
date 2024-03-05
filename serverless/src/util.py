JWT_SECRET_KEY = 'sample_secret_key'
JWT_ALGORITHM = 'HS256'

def envelop(content):
    response = {
        "statusCode": 200,
        "headers": {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': 'true'
        },
        "body": content
    }
    return response
    