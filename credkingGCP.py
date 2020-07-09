#!/usr/bin/python3
import requests
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.cloud import storage
from pprint import pprint
from threading import Lock, Thread
lock = Lock()
import json, sys, random, string, ntpath, time, os, datetime, queue, shutil
sa_file = 'service-account.json'
credentials = service_account.Credentials.from_service_account_file(sa_file)

service = build('cloudfunctions','v1',credentials=credentials)

storage_service = build('storage','v1',credentials=credentials)


#TODO Get Project
#project = 'projects/canvas-network-282101'

# Delete a file from a bucket
#blob.delete()

# Delete bucket
#print(storage_service.buckets().delete(bucket="credkinggcp123456").execute())


#print(storage_service.buckets().list(project=project).execute())

'''
#TODO: Get Locations
locations = service.projects().locations().list(name=project).execute()
print(len(locations['locations']))
#print(json.dumps(locations,indent=2))
print(locations['locations'][0])

#print(service.projects().locations().functions().list(parent=locations['locations'][0]['name']).execute())

#TODO: Generate Upload URL
uploadURL = service.projects().locations().functions().generateUploadUrl(parent=locations['locations'][0]['name']).execute()
print(uploadURL['uploadUrl'])
'''

#TODO: Upload Code
'''This needs to be done via the rest API via signed url - need to read up on what that is'''
# Creating a bucket
project = 'canvas-network-282101'

# Creating a bucket
body = {'name':'credkinggcp123456'}
#print(storage_service.buckets().insert(project=project,predefinedAcl="projectPrivate",body=body).execute())

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
        print('Creating build deployment for plugin: {}'.format(plugin))
        shutil.make_archive(build_zip[0:-4], 'zip', plugin_path)

    return build_zip

path = create_zip('okta')
blob = bucket.blob('test.zip')
print(blob.upload_from_filename(path))



#TODO: Create Function 

#TODO: Modify Pluging to work in GCP and AWS

#TODO: Thread the above code

#TODO: Delete Function

#TODO: Delete Code

