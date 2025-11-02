from django.contrib import admin
from django.db import models
from django import forms
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
import json

from .models import DataSource, DataSet,\
    OUData, OURelation, MergedUserData, UserData, UserDataField,\
    LDAPObject, LDAPObjectBatch,\
    LDAPApply, LDAPApplyBatch,\
    TranslationTable, TranslationRule


# Register your models here.
class DataSetAdmin(admin.ModelAdmin):
    raw_id_fields = ('source',)
    readonly_fields = ('source', 'data_links', 'source_data')

    @admin.display(description="UserData")
    def data_links(self, instance):
        return format_html_join(
            mark_safe("<br>"),
            """<a href="{}">{}: {}({})</a>""",
            [(reverse("admin:apis_rilec_userdata_change", args=(d.id,)), d.id, d.uid, d.sub_id) for d in instance.userdata_set.all()],
        )
    
    @admin.display(description="Source data")
    def source_data(self, instance):
        return format_html("<pre>{}</pre>", json.dumps(instance.source.parsed_json(), indent=4))

class DataSourceAdmin(admin.ModelAdmin):
    actions = ('to_datasets',)
    # list_display = ['str_data']
    readonly_fields = ('str_data', 'dataset_links')
    list_filter = ["source"] 
    search_fields = ["timestamp"] 
    
    @admin.display(description="Raw data")
    def str_data(self, instance):
        return instance.data.decode('utf-8')
        # return instance.str_data()

    @admin.display(description="DataSet")
    def dataset_links(self, instance):
        # return "HEH:" + str(instance.dataset_set.all())
        return format_html_join(
            mark_safe("<br>"),
            """<a href="{}">{}</a>""",
            [(reverse("admin:apis_rilec_dataset_change", args=(d.id,)), d.id) for d in instance.dataset_set.all()],
        )

    @admin.action(description='Turn into datasets')
    def to_datasets(self, request, queryset):
        for i in queryset.all():
            i.to_datasets()


class TranslationRuleInline(admin.TabularInline):
    model = TranslationRule


class TranslationTableAdmin(admin.ModelAdmin):
    raw_id_fields = ('dataset',)
    readonly_fields = ('dataset',)
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
    raw_id_fields = ('dataset',)
    readonly_fields = ('dataset',)
    inlines = [
        UserDataFieldInline,
    ]
    list_filter = [OldUserdataFilter]
    search_fields = ["uid", "sub_id"] 


class LDAPObjectAdmin(admin.ModelAdmin):
    raw_id_fields = ('dataset',)
    readonly_fields = ('dataset',)


class OUDataAdmin(admin.ModelAdmin):
    raw_id_fields = ('dataset',)
    readonly_fields = ('dataset',)


class MergedUserDataAdmin(admin.ModelAdmin):
    raw_id_fields = ['data']
    readonly_fields = ['data_links', 'with_extra']
    search_fields = ['uid',]
    
    @admin.display(description="UserData")
    def data_links(self, instance):
        return format_html_join(
            mark_safe("<br>"),
            """<a href="{}">{}: {}({})</a>""",
            [(reverse("admin:apis_rilec_userdata_change", args=(d.id,)), d.id, d.uid, d.sub_id) for d in instance.data.all()],
        )

    @admin.display(description="As dicts")
    def with_extra(self, instance):
        s = mark_safe("")
        for fieldset in instance.with_extra():
            s += mark_safe("<ul>")
            for k in sorted(fieldset.keys()):
                s += format_html("<li><span>{}:</span>", k)
                l = [(i,) for i in fieldset.getlist(k, [])]
                s += format_html_join(",", "{}", l)
                s += mark_safe("</li>")
            s += mark_safe("</ul>")
        return s
    # readonly_fields = ['data']
    #actions = ['to_ldapactionbatch']
    #@admin.action(description="Convert to LDAPActionBatch")
    #def to_ldapactionbatch(self, request, queryset):
    #    user_ldapactionbatch(queryset.all())


admin.site.register(DataSource, DataSourceAdmin)
admin.site.register(DataSet, DataSetAdmin)
admin.site.register(OUData, OUDataAdmin)
admin.site.register(TranslationTable, TranslationTableAdmin)
admin.site.register(UserData, UserDataAdmin)
admin.site.register(MergedUserData, MergedUserDataAdmin)
admin.site.register(LDAPObject)
admin.site.register(LDAPObjectBatch)
admin.site.register(LDAPApply)
admin.site.register(LDAPApplyBatch)
