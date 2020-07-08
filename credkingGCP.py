#!/usr/bin/python3
import requests
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account
from pprint import pprint
sa_file = 'service-account.json'
credentials = service_account.Credentials.from_service_account_file(sa_file)

service = build('cloudfunctions','v1',credentials=credentials)


#TODO Get Project
project = 'projects/canvas-network-282101'

#TODO: Get Locations
locations = service.projects().locations().list(name=project).execute()
print(len(locations['locations']))
#print(json.dumps(locations,indent=2))
print(locations['locations'][0])

print(service.projects().locations().functions().list(parent=locations['locations'][0]['name']).execute())

#TODO: Generate Upload URL

#TODO: Upload Code
'''This needs to be done via the rest API via signed url - need to read up on what that is:w'''

#TODO: Create Function 

#TODO: Modify Pluging to work in GCP and AWS

#TODO: Thread the above code

#TODO: Delete Function

#TODO: Delete Code

