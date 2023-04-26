from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'apis_rilec'
urlpatterns = [
    path('', views.index, name='index'),
    path('hr/HRMaster/replicate', csrf_exempt(views.hrmaster_replicate), name='hrmaster_replicate'),
    path('mergeduserdata/', views.mergeduserdata_list, name='mergeduserdata_list'),
    path('mergeduserdata/<str:user_id>', views.mergeduserdata_detail, name='mergeduserdata_detail'),
    path('userproperties', views.userproperty_list, name='userproperty_list'),
    path('rules/', views.rule_list, name='rule_list'),
    path('rules/USER_RULES', views.user_rules, name='user_rules'),
    path('rules/TRANSLATIONS', views.translations, name='translations'),
    path('rules/GROUP_RULES', views.group_rules, name='group_rules'),
    path('rules/<str:rules_part>', views.generic_rule_detail, name='generic_rule_detail'),
    path('actionbatches/', views.ldapactionbatch_list, name='ldapactionbatch_list'),
    path('actionbatches/<int:pk>', views.ldapactionbatch_detail, name='ldapactionbatch_detail'),
]

