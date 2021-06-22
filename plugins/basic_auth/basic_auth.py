import requests
from requests.auth import HTTPBasicAuth
from time import sleep


def setup_tor_proxy():
    """Sets up the Tor proxy. Taken from: https://github.com/qrtt1/aws-lambda-tor"""

    from tempfile import mkstemp
    from subprocess import Popen, PIPE
    import os

    fd, tmp = mkstemp(".torrc")
    fd_datadir, data_dir = mkstemp(".data")
    os.unlink(data_dir)
    os.makedirs(data_dir)

    with open(tmp, "w") as f:
        f.write("SOCKSPort 9050\n")
        f.write(f"DataDirectory {data_dir}\n")

    tor_path = os.path.join(os.environ["LAMBDA_TASK_ROOT"], "tor")
    process = Popen([tor_path, "-f", tmp], cwd=os.path.dirname(data_dir), stdout=PIPE)
    return process1


def cred_check(url, user, password, tor_enabled):
    headers = {
        'User-Agent': ''
    }
    proxies = {'http': 'socks5h://localhost:9050', 'https': 'socks5h://localhost:9050'}
    if (password) is not None:
        result = None
        if tor_enabled:
            result = requests.get(url, auth=HTTPBasicAuth(user, password), headers=headers, proxies=proxies)
        else:
            result = requests.get(url, auth=HTTPBasicAuth(user, password), headers=headers)
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
    tor_enabled = 0
    if event['args']['tor']:
        tor_enabled = 1

    if tor_enabled == 1:
        process = setup_tor_proxy()
        sleep(20)

    output = basic_auth(url, event['user'], event['password'], tor_enabled)
    if tor_enabled == 1:
        process.terminate()
    return output
