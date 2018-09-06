def validate(args):
    if 'ciscourl' in args.keys():
        return True,None
    else:
        error = "Missing ciscourl argument, specify as --ciscourl sub.org.com"
        return False,error
