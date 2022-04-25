def validate(args):
    if 'host' in args.keys():
        return True, None
    else:
        error = "Missing host argument, specify as --host 1.2.3.4"
        return False, error
    if 'port' in args.keys():
        return True, None
    else:
        error = "Missing port argument, specify as --port 50050"
        return False, error
