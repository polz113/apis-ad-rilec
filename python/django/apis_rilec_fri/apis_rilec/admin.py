from django.contrib import admin
from django.db import models
from django import forms


from .models import DataSource, DataSet,\
    OUData, OURelation, MergedUserData, UserData, UserDataField,\
    TranslationTable, TranslationRule,\
    LDAPActionBatch, LDAPAction, LDAPApply,\
    user_ldapactionbatch

# Register your models here.
class DataSourceAdmin(admin.ModelAdmin):
    actions = ['to_datasets']
    # list_display = ['str_data']
    # readonly_fields = ['str_data']
    
    @admin.display(description="Raw data")
    def str_data(self, instance):
        return instance.data.decode('utf-8')
        # return instance.str_data()

    @admin.action(description='Turn into datasets')
    def to_datasets(self, request, queryset):
        for i in queryset.all():
            i.to_datasets()

class TranslationRuleInline(admin.TabularInline):
    model = TranslationRule

class TranslationTableAdmin(admin.ModelAdmin):
    inlines = [
        TranslationRuleInline,
    ]

class UserDataFieldInline(admin.TabularInline):
    model = UserDataField

class UserDataAdmin(admin.ModelAdmin):
    inlines = [
        UserDataFieldInline,
    ]


class MergedUserDataAdmin(admin.ModelAdmin):
    raw_id_fields = ['data']
    # readonly_fields = ['data']
    actions = ['to_ldapactionbatch']
    @admin.action(description="Convert to LDAPActionBatch")
    def to_ldapactionbatch(self, request, queryset):
        user_ldapactionbatch(queryset.all())


class LDAPActionBatchAdmin(admin.ModelAdmin):
    actions = ['apply', 'prune']

    @admin.action(description='Prune')
    def prune(self, request, queryset):
        for i in queryset.all():
            i.prune()

    @admin.action(description='Apply')
    def apply(self, request, queryset):
        for i in queryset.all():
            i.apply()

class LDAPActionAdmin(admin.ModelAdmin):
    actions = ['apply']
    raw_id_fields = ['sources']

    @admin.action(description='Apply')
    def apply(self, request, queryset):
        for i in queryset.all():
            i.apply()


admin.site.register(DataSource, DataSourceAdmin)
admin.site.register(DataSet)
admin.site.register(OUData)
admin.site.register(TranslationTable, TranslationTableAdmin)
admin.site.register(UserData, UserDataAdmin)
admin.site.register(MergedUserData, MergedUserDataAdmin)
admin.site.register(LDAPActionBatch, LDAPActionBatchAdmin)
admin.site.register(LDAPAction, LDAPActionAdmin)
admin.site.register(LDAPApply)
