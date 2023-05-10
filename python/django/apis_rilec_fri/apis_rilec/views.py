from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from itertools import chain
from django.contrib.admin.views.decorators import staff_member_required
import logging
import ldap

from .models import DataSource, MergedUserData, LDAPActionBatch, LDAPAction, UserDataField,\
        get_rules, dicts_to_ldapuser, dicts_to_ldapgroups,\
        delete_old_userdata, user_ldapactionbatch, group_ldapactionbatch

# Create your views here

logger = logging.getLogger(__name__)

def index(request):
    return render(request, 'apis_rilec/index.html')

def hrmaster_replicate(request):
    if request.headers['X-Api-Key'] != settings.X_API_KEY:
        response = JsonResponse({'result': 'Unauthorized'})
        response.status_code=401
        logger.error('failed replicate:{}'.format(request.headers))
        return response
    if request.method == 'PUT' or request.method == 'POST':
        hrmaster = DataSource(source='apis', timestamp=timezone.now(), data=request.body)
        hrmaster.save()
        return JsonResponse({'result': 'OK'})
    elif request.method == 'GET':
        sources = DataSource.objects.filter(source='apis').order_by('timestamp').iterator()
        try:
            s0 = next(sources)
        except StopIteration:
            return JsonResponse([], safe=False)
        return StreamingHttpResponse(
            chain([b"[\n", s0.data], (b", " + source.data for source in sources), [b"]\n"]),
            content_type="application/json",
        )
    return JsonResponse({'result': 'UNSUPPORTED METHOD'})
        

@staff_member_required
def mergeduserdata_list(request):
    mudl = MergedUserData.objects.all()
    return render(request, 'apis_rilec/mergeduserdata_list.html', {'object_list': mudl})


@staff_member_required
def mergeduserdata_detail(request, user_id):
    try:
        ldap_conn = ldap.initialize(settings.LDAP_SERVER_URI)
        ldap_conn.simple_bind_s(settings.LDAP_BIND_DN, settings.LDAP_BIND_PASSWORD)
    except Exception as e:
        print(e)
        ldap_conn = None
    mud = get_object_or_404(MergedUserData, uid=user_id)
    user_rules = get_rules('USER_RULES')
    group_rules = get_rules('GROUP_RULES')
    extra_fields = get_rules('EXTRA_FIELDS')
    translations = get_rules('TRANSLATIONS')
    with_extra = mud.with_extra(translations=translations, extra_fields=extra_fields,
                                ldap_conn = ldap_conn)
    by_rules = dicts_to_ldapuser(user_rules, translations, with_extra)
    default_dn, groups = dicts_to_ldapgroups(group_rules, with_extra)
    return render(request, 'apis_rilec/mergeduserdata_detail.html', {
                                'by_rules': by_rules,
                                'with_extra': with_extra,
                                'groups': groups,
                                'default_dn': default_dn,
                                'object': mud
                            })


@staff_member_required
def delete_old_userdata_view(request):
    # if request.method == 'PUT' or request.method == 'POST':
    # TODO fix CSRF vulnerability here
    delete_old_userdata()
    return redirect(reverse("apis_rilec:mergeduserdata_list"))

@staff_member_required
def user_ldapactionbatch_view(request, t=None):
    # if request.method == 'PUT' or request.method == 'POST':
    # TODO fix CSRF vulnerability here
    b = user_ldapactionbatch(t)
    return redirect(b)

@staff_member_required
def group_ldapactionbatch_view(request, t=None):
    # if request.method == 'PUT' or request.method == 'POST':
    # TODO fix CSRF vulnerability here
    b = group_ldapactionbatch(t)
    return redirect(b)

#@staff_member_required

def userproperty_list(request):
    props = UserDataField.objects.values_list('field', flat=True).distinct()
    return render(request, 'apis_rilec/userproperty_list.html', {'object_list': props})

def rule_list(request):
    props = get_rules()
    return render(request, 'apis_rilec/rule_list.html', {'object_list': props})

def user_rules(request):
    extra_fields = get_rules('EXTRA_FIELDS')
    user_rules = get_rules('USER_RULES')
    properties = UserDataField.objects.values_list('field', flat=True).distinct()
    return render(request, 'apis_rilec/user_rules.html', {'properties': properties, 'extra_fields': extra_fields, 'user_rules': user_rules})

def generic_rule_detail(request, rules_part):
    try:
        props = get_rules(rules_part)
    except:
        props = dict()
    return render(request, 'apis_rilec/generic_rule_detail.html', {'object': props, 'rules_part': rules_part})

def group_rules(request):
    props = get_rules('GROUP_RULES')
    return render(request, 'apis_rilec/group_rules.html', {'object': props})

@staff_member_required
def translations(request):
    props = get_rules('TRANSLATIONS')
    return render(request, 'apis_rilec/translations.html', {'object_list': props})

@staff_member_required
def ldapactionbatch_list(request):
    batches = LDAPActionBatch.objects.all()
    return render(request, 'apis_rilec/ldapactionbatch_list.html', {'object_list': batches})

@staff_member_required
def ldapactionbatch_detail(request, pk):
    batch = get_object_or_404(LDAPActionBatch, pk=pk)
    return render(request, 'apis_rilec/ldapactionbatch_detail.html', {'object': batch})

@staff_member_required
def ldapactionbatch_apply(request, pk):
    batch = get_object_or_404(LDAPActionBatch, pk=pk)
    ret = batch.apply() 
    return render(request, 'apis_rilec/ldapactionbatch_apply.html', {'object': batch, 'ret': ret})

@staff_member_required
def ldapactionbatch_prune(request, pk):
    batch = get_object_or_404(LDAPActionBatch, pk=pk)
    ret = batch.prune()
    return render(request, 'apis_rilec/ldapactionbatch_prune.html', {'object': batch, 'ret': ret})
