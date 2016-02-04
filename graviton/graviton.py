import six
import six.moves.urllib.request

if six.PY2:
    from httplib import HTTPConnection
else:
    from http.client import HTTPConnection

import json
import time
import os

baseurl = "genetrail2.bioinf.uni-sb.de"
basepath= ""

con = HTTPConnection(baseurl)
con.connect()

def handleResponse(response):
    message = response.read()
    try:
        result = json.loads(message.decode("utf-8"));
    except ValueError:
        raise ValueError("Unexpected server response from server: " + str(message))

    return (result, response.status);

def doGet(endpoint):
    headers = {
        "Content-type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }

    con.request("GET", basepath + endpoint)

    return handleResponse(con.getresponse())

def doPost(endpoint, **kwargs):
    headers = {
        "Content-type": "application/x-www-form-urlencoded"
    }

    data = urllib.parse.urlencode(kwargs)

    con.request("POST", basepath + endpoint, data, headers)

    return handleResponse(con.getresponse())

def getSession():
    response, code = doGet('/api/session')

    if code != 200:
        raise ValueError("Unexpected server response. Unable to obtain API key.")

    print("Key is: " + response["session"])

    return response["session"]

def uploadFile(key, path):
    f = open(path, 'r')
    content = f.read()
    f.close()

    res, status = doPost('/api/upload?session=' + key,
        value = content,
		displayName = os.path.basename(path)
    )

    if res["status"] != "success":
        raise ValueError("Error during upload: " + res["message"])

    return res["results"]["result"]

def uploadReference(key, path):
    f = open(path, 'r')

    content = f.read()
    f.close()

    res, status = doPost('/api/upload/list?session=' + key,
        list = content,
        reference = True
    )

    if res["status"] != "success":
        raise ValueError("Error during upload: " + res["message"])

    return res["results"]["result"]

def mapResource(key, res, identifier, variant = None):
    if variant == None:
        variant = "default"

    res, status = doPost('/api/map/%d/%s/%s?session=%s' % (res, identifier, variant, key))

    if res["status"] != "success":
        raise ValueError("Error during mapping: " + res["message"])

    return res["results"]["result"]["id"]

def setupEnrichment(key, method, res, categories, **kwargs):
    res, status = doPost('/api/job/setup/%s?session=%s' % (method, key),
        significance=0.05,
        adjustment="benjamini_hochberg",
        categories=json.dumps(categories),
        minimum=3,
        maximum=500,
        adjustSeparately=True,
        input=str(res),
        **kwargs
    )

    if res["status"] != "success":
        raise ValueError("Could not setup service: " + res["message"])

def setupScoring(key, method, **kwargs):
    res, status = doPost('/api/job/setup/scoring?session=%s' % key,
        method = method,
        **kwargs
    )

def setupORA(key, res, categories, ref):
    return setupEnrichment(key, "ora", res, categories, reference="/user/" + str(ref));

def setupFilter(key, resource, f, param):
	res, status = doPost('/api/job/setup/scoreFilter?session=%s' % key,
		input = resource,
		filters = '["%s:%f"]' % (f, param)
	)

	if res["status"] != "success":
		raise ValueError("Error during filter setup: " + res["message"])

def getCategories(organism, pipeline):
    res, status = doGet('/api/categories?organism=%d&pipeline=%s' % (organism, pipeline))

    if status != 200:
        raise ValueError('Could not retrieve categories: ' + res['message'])

    return res

def runJob(key):
    doGet('/api/job/start?session=' + key)
    while True:
        time.sleep(2)
        res, code = doGet('/api/job/query?session=' + key)
        if res["status"] == 'status':
            print(res["message"])
        elif res["status"] == 'success':
            return res["results"]
        else:
            raise ValueError("Unexpected status during computation: '" + res["message"] + "'")

def downloadResult(key, res, path):
    url = "http://%s%s/api/resource/%s/download/?session=%s" % (baseurl, basepath, str(res), key)
    urllib.request.urlretrieve(url, path)
