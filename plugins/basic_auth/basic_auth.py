import requests
from requests.auth import HTTPBasicAuth


def cred_check(url, user, password):
    headers = {
        'User-Agent': ''
    }
    if (password) is not None:
        result = None
        result = requests.get(url, auth=HTTPBasicAuth(user, password), headers=headers)
        print(result.status_code)
        if result.status_code == 200:
            return True


def basic_auth(url,user,password):
    data_response = {
        'code': 'notset',
        'success': False,
        'url': url,
        'user': user,
        'password': password
    }
    try:
        auth_check = cred_check(url, user, password)
        if auth_check:
            data_response['success'] = True
    except Exception as ex:
        data_response['error'] = ex
        pass
    return data_response


def lambda_handler(event, context):
    url = event['args']['url']
    return basic_auth(url, event['user'], event['password'])
