import six
from six.moves import urllib

if six.PY2:
    from httplib import HTTPSConnection
else:
    from http.client import HTTPSConnection

import json
import time
import os

baseurl = "genetrail2.bioinf.uni-sb.de"
basepath= ""

con = HTTPSConnection(baseurl)
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

def setupReggae(key, scores, matrix, order, method, impactScore, confidenceIntervals, regulations, **kwargs):
	if not (order in ["increasingly", "decreasingly"]):
		raise ValueError('order has to be one of the following: "increasingly", "decreasingly"')
	if not (method in ["wrs-test", "ks-test"]):
		raise ValueError('method has to be one of the following: "wrs-test", "ks-test"')
	if not (impactScore in ["pearson_correlation", "spearman_correlation"]):
		raise ValueError('impactScore has to be one of the following: "pearson_correlation", "spearman_correlation"')
	if not (confidenceIntervals in ["percentile", "bca"]):
		raise ValueError('confidenceIntervals has to be one of the following: "percentile", "bca"')
	
	res, status = doPost('/api/job/setup/reggae?session=%s' % key,
       		scores = scores
        	matrix = matrix
		order = order,
		method = method,
		impactScore = impactScore,
		confidenceIntervals = confidenceIntervals,
		regulations = regulations
		**kwargs
	)

	if res["status"] != "success":
		raise ValueError("Error during filter setup: " + res["message"])

def setupRIF(which, key, scoring_mode, **kwargs):
	if not (str(which) in ["1", "2"]):
		raise ValueError('which has to be one of the following: "1", "2"')
	if not (scoring_mode in ["raw", "standardize"]):
		raise ValueError('scoring_mode has to be one of the following: "raw", "standardize"')
	
	res, status = doPost('/api/job/setup/rif%s?session=%s' % (str(which), key),
		adjustment="benjamini_hochberg",
		scoring_mode = scoring_mode,
		**kwargs
	)

	if res["status"] != "success":
		raise ValueError("Error during setup service: " + res["message"])

def setupRIF1(key, scoring_mode, **kwargs):
	setupRIF(1, key, scoring_mode, **kwargs)

def setupRIF2(key, scoring_mode, **kwargs):
	setupRIF(2, key, scoring_mode, **kwargs)

def setupTepic(key, intervals, windowSize, geneList="",duplicateMethod="median"):
	
	if windowSize < 0.0:
		raise ValueError("windowSize has to be non-negative")
	
	res, status = doPost('/api/job/setup/tepic?session=%s' % key,
		intervals = intervals,
		geneList = geneList,
		window = windowSize,
		duplicateMethod = duplicateMethod
	)
	
	if res["status"] != "success":
		raise ValueError("Error during setup service: " + res["message"])

def setupInvoke(key, **kwargs):
	res, status = doPost('/api/job/setup/tepic?session=%s' % key,
		**kwargs
	)
	
	if res["status"] != "success":
		raise ValueError("Error during setup service: " + res["message"])

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
