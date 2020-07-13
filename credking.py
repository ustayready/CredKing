import re, argparse, importlib
import credkingGCP
import credkingAWS

def main(args, pargs):
    global start_time, end_time, time_lapse

    thread_count = args.threads
    plugin = args.plugin
    username_file = args.userfile
    password_file = args.passwordfile
    sa_file = args.sa_creds_file
    user_agent_file = args.useragentfile
    print(args.env)

    pluginargs = {}
    for i in range(0, len(pargs) - 1):
        key = pargs[i].replace("--", "")
        pluginargs[key] = pargs[i + 1]

    sa_credentials = credkingGCP.service_account.Credentials.from_service_account_file(sa_file)
    storage_service = credkingGCP.build('storage', 'v1', credentials=sa_credentials)

    # Creating a bucket
    bucket_name = f"credking_{next(credkingGCP.generate_random())}"
    body = {'name': bucket_name}
    credkingGCP.log_entry(storage_service.buckets().insert(project=sa_credentials.project_id, predefinedAcl="projectPrivate",
                                               body=body).execute())


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