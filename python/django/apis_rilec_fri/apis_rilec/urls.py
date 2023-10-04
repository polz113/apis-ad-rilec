from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'apis_rilec'
urlpatterns = [
    path('', views.index, name='index'),
    path('hr/HRMaster/replicate', csrf_exempt(views.hrmaster_replicate), name='hrmaster_replicate'),
    path('datasources_to_datasets', views.datasources_to_datasets, name='datasources_to_datasets'),
    path('get_data_studis', views.get_data_studis_view, name='get_data_studis'),
    path('mergeduserdata/', views.mergeduserdata_list, name='mergeduserdata_list'),
    path('mergeduserdata_fields/', views.MergedUserdataFieldsView.as_view(), name='mergeduserdata_fields'),
    path('mergeduserdata/<str:user_id>', views.mergeduserdata_detail, name='mergeduserdata_detail'),
    path('delete_old_userdata', views.delete_old_userdata_view, name='delete_old_userdata'),
    path('user_rilec_save', views.user_rilec_save_view, name='user_rilec_save'),
    path('save_ldap', views.save_ldap_view, name='save_ldap'),
    path('autogroup_ldapobjects', views.autogroup_ldapobjects_view, name='autogroup_ldapobjects'),
    path('userproperties', views.userproperty_list, name='userproperty_list'),
    path('rules/', views.rule_list, name='rule_list'),
    path('rules/USER_RULES', views.user_rules, name='user_rules'),
    path('rules/TRANSLATIONS', views.translations, name='translations'),
    path('rules/GROUP_RULES', views.group_rules, name='group_rules'),
    path('rules/<str:rules_part>', views.generic_rule_detail, name='generic_rule_detail'),
    path('ldapobjectbatch/', views.ldapobjectbatch_list, name='ldapobjectbatch_list'),
    path('ldapobjectbatch/<int:pk>', views.ldapobjectbatch_detail, name='ldapobjectbatch_detail'),
    path('ldapobjectbatch/<int:pk>/diff/<int:pk2>', views.ldapobjectbatch_diff, name='ldapobjectbatch_diff'),
    path('ldapobjectbatch/<int:pk>/diff/<int:pk2>/toldap', views.ldapobjectbatch_diff_to_ldap, name='ldapobjectbatch_diff_to_ldap'),
    path('ldapobjectbatch/<int:pk>/toldap', views.ldapobjectbatch_to_ldap, name='ldapobjectbatch_to_ldap'),
    path('ldapobject/', views.ldapobject_list, name='ldapobject_list'),
    path('ldapobject/<int:pk>', views.ldapobject_detail, name='ldapobject_detail'),
    path('ldapobject/<int:pk>/diff/<int:pk2>', views.ldapobject_diff, name='ldapobject_diff'),
    path('ldapobject/<int:pk>/latest', views.latest_ldapobject, name='latest_ldapobject'),
    path('ldapobject/<int:pk>/save_<slug:source>', views.ldapobject_save, name='ldapobject_save'),
    path('ldapobject/<int:pk>/toldap', views.ldapobject_to_ldap, name='ldapobject_to_ldap'),
    path('ldapobject/<int:pk>/diff/<int:pk2>/toldap', views.ldapobject_diff_to_ldap, name='ldapobject_diff_to_ldap'),
    path('ldapapplybatch/', views.ldapapplybatch_list, name='ldapapplybatch_list'),
    path('ldapapplybatch/<int:pk>', views.ldapapplybatch_detail, name='ldapapplybatch_detail'),
    path('ldapapply/<int:pk>', views.ldapapply_detail, name='ldapapply_detail'),
 
]

