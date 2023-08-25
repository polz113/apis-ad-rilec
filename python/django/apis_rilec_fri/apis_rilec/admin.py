from django.contrib import admin
from django.db import models
from django import forms
from django.utils.translation import gettext_lazy as _

from .models import DataSource, DataSet,\
    OUData, OURelation, MergedUserData, UserData, UserDataField,\
    LDAPObject, LDAPObjectBatch,\
    LDAPApply, LDAPApplyBatch,\
    TranslationTable, TranslationRule

# Register your models here.
class DataSourceAdmin(admin.ModelAdmin):
    actions = ['to_datasets']
    # list_display = ['str_data']
    readonly_fields = ['str_data']
    
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


class OldUserdataFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _("Used in MultiuserData")

    # Parameter for the filter that will be used in the URL query.
    parameter_name = "old_unused"

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return [
            ("never", _("Never")),
        ]

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == "never":
            return queryset.filter(
                mergeduserdata=None
            )


class UserDataAdmin(admin.ModelAdmin):
    inlines = [
        UserDataFieldInline,
    ]
    list_filter = [OldUserdataFilter]


class LDAPObjectAdmin(admin.ModelAdmin):
    pass


class MergedUserDataAdmin(admin.ModelAdmin):
    raw_id_fields = ['data']
    # readonly_fields = ['data']
    #actions = ['to_ldapactionbatch']
    #@admin.action(description="Convert to LDAPActionBatch")
    #def to_ldapactionbatch(self, request, queryset):
    #    user_ldapactionbatch(queryset.all())


admin.site.register(DataSource, DataSourceAdmin)
admin.site.register(DataSet)
admin.site.register(OUData)
admin.site.register(TranslationTable, TranslationTableAdmin)
admin.site.register(UserData, UserDataAdmin)
admin.site.register(MergedUserData, MergedUserDataAdmin)
admin.site.register(LDAPObject)
admin.site.register(LDAPObjectBatch)
admin.site.register(LDAPApply)
admin.site.register(LDAPApplyBatch)
