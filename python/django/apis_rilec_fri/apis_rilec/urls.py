from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views

app_name = 'apis_rilec'
urlpatterns = [
    path('', views.index, name='index'),
    path('hr/HRMaster/replicate', csrf_exempt(views.hrmaster_replicate), name='hrmaster_replicate'),
    path('userprofile/<str:date_str>/', views.userprofile_list, name='userprofile_list'),
    path('userprofile/<str:date_str>/<str:user_id>', views.userprofile_detail, name='userprofile_detail'),
]

