CredKing
==================
- [Overview](#overview)
	- [Benefits](#benefits)
- [Basic Usage](#basic-usage)
- [Plugin Usage](#plugin-usage)
    - [Gmail](#gmail)
    - [Okta](#okta)
- [Installation](#installation)
- [Development](#development)
    - [Plugin specific arguments](#plugin-specific-arguments)

## Overview ##
Easily launch a password spray using AWS Lambda across multiple regions, rotating IP addresses with each request.

**Brought to you by:**

![Black Hills Information Security](https://www.blackhillsinfosec.com/wp-content/uploads/2016/03/BHIS-logo-L-300x300.png "Black Hills Information Security")

### Benefits ###

 * Fully supports all AWS Lambda Regions
 * Multi-threaded processing
 * Generates user/password pairs
 * Easily add new plugins
 * Automatically creates execution role and lambdas

## Basic Usage ##
usage: **credking.py** [-h] --plugin PLUGIN [--threads THREADS] --userfile
                   USERFILE --passwordfile PASSWORDFILE --access_key
                   ACCESS_KEY --secret_access_key SECRET_ACCESS_KEY
                   [--useragentfile USERAGENTFILE]

```
Arguments:
  -h, --help                            show this help message and exit
  --plugin PLUGIN                       spraying plugin
  --threads THREADS                     thread count (default: 1)
  --userfile USERFILE                   username file
  --passwordfile PASSWORDFILE           password file
  --access_key ACCESS_KEY               aws access key
  --secret_access_key SECRET_ACCESS_KEY aws secret access key
  --useragentfile                       useragent file
```

## Plugin Usage ##

### Gmail ###
The Gmail plugin does not require any additional arguments.

### Okta ###
The Okta plugin adds a new required argument called oktadomain.

usage: **credking.py** \<usual arugments\> --oktadomain org.okta.com

## Installation ##

### Ubuntu 16.04

You can install and run automatically using Python 3 with the following command:

```bash
$ git clone https://github.com/ustayready/CredKing
$ cd CredKing
~/CredKing$ python3 credking.py
```

Note that Python 3 is required.

**Bug reports, feature requests and patches are welcome.**

## Development ##

You can create new plugins by:

```bash
$ cd plugins
$ mkdir newplugin
$ cd newplugin
$ touch __init__.py
$ touch newplugin.py
```

Next, make sure to include the lambda handler function in your newplugin.py:
```python
def lambda_handler(event, context):
	return your_function(event['username'], event['password'])
```

CredKing generates a deployment zip file which the lambdas receive when they are created. Because of this, CredKing requires the pre-reqs to be installed directly into the newplugin folder. You can accomplish this by:

```bash
$ pip install <pre-req> -t .
```

### Plugin specific arguments ###

Plugin specific arguments can be specified with no modifications to credking.py, simply pass them as *--argumentname value*

If your plugin requirements plugin-specific arguments, you can implement a validate function in the \_\_init\_\_.py file of your plugin directory that will be passed an dictionary of all optional arguments.

Below is an example of plugin arugment validation used by the okta plugin's [\_\_init\_\_.py](plugins/okta/__init__.py).

```python
def validate(args):
    if 'oktadomain' in args.keys():
        return True,None
    else:
        error = "Missing oktadomain argument, specify as --oktadomain org.okta.com"
        return False,error
```

The [okta.py](plugins/okta/okta.py) lambda_handler function then accesses the oktadomain argument as shown below.

```python
def lambda_handler(event, context):
	domain = event['args']['oktadomain']
	return okta_authenticate(domain, event['username'], event['password'], event['useragent'])
```

**That's it, enjoy!**
