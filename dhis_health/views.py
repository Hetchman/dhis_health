# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
from django.core.serializers import serialize
from django.views import generic
from .api import organisationUnits_api, analytics_api,analytics_data
import json

# Create your views here.

# Calls the organisationUnits_api function then create a view for accessing the organisation units data
def organisation_unit_view(request):
	# Get the id and names of available organisation units to display of tables
	org_units = organisationUnits_api()
	org_id = [i['id'] for i in org_units]
	org_name = [i['name'] for i in org_units]

	if 'orgname' in request.GET:
		items=request.GET['orgname']
		for i,j in zip(org_id, org_name):
			if items == j:
				org_items=zip([i],[j])
	else:
		org_items = zip(org_id, org_name)

	# return HttpResponse(json.dumps(org_items), content_type='json')

	return render(request, 'dhis_health/html/table-basic.html', {

			'org_items' : org_items

			})

# Retrieve ANC_VISITS for the Last 12 months
def analytics_func():
	org_units = organisationUnits_api()
	org_id = [i['id'] for i in org_units]
	org_name= ",".join(org_id)
	par = {'ou': org_name,'dx': 'dwEq7wi6nXV','pe':'LAST_12_MONTHS'}
	anc_visits = analytics_api(par)

	return anc_visits

# Retrieves geojson data to be mapped
def anc_map_view(request):
	# org_units = organisationUnits_api()
	# org_id = [i['id'] for i in org_units]
	# org_name= ",".join(org_id)
	# par = {'ou': org_name,'dx': 'dwEq7wi6nXV','pe':'LAST_12_MONTHS'}
	# anc_visits = analytics_api(par)
	analytics_map = analytics_data(analytics_func(),2)
	# return render(request, 'dhis_health/html/map-google.html', {

	# 		'anc_feat' : analytics_map

	# 		})
	return HttpResponse(analytics_map, content_type='json')

# Retrieves analytics data for creating charts
def charts_view(request):
	dat=[]
	val = []
	anc = analytics_func()
	for i, j in anc.items():
		for v in range(len(j)):
			for m, n in j[v].items():
				dat.append(m)
				val.append(float(n))
				date_val=zip(dat, val)

	unique_date = set(dat)
	sorted_dat = {}

	for mn in unique_date:
		sorted_dat[mn]=[]
		for mnth, values in date_val:
			if mn == mnth:
				sorted_dat[mn].append(values)
	# dt=[]
	# vl=[]
	# for month, value in sorted_dat.items():
	# 	dt.append(month)
	# 	vl.append(value)
	# 	date_value = zip(dt, vl)

	# return render(request, 'dhis_health/ancbar_chart.html',
	# 	{
	# 	'anc_data': date_value
	# 	})
	return HttpResponse(json.dumps(sorted_dat), content_type='json')

# Creates view for the map
class map_view(generic.TemplateView):
	template_name = 'dhis_health/html/map.html'

# Creates view for the charts
class chart_view(generic.TemplateView):
	template_name = 'dhis_health/html/charts.html'
