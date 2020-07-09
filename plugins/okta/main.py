import requests
import json,datetime

def lambda_handler(event, context=None):
	if isinstance(event,dict):
		domain = event['args']['oktadomain']
		return okta_authenticate(domain, event['username'], event['password'], event['useragent'])
	else:
		# TODO: This is needed for GCP as the argument is flask.Request
		request_json = event.get_json(silent=True)
		request_args = event.args
		username = ""
		if request_json and 'username' in request_json:
			username = request_json['username']
			password = request_json['password']
			useragent = request_json['useragent']
			domain = request_json['args']['oktadomain']
			return json.dumps(okta_authenticate(domain, username, password, useragent))
		elif request_args and 'username' in request_args:
			username = request_args['username']
			password = request_args['password']
			useragent = request_args['useragent']
			domain = request_args['args']['oktadomain']
			return json.dumps(okta_authenticate(domain, username, password, useragent))
		else:
			return f'Error'




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

	payload = {"username":username, "password":password, "options":{"warnBeforePasswordExpired":True, "multiOptionalFactorEnroll":True}}
	url = "https://%s/api/v1/authn/" % domain
	
	try:
		resp = requests.post(url,data=json.dumps(payload),headers={'Content-Type':'application/json', 'User-Agent':useragent})
		if resp.status_code == 200:
			resp_json = json.loads(resp.text)
			if resp_json.get("status") == "LOCKED_OUT": #Warning: administrators can configure Okta to not indicate that an account is locked out. Fair warning ;)
				data_response['success'] = False
				data_response['error'] ='locked out'
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
