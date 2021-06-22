def validate(args):
    if 'url' in args.keys():
        return True, None
    else:
        error = "Missing url argument, specify as --url http://host/login"
        return False, error
