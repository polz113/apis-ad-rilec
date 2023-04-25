from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'apis_rilec'
urlpatterns = [
    path('', views.index, name='index'),
    path('hr/HRMaster/replicate', csrf_exempt(views.hrmaster_replicate), name='hrmaster_replicate'),
    path('mergeduserdata', views.mergeduserdata_list, name='mergeduserdata_list'),
    path('mergeduserdata/<str:user_id>', views.mergeduserdata_detail, name='mergeduserdata_detail'),
    path('userproperties', views.userproperty_list, name='userproperty_list'),
    path('rules/', views.rule_list, name='rule_list'),
    path('rules/USER_RULES', views.user_rules, name='user_rules'),
    path('rules/<str:rules_part>', views.generic_rule_detail, name='generic_rule_detail'),
]

