from django.contrib import admin

from .models import DataSource, DataSet, OUData, UserData, LDAPActionBatch, LDAPAction, LDAPApply

# Register your models here.

admin.site.register(DataSource)
admin.site.register(DataSet)
admin.site.register(OUData)
admin.site.register(UserData)
admin.site.register(LDAPActionBatch)
admin.site.register(LDAPAction)
admin.site.register(LDAPApply)
