from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse, Http404
from django.db.models import F
from django.utils.datastructures import MultiValueDict
from django.utils import timezone
from itertools import chain
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.response import Response

import logging
import ldap

if settings.DEBUG:
    from silk.profiling.profiler import silk_profile
    # def silk_profile(*args, **kwargs):
    #     return lambda func: func
else:
    def silk_profile(*args, **kwargs):
        return lambda func: func


from .models import DataSource, MergedUserData, UserDataField,\
        LDAPObject, LDAPObjectBatch,\
        LDAPApply, LDAPApplyBatch,\
        dicts_to_ldapuser, dicts_to_ldapgroups, ldap_state,\
        get_rules, _get_keep_fields,\
        get_groups,\
        delete_old_userdata,\
        save_rilec, save_ldap, autogroup_ldapobjects,\
        get_data_studis, apis_to_translations, try_init_ldap,\
        DEFAULT_IGNORE_FIELDS, DEFAULT_KEEP_FIELDS

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
        

@silk_profile(name='datasources_to_datasets')
@staff_member_required
def datasources_to_datasets(request):
    for i in DataSource.objects.filter(dataset=None):
        i.to_datasets()
    apis_to_translations()
    return render(request, 'apis_rilec/datasources_to_datasets.html')


@staff_member_required
def get_data_studis_view(request):
    get_data_studis()
    return render(request, 'apis_rilec/get_data_studis.html')


# @silk_profile(name='mergeduserdata list')
@staff_member_required
def mergeduserdata_list(request):
    mudl = MergedUserData.objects.prefetch_related('data', 'data__fields').all()
    return render(request, 'apis_rilec/mergeduserdata_list.html', {'object_list': mudl})


def _mergeduserdata_fields_objs(request, fieldnames):
    objects = UserDataField.objects.select_related('userdata').filter(
            field__in=fieldnames).order_by('userdata__uid', 'userdata__id')
    uids = request.GET.getlist('uid')
    if len(uids):
        objects = objects.filter(userdata__uid__in=uids)
    object_list = []
    old_id = None
    old_uid = None
    fields = MultiValueDict()
    for o in objects:
        if old_id is not None and o.userdata.id != old_id:
            d = {"uid": old_uid, "id": old_id}
            d.update(fields)
            object_list.append(d)
            fields = MultiValueDict()
        old_uid = o.userdata.uid
        old_id = o.userdata.id
        fields.appendlist(o.field, o.value)
    if len(fields):
        d = {"uid": o.userdata.uid, "id": o.userdata.id}
        d.update(fields)
        object_list.append(d)
    return object_list



class MergedUserdataFieldsView(APIView):
    permission_classes = [HasAPIKey | IsAuthenticated]
    def get(self, request, format=None):
        """
        Return the filtered fields
        """
        fieldnames = request.GET.getlist(
            'fieldname',
            ['OsebniPodatki__0002__0__ime', 'OsebniPodatki__0002__0__priimek', 'OsebniPodatki__kadrovskaSt'])
        uids = request.GET.getlist('uid')
        objects = UserDataField.objects.select_related('userdata').\
                filter(field__in=fieldnames).\
                annotate(uid=F('userdata__uid'))
        if len(uids):
            objects = objects.filter(userdata__uid__in=uids)
        return Response(objects.values("field", "value", "uid").order_by("uid").distinct())


@login_required
def mergeduserdata_fields_json(request):
    fieldnames = request.GET.getlist(
            'fieldname',
            ['OsebniPodatki__0002__0__ime', 'OsebniPodatki__0002__0__priimek', 'OsebniPodatki__kadrovskaSt'])
    object_list = _mergeduserdata_fields_objs(request, fieldnames)
    return JsonResponse(object_list, safe=False)


@login_required
def mergeduserdata_fields(request):
    fieldnames = request.GET.getlist(
            'fieldname',
            ['OsebniPodatki__0002__0__ime', 'OsebniPodatki__0002__0__priimek', 'OsebniPodatki__kadrovskaSt'])
    object_list = _mergeduserdata_fields_objs(request, fieldnames)
    return render(request, 'apis_rilec/mergeduserdata_fields.html', {'object_list': object_list, "fieldnames": fieldnames})


@staff_member_required
def mergeduserdata_detail(request, user_id):
    mud = get_object_or_404(MergedUserData, uid=user_id)
    user_rules = get_rules('USER_RULES')
    group_rules = get_rules('GROUP_RULES')
    extra_fields = get_rules('EXTRA_FIELDS')
    translations = get_rules('TRANSLATIONS')
    merge_rules = get_rules('MERGE_RULES')
    with_extra = mud.with_extra(translations=translations, extra_fields=extra_fields)
    by_rules = dicts_to_ldapuser(user_rules=user_rules, merge_rules=merge_rules, datadicts=with_extra)
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


# @silk_profile(name='user_ldapactionbatch')
@staff_member_required
def user_rilec_save_view(request):
    # if request.method == 'PUT' or request.method == 'POST':
    # TODO fix CSRF vulnerability here
    userdata = MergedUserData.objects.prefetch_related('data', 'data__fields', 'data__dataset__source').all()
    batch = save_rilec(userdata)
    return redirect(reverse("apis_rilec:ldapobjectbatch_detail", kwargs={'pk': batch.pk}))


@staff_member_required
def save_ldap_view(request):
    # if request.method == 'PUT' or request.method == 'POST':
    # TODO fix base, filterstr to something that will actually work
    batch = save_ldap()
    return redirect(reverse("apis_rilec:ldapobjectbatch_detail", kwargs={'pk': batch.pk}))


@staff_member_required
def autogroup_ldapobjects_view(request, t=None):
    # if request.method == 'PUT' or request.method == 'POST':
    # TODO fix CSRF vulnerability here
    batch = autogroup_ldapobjects()
    return redirect(reverse("apis_rilec:ldapobjectbatch_detail", kwargs={'pk': batch.pk}))

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
    return render(request, 'apis_rilec/user_rules.html',
                  {'properties': properties, 'extra_fields': extra_fields, 'user_rules': user_rules})

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

@silk_profile(name='ldapobject_list')
@staff_member_required
def ldapobject_list(request):
    latest_objects = ldap_state(mark_changed=True)
    return render(request, 'apis_rilec/ldapobject_list.html', {'object_list': latest_objects})

@staff_member_required
def latest_ldapobject(request, pk):
    obj = get_object_or_404(LDAPObject, pk=pk) 
    return redirect(reverse("apis_rilec:ldapobject_detail", kwargs={"pk": obj.latest_id()}))

@staff_member_required
def ldapobject_detail(request, pk):
    return ldapobject_diff(request, pk)

@staff_member_required
def ldapobject_diff(request, pk, pk2=None):
    obj = get_object_or_404(LDAPObject, pk=pk)
    if pk2 is None:
        obj2 = obj.previous()
    else:
        obj2 = get_object_or_404(LDAPObject, pk=pk2)
    added, removed = obj.diff(obj2)
    added = added.order_by('field')
    removed = removed.order_by('field')
    return render(request, 'apis_rilec/ldapobject_diff.html',
                  {'object': obj, 'added': added, 'removed': removed})

@staff_member_required
def ldapobject_save(request, pk, source): 
    # TODO POST ONLY
    obj = get_object_or_404(LDAPObject, pk=pk)
    dn = obj.find_in_ldap()
    if dn is None:
        dn = obj.dn
    if source == 'ldap':
        save_ldap(ldap_conn=None, filterstr='(objectclass=*)', base=dn, scope=ldap.SCOPE_BASE)
    elif source == 'rilec':
        if obj.uid is None:
            raise Http404
        muds = MergedUserData.objects.filter(uid=obj.uid)
        if not muds.exists():
            raise Http404
        save_rilec(muds)
    else:
        save_ldap(ldap_conn=None, filterstr='(objectclass=*)', base=dn, scope=ldap.SCOPE_BASE)
    return redirect(reverse("apis_rilec:latest_ldapobject", kwargs={"pk": pk}))

@staff_member_required
def ldapobject_user_rilec_save(request, pk):
    # TODO POST ONLY
    return ldapobject_save(request, pk, 'rilec')

@staff_member_required
def ldapobject_to_ldap(request, pk): 
    # TODO POST ONLY
    obj = get_object_or_404(LDAPObject, pk=pk)
    merge_rules = get_rules('MERGE_RULES')
    keep_fields = _get_keep_fields(merge_rules)
    autogroups=get_groups(parents=False)
    applybatch = LDAPApplyBatch(name="object to ldap")
    applybatch.save()
    apply = obj.to_ldap(rename=True, keep_fields=keep_fields,
                clean_group_set=autogroups, simulate=False)
    apply.batch = applybatch
    apply.save()
    return redirect(reverse("apis_rilec:ldapapplybatch_detail", kwargs={"pk": applybatch.id}))

@staff_member_required
def ldapobject_diff_to_ldap(request, pk, pk2): 
    # TODO POST ONLY
    obj = get_object_or_404(LDAPObject, pk=pk)
    obj2 = get_object_or_404(LDAPObject, pk=pk2)
    merge_rules = get_rules('MERGE_RULES')
    keep_fields = _get_keep_fields(merge_rules)
    changed, removed = obj.diff(obj2)
    changed_fields = set(changed.values_list('field', flat=True))
    ignore_fields = set(obj.fields.values_list('field', flat=True)).difference(changed_fields)
    ignore_fields = set(DEFAULT_IGNORE_FIELDS).union(ignore_fields)
    autogroups=get_groups()
    applybatch = LDAPApplyBatch(name="object diff to ldap")
    applybatch.save()
    apply = obj.to_ldap(rename=True, keep_fields=keep_fields, ignore_fields=ignore_fields,
                clean_group_set=autogroups, simulate=False)
    apply.batch = applybatch
    apply.save()
    return redirect(reverse("apis_rilec:ldapapplybatch_detail", kwargs={"pk": applybatch.id}))

@silk_profile(name='ldapobjectbatch_list')
@staff_member_required
def ldapobjectbatch_list(request):
    objs = LDAPObjectBatch.objects.order_by('-timestamp')
    return render(request, 'apis_rilec/ldapobjectbatch_list.html', {'object_list': objs})

@staff_member_required
def ldapobjectbatch_detail(request, pk):
    obj = get_object_or_404(LDAPObjectBatch, pk=pk)
    older = LDAPObjectBatch.objects.filter(timestamp__lt=obj.timestamp).order_by('-timestamp')
    prev_rilec = older.filter(name__startswith='save_rilec').first()
    prev_ldap = older.filter(name__startswith='save_ldap').first()
    source = obj.name.split(" ", 1)[0]
    prev_same = older.filter(name__startswith=source).first()
    return render(request, 'apis_rilec/ldapobjectbatch_detail.html',
                  {'object': obj,
                   'prev_ldap': prev_ldap,
                   'prev_rilec': prev_rilec,
                   'prev_same': prev_same})

@silk_profile(name='ldapobjectbatch_diff')
@staff_member_required
def ldapobjectbatch_diff(request, pk, pk2):
    batch1 = get_object_or_404(LDAPObjectBatch, pk=pk)
    batch2 = get_object_or_404(LDAPObjectBatch, pk=pk2)
    objects1 = batch1.ldapobjects.all().prefetch_related('fields')
    objects2 = batch2.ldapobjects.order_by('dn').prefetch_related('fields')
    obj1_dict = dict()
    for obj1 in objects1:
        obj1_dict[obj1.dn] = obj1
    missing_objs = list()
    added_obj_dns = set(obj1_dict.keys())
    changed_objs = []
    unchanged_objs = []
    for obj2 in objects2:
        dn = obj2.dn
        obj1 = obj1_dict.get(dn, None)
        if obj1 is None:
            obj1 = obj2.siblings().filter(ldapobjectbatch=batch1)
            if obj1.exists():
                obj1 = obj1[0]
            else:
                obj1 = None
        if obj1 is not None:
            added_obj_dns.discard(obj1.dn)
            changed, removed = obj1.diff(obj2)
            changed_fields = set(changed.values_list('field', flat=True))
            unchanged_fields = set(obj1.fields.values_list('field', flat=True))
            unchanged_fields.difference_update(changed_fields)
            ignore_fields = set(DEFAULT_IGNORE_FIELDS)
            changed_fields.difference_update(ignore_fields)
            unchanged_fields.difference_update(ignore_fields)
            changed = obj1.fields.filter(field__in=changed_fields)
            unchanged = obj1.fields.filter(field__in=unchanged_fields)
            ignore = obj1.fields.filter(field__in=ignore_fields)
            if len(changed_fields) > 0:
                changed_objs.append({"obj": obj1, "obj2": obj2,
                                     "changed": changed,
                                     "unchanged": unchanged,
                                     "ignore": ignore})
            else:
                unchanged_objs.append({"obj": obj1, "obj2": obj2,
                                     "changed": changed,
                                     "unchanged": unchanged,
                                     "ignore": ignore})
        else:
            missing_objs.append(obj2)
    added_objs = []
    for dn in sorted(added_obj_dns):
        added_objs.append(obj1_dict[dn])
    return render(request, 'apis_rilec/ldapobjectbatch_diff.html',
                  {'added_objs': added_objs,
                   'changed_objs': changed_objs,
                   'unchanged_objs': unchanged_objs,
                   'missing_objs': missing_objs,
                   })

@staff_member_required
def ldapobjectbatch_to_ldap(request, pk):
    # TODO POST ONLY
    batch = get_object_or_404(LDAPObjectBatch, pk=pk)
    merge_rules = get_rules('MERGE_RULES')
    keep_fields = _get_keep_fields(merge_rules)
    autogroups = get_groups(parents=False)
    applybatch = LDAPApplyBatch(name="batch to ldap")
    applybatch.save()
    applies = list()
    for obj in batch.ldapobjects.all():
        applies.append(obj.to_ldap(rename=True, keep_fields=keep_fields,
                clean_group_set=autogroups, simulate=False))
    for a in applies:
        a.batch = applybatch
    LDAPApply.objects.bulk_create(applies)
    return redirect(reverse("apis_rilec:ldapapplybatch_detail", kwargs={"pk": applybatch.id}))

@staff_member_required
def ldapobjectbatch_diff_to_ldap(request, pk, pk2):
    # TODO POST ONLY
    obj1 = get_object_or_404(LDAPObjectBatch, pk=pk)
    obj2 = get_object_or_404(LDAPObjectBatch, pk=pk2)
    # TODO prepare object pairs
    # TODO write to ldap
    return redirect(reverse("apis_rilec:ldapapplybatch_detail", kwargs={"pk": pk}))

@silk_profile(name='ldapapplybatch_list')
@staff_member_required
def ldapapplybatch_list(request):
    objs = LDAPApplyBatch.objects.order_by('-timestamp')
    return render(request, 'apis_rilec/ldapapplybatch_list.html', {'object_list': objs})

@staff_member_required
def ldapapplybatch_detail(request, pk):
    obj = get_object_or_404(LDAPApplyBatch, pk=pk)
    return render(request, 'apis_rilec/ldapapplybatch_detail.html',
                  {'object': obj})

@staff_member_required
def ldapapply_detail(request, pk):
    obj = get_object_or_404(LDAPApply, pk=pk)
    return render(request, 'apis_rilec/ldapapply_detail.html',
                  {'object': obj})
