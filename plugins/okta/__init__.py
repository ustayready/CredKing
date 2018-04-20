def validate(args):
    if 'oktadomain' in args.keys():
        return True,None
    else:
        error = "Missing oktadomain argument, specify as --oktadomain org.okta.com"
        return False,error