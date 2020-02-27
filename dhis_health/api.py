## THE API MODULE SERVES AS THE CORE FOR RETRIEVING AND PROCESSING DATA FOR THE APPLICATION
import json
import requests
from django.conf import settings
from collections import defaultdict

# Base url for dhis2 api
BASE_URL = "https://play.dhis2.org/dev/api"

# Get the id and password for accessing data from dhis2 api
AUTH = (settings.AUTH_ID,settings.AUTH_PASS)


class AuthMissingError(Exception):
   pass

# Raise an error when authorisation is missing
if AUTH is None:
   raise AuthMissingError(
	  "All methods require a username and password"
   )

# Create a requests session and pass in he authorisation for id and password
session = requests.Session()
session.auth = AUTH

# A function that requests for analytical, aggregated data in dhis2 and returns as json format
# Allows requesting data for data elements, periods and organisation units
def analytics_api(payload={}):
    # path for analytics data
    path = "/analytics.json"

    # Check if data elements(dx), period(pe) or organisation units(ou) parameters are input
    # if not notify user to input
	if not payload.get("dx") or not payload.get("ou") or not payload.get("pe"):
		return json.dumps({"404" : "Cant have null parameters"})

    # Gets organisation units and data elements from string input
    ou = payload["ou"].split(",")
	dx = payload["dx"].split(",")

    # Provides parameters for requesting analystics data
    # dimension - dimensions and dimension items to be retrieved
    # filter - filters items to apply to the query
    # skipMeta - skip metadata part of the response
    # displayProperty - property for display for metadata
	params = {
			"dimension": ["ou:"+';'.join(ou), "pe:"+ payload["pe"]],
			"filter": ["dx:"+';'.join(dx)],
			"skipMeta": "true",
			"displayProperty": "NAME"
				}
    # Get full url path for api add parameters, request and return json data for the rows key
	url = BASE_URL + path
	session.params = params
	response = session.get(url)
	rows = response.json()["rows"]

    # Organize the analytics data in a list so as every organisation unit has its values for every year
    # sorted in a key value dictionary where date is key and value is values for the coverage
    data = defaultdict(list)
	for ou_id in ou:
		for value in rows:
			if ou_id == value[0]:
				data[ou_id].append({value[1]:value[2]})

	return data

# Requests for indicators which is a calculated formula based on a combination of data elements
# Indicators can be Maternal mortality unit, Immunizations, ANC, HIV etc
def indicators_api(payload={}):
	path = "/indicatorGroups" if payload.get("kind") == "group" else "indicators"

    # parameters for requesting data
    # paging - indicates whether return lists of elements in pages. Values are true or false
    # fields - indicates the fields to retrieve data from
	params = {
			"paging": "false",
			"fields": ["id", "name", "code"]
			}
	id = payload.get("members")
	if id:
		return indicator_members(id)
	url = BASE_URL + path
	session.params = params
	response = session.get(url)
	return response.json()[path[1:]]

# Retrieves available names of the different organisational units available in dhis2
# Can be regional, national, municipal
# level=2 indicates the districs
def organisationUnits_api(payload={}):
	path = "/organisationUnits"
	params = {
			"level" : 2 if not payload.get("level") else payload["level"],
			"paging" : "false",
			"fields" : ["id", "name", "code"]
			}
	url = BASE_URL + path
	session.params = params
	response = session.get(url)
	return response.json()[path[1:]]

def indicator_members(group_id):
	def get_ids(group_id):
		path = "/indicatorGroups/"+group_id
		url = BASE_URL + path
		res = requests.get(url, auth=session.auth)
		return res.json()["indicators"]
	all_members_id = get_ids(group_id)
	members_list = []
	params = {
			"fields" : ["id", "name"]
			}
	session.params = params
	path = "/indicators/"
	for key, val in enumerate(all_members_id):
		url = BASE_URL + path +val["id"]
		res = session.get(url)
		members_list.append(res.json())
	return members_list

def parseData(payload={}):
	pass

# Retrieve the geospatial data for the various organisational units
# Parses the data from api to geojson used for mapping.
# default level=2 indicates districs
def poly_units_geojson(level=2):
	path = "/geoFeatures.json"
	params = {
		'ou': ['ou:LEVEL-'+str(level)]
	}
	url = BASE_URL + path
	session.params = params
	response = session.get(url)
	level2 = response.json()
    # Create a geojson feature object for representing the spatial data
	feat = {'features': [],'type': 'FeatureCollection', "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } } }
	if level==2 or level==3:
		for n in range(len(level2)):
			feat['features'].append({
			'geometry': {'coordinates': [json.loads(level2[n]['co'])],'type': 'MultiPolygon'},
			'id': level2[n]['id'],
			'properties': {"code": level2[n]['code'],
			"name": level2[n]['na'],
			"parent_graph": level2[n]['pg'],
			"parent_id": level2[n]['pi'],
			"parent_name": level2[n]['pn'],
			"level": level2[n]['le']},
			'type': 'Feature'})
		return feat
	elif level==4:
		  for n in range(len(level2)):
			feat['features'].append({
			'geometry': {'coordinates': [json.loads(level2[n]['co'])],'type': 'Point'},
			'id': level2[n]['id'],
			'properties': {"code": level2[n]['code'],
			"name": level2[n]['na'],
			"parent_graph": level2[n]['pg'],
			"parent_id": level2[n]['pi'],
			"parent_name": level2[n]['pn'],
			"level": level2[n]['le']},
			'type': 'Feature'})
		  return feat

# This function merges analytics data to the geojson for viewing
# Also computes sum of the value for the coverages
def analytics_data(analytic_data, level):
    # Get the names for available organisation units
	def get_org_name(id_key):
		for v in organisationUnits_api({}):
			if v['id'] == id_key:
				return v['name']

    # Create a list to hold the analytics data for better access in the geojson to be merged to
	columns = defaultdict(list)
	orgs = []
	for i, j in analytic_data.items():
		for v in range(len(j)):
			for m,n in j[v].items():
				dat = {}
				orgs.append(i)
				dat['Organisation Unit'] = i
				dat['pe'] = m
				dat['val'] = float(n)
				columns['records'].append(dat)

    # Call the poly_units_geojson function
	def get_geojson_pk():
		x = poly_units_geojson(level)

    unique_orgs = set(orgs)
	collection={}

	for org in unique_orgs:
		collection[org] = [{"period" : [], "value" : [], "name" : '', "average" : ''}]

	geojson = poly_units_geojson()
    
    # Add the organisation units data to the geojson object
	for x in unique_orgs:
		for n in columns["records"]:
			org = n["Organisation Unit"]
			if x == org:
				org_name = get_org_name(x)
				collection[x][0]["period"].append(n['pe'])
				collection[x][0]["value"].append(n['val'])
				collection[x][0]["name"]=org_name
				tot = sum(collection[x][0]["value"])
				av = tot/len(collection[x][0]["period"])
				collection[x][0]["average"] = av

				for i in range(len(geojson["features"])):
					id = geojson["features"][i]['id']
					if x == id:
						geojson['features'][i]["properties"]['average'] = av

	collection["geojson"] = geojson
	return json.dumps(collection)
