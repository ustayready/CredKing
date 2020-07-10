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


#TODO Get Project
project = 'canvas-network-282101'

def log_entry(entry):
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{ts}] {entry}')

#print(service.projects().locations().functions().list(parent=locations['locations'][0]['name']).execute())


# Uploading Code
# Creating a bucket
project = 'canvas-network-282101'

# Creating a bucket
body = {'name':'credkinggcp123456'}
log_entry(storage_service.buckets().insert(project=project,predefinedAcl="projectPrivate",body=body).execute())

# Uploading a file from a created bucket
storage_client = storage.Client(project=project,credentials=credentials)
bucket = storage_client.bucket('credkinggcp123456')

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

def create_bucket(plugin):
    path = create_zip(plugin)
    blob = bucket.blob('test.zip')
    blob.upload_from_filename(path)
    object_url = f'gs://{blob.bucket.name}/{blob.name}'
    return object_url

sourceURL = create_bucket('okta')

# Get Locations
locations = service.projects().locations().list(name=f'projects/{project}').execute()
log_entry(len(locations['locations']))
#print(json.dumps(locations,indent=2))
log_entry(locations['locations'][0])

function_name = 'function-3'
name = f"{locations['locations'][0]['name']}/functions/{function_name}"
log_entry(name)

# Create Function
body =  {
        #"name": "projects/canvas-network-282101/locations/us-central1/functions/function-3",
        "name" : name,
        "availableMemoryMb": 128,
        "entryPoint": "lambda_handler",
        "description": "Test function",
        "timeout": "60s",
        "runtime": "python37",
        "ingressSettings": "ALLOW_ALL",
        "maxInstances": 1,
        "sourceArchiveUrl": sourceURL,
        "httpsTrigger": {},
        "vpcConnector": "",
        "serviceAccountEmail": credentials.service_account_email
        }
log_entry(service.projects().locations().functions().create(location=locations['locations'][0]['name'],body=body).execute())

# Get Status of the function and make sure that it is active
while True:
    sleep = 5
    status = service.projects().locations().functions().get(name="projects/canvas-network-282101/locations/us-central1/functions/function-3").execute()
    if status['status'] == 'ACTIVE':
        break
    else:
        log_entry(f"Waiting {sleep} seconds for function to become ACTIVE")
        time.sleep(sleep)

# Call Function
data = {"username": "test.test2", "password": "Spring2018", "useragent": "test", "args": {"oktadomain": "cardinalb2e.okta.com"}}
body = {"data": json.dumps(data)}
#body = {"data": "{\"username\": \"test.test1\", \"password\": \"Spring2018\", \"useragent\": \"test\", \"args\": {\"oktadomain\": \"cardinalb2e.okta.com\"}}"}
log_entry(service.projects().locations().functions().call(name="projects/canvas-network-282101/locations/us-central1/functions/function-3",body=body).execute())


# Delete Function
log_entry(service.projects().locations().functions().delete(name="projects/canvas-network-282101/locations/us-central1/functions/function-3").execute())

# Delete Code
blob = bucket.blob('test.zip')
blob.delete()
bucket.delete()


# Delete Zip
filelist = [ f for f in os.listdir('build') if f.endswith(".zip") ]
for f in filelist:
    os.remove(os.path.join('build', f))
    log_entry(f"Removing file {f}")

# TODO: Parameterize above
# TODO: Make into functions with a main method

# TODO: Thread the above code
