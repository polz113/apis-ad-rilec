from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'apis_rilec'
urlpatterns = [
    path('', views.index, name='index'),
    path('hr/HRMaster/replicate', csrf_exempt(views.hrmaster_replicate), name='hrmaster_replicate'),
    path('datasources_to_datasets', views.datasources_to_datasets, name='datasources_to_datasets'),
    path('get_data_studis', views.get_data_studis_view, name='get_data_studis'),
    path('mergeduserdata/', views.mergeduserdata_fields, name='mergeduserdata_list'),
    path('mergeduserdata_fields/', views.mergeduserdata_fields, name='mergeduserdata_fields'),
    path('mergeduserdata/<str:user_id>', views.mergeduserdata_detail, name='mergeduserdata_detail'),
    path('delete_old_userdata', views.delete_old_userdata_view, name='delete_old_userdata'),
    path('user_ldapactionbatch', views.user_ldapactionbatch_view, name='user_ldapactionbatch'),
    path('group_ldapactionbatch', views.group_ldapactionbatch_view, name='group_ldapactionbatch'),
    path('userproperties', views.userproperty_list, name='userproperty_list'),
    path('rules/', views.rule_list, name='rule_list'),
    path('rules/USER_RULES', views.user_rules, name='user_rules'),
    path('rules/TRANSLATIONS', views.translations, name='translations'),
    path('rules/GROUP_RULES', views.group_rules, name='group_rules'),
    path('rules/<str:rules_part>', views.generic_rule_detail, name='generic_rule_detail'),
    path('actionbatches/', views.ldapactionbatch_list, name='ldapactionbatch_list'),
    path('actionbatches/<int:pk>', views.ldapactionbatch_detail, name='ldapactionbatch_detail'),
    path('actionbatches/<int:pk>/apply', views.ldapactionbatch_apply, name='ldapactionbatch_apply'),
    path('actions/<int:pk>/apply', views.ldapaction_apply, name='ldapaction_apply'),
    path('actionbatches/<int:pk>/prune', views.ldapactionbatch_prune, name='ldapactionbatch_prune'),
]

