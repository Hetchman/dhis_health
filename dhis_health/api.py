import json
import requests
from django.conf import settings

BASE_URL = "https://play.dhis2.org/dev/api"

AUTH = (settings.AUTH_ID,settings.AUTH_PASS)


class AuthMissingError(Exception):
   pass

if AUTH is None:
   raise AuthMissingError(
	  "All methods require a username and password"
   )

session = requests.Session()
session.auth = AUTH

def analytics_api(payload={}):
	path = "/analytics.json"
	
	if not payload.get("dx") or not payload.get("ou") or not payload.get("pe"):
		return json.dumps({"404" : "Cant have null parameters"})
	
	ou = payload["ou"].split(",")
	dx = payload["dx"].split(",")
	
	params = {
			"dimension": ["ou:"+';'.join(ou), "pe:"+ payload["pe"]],
			"filter": ["dx:"+';'.join(dx)],
			"skipMeta": "true",
			"displayProperty": "NAME"
				}
	url = BASE_URL + path
	session.params = params
	response = session.get(url)
	rows = response.json()["rows"]
	
	data = {}
	for ou_id in ou:
		data[ou_id]=[]
		for key, value in enumerate(rows):
			if ou_id == value[0]:
				data[ou_id].append({value[1]:value[2]})

	return data

def indicators_api(payload={}):
	path = "/indicatorGroups" if payload.get("kind") == "group" else "indicators"
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

def poly_units_geojson(level=2):
	path = "/geoFeatures.json"
	params = {
		'ou': ['ou:LEVEL-'+str(level)]
	}
	url = BASE_URL + path
	session.params = params
	response = session.get(url)
	level2 = response.json()
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

def analytics_data(analytic_data, level):
	def get_org_name(id_key):
		for k, v in enumerate(organisationUnits_api({})):
			if k == id_key:
				return v
	columns = {
			"records" : []
			}
	orgs = []

	for i, j in analytic_data.items():
		for v in range(len(j)):
			for m,n in j[v].items():
				dat = {}
				org = i
				orgs.append(org)
				pe = m
				val = n
				dat['Organisation Unit'] = org
				dat['pe'] = pe
				dat['val'] = float(val)
				columns['records'].append(dat)

	unique_orgs = set(orgs)

	def get_geojson_pk():
		x = poly_units_geojson(level)
	
	collection={}   

	for org in unique_orgs:
		collection[org] = [{"period" : [], "value" : [], "name" : '', "average" : ''}]
		
	geojson = poly_units_geojson()
	
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
					feat = geojson["features"][i]
					id = feat["id"]
					if x == id:
						total = sum(collection[x][0]["value"])
						av = total / len(collection[x][0]["period"])
						feat["properties"]['average'] = av
				
	collection["geojson"] = geojson
	return json.dumps(collection) 
	

