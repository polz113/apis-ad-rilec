from django.contrib import admin

from .models import DataSource, DataSet,\
    OUData, OURelation, UserData, UserDataField,\
    TranslationTable, TranslationRule,\
    LDAPActionBatch, LDAPAction, LDAPApply

# Register your models here.

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

admin.site.register(DataSource)
admin.site.register(DataSet)
admin.site.register(OUData)
admin.site.register(TranslationTable, TranslationTableAdmin)
admin.site.register(UserData, UserDataAdmin)
admin.site.register(LDAPActionBatch)
admin.site.register(LDAPAction)
admin.site.register(LDAPApply)
