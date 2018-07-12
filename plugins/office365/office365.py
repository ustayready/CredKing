import botocore.vendored.requests as requests
import json,datetime

def lambda_handler(event, context):
    return office_authenticate(event['username'], event['password'], event['useragent'])


def office_authenticate(username, password, useragent):
    """
    Attempts to authenticate to the Microsoft Office 365
    page at login.microsoftonline.com. If successful, the
    "success" key is set to True. Otherwise the login failed.

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
    headers = {}
    headers["User-Agent"] = useragent
    url = "https://login.microsoftonline.com"
    r = requests.get(url, headers=headers)
    
    # Set the referer url to track nonce
    headers["Referer"] = r.url
    
    # Get the other nonce/csrf tokens
    tokens = parse_tokens(r.content)

    # The endpoint to authenticate against
    authentication_url = url + "/common/login"

    # POST Data
    data = {
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
        "ctx":tokens["ctx"],
        "hpgrequestid":"",
        "flowToken":tokens["flowToken"],
        "PPSX":"",
        "NewUser":"1",
        "FoundMSAs":"",
        "fspost":"0",
        "i21":"0",
        "CookieDisclosure":"0",
        "IsFidoSupported":"1",
        "i2":"1",
        "i17":"",
        "i18":"",
        "i19":"122868"
    }

    # Response dictionary prep
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
    

    try:
        resp = requests.post(authentication_url, data=data, headers=headers)
        if "ESTSAUTH" in resp.cookies.keys():
            data_response["success"] = True
    except Exception as e:
        data_response["error"] = e

    return data_response
 

   
def parse_tokens(content):
    """
    Take's the content of a page and returns the
    stateful tokens associated with authentication requests.

    Params:
        (bytes)content - The content of a requests object.

    Returns:
        dict - Dictionary of strings containing flowToken
               and ctx keys.

    Example:
        >> tokens = parse_tokens(r.content)
        >> tokens
        {
            "flowToken": "AAQbZ...",
            "ctx": "rQIA..."
        }
    """
    sFTIndex = content.index(b'sFT":"')
    sFTIndex += 6
    endFTIndex = content.index(b'"', sFTIndex)
    flowToken = content[sFTIndex:endFTIndex].decode()
    sCtxIndex = content.index(b'sCtx":"')
    sCtxIndex += 7
    endCtxIndex = content.index(b'"', sCtxIndex)
    ctx = content[sCtxIndex:endCtxIndex]
    results = {
        "flowToken": flowToken,
        "ctx": ctx
    }
    return results
