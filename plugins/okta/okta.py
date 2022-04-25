import datetime
import json

import botocore.vendored.requests as requests  # As long as we're in AWS Lambda, this trick works for accessing requests


def lambda_handler(event, context):
    domain = event['args']['oktadomain']
    return okta_authenticate(domain, event['username'], event['password'], event['useragent'])


def okta_authenticate(domain, username, password, useragent):
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    data_response = {
        'timestamp': ts,
        'username': username,
        'password': password,
        'success': False,
        'change': False,
        '2fa_enabled': False,
        'type': None,
        'code': None,
        'name': None,
        'action': None,
        'headers': [],
        'cookies': [],
    }

    payload = {"username": username, "password": password,
               "options": {"warnBeforePasswordExpired": True, "multiOptionalFactorEnroll": True}}
    url = "https://%s/api/v1/authn/" % domain

    try:
        resp = requests.post(url, data=json.dumps(payload),
                             headers={'Content-Type': 'application/json', 'User-Agent': useragent})
        if resp.status_code == 200:
            resp_json = json.loads(resp.text)
            if resp_json.get(
                    "status") == "LOCKED_OUT":  # Warning: administrators can configure Okta to not indicate that an account is locked out. Fair warning ;)
                data_response['success'] = False
                data_response['error'] = 'locked out'
                data_response['action'] = 'redirect'
            elif resp_json.get("status") == "SUCCESS":
                data_response['success'] = True
            elif resp_json.get("status") == "MFA_REQUIRED":
                data_response['2fa_enabled'] = True
                data_response['success'] = True
                try:
                    data_response['code'] = resp_json['_embedded']['factors'][0]['factorType']
                except:
                    data_response['code'] = "Unknown"
            elif resp_json.get("status") == "PASSWORD_EXPIRED":
                data_response['change'] = True
                data_response['success'] = True
            else:
                data_response['success'] = False
        else:
            data_response['success'] = False
    except Exception as ex:
        data_response['error'] = ex
        pass

    return data_response
