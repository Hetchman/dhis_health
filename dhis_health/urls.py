from django.conf.urls import url
from . import views

app_name = 'dhis_health'
urlpatterns=[
	url(r'^org_units/$', views.organisation_unit_view, name='org_units'),
	url(r'^anc_map.data/$', views.anc_map_view, name='anc_map'),
	url(r'^map_view/$', views.map_view.as_view(), name='map_view'),
	url(r'^charts_view/$', views.chart_view.as_view(), name='charts_view'),
	url(r'^chart_test/$', views.charts_view, name='chart_test')
	]