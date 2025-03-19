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
from django.forms.models import model_to_dict

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework_api_key.permissions import HasAPIKey
from rest_framework.response import Response

import itertools
import logging
import ldap
from collections import defaultdict

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


@silk_profile(name='autogroup_ldapobjects')
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

@silk_profile(name='rule_list')
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

@silk_profile(name='translations')
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
    obj = get_object_or_404(LDAPObject, pk=pk)
    return render(request, 'apis_rilec/ldapobject_detail.html',
                  {'object': obj})

@staff_member_required
def ldapobject_diff(request, pk, pk2=None):
    obj = get_object_or_404(LDAPObject, pk=pk)
    if pk2 is None:
        obj2 = obj.previous()
    else:
        obj2 = get_object_or_404(LDAPObject, pk=pk2)
    added, removed, unchanged, ignored = obj.diff(obj2)
    added = added.order_by('field')
    removed = removed.order_by('field')
    return render(request, 'apis_rilec/ldapobject_diff.html',
                  {'object': obj, 'object2': obj2,
                   'added': added, 'removed': removed})

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

@silk_profile(name='ldapobject_diff_to_ldap')
@staff_member_required
def ldapobject_diff_to_ldap(request, pk, pk2): 
    # TODO POST ONLY
    obj = get_object_or_404(LDAPObject, pk=pk)
    obj2 = get_object_or_404(LDAPObject, pk=pk2)
    merge_rules = get_rules('MERGE_RULES')
    keep_fields = _get_keep_fields(merge_rules)
    changed, removed, unchanged, ignored = obj.diff(obj2)
    changed_fields = set(changed.values_list('field', flat=True))
    ignore_fields = set(obj.fields.values_list('field', flat=True)).difference(changed_fields)
    ignore_fields = set(DEFAULT_IGNORE_FIELDS).union(ignore_fields)
    autogroups=get_groups()
    applybatch = LDAPApplyBatch(name="object diff to ldap")
    applybatch.save()
    apply = obj.to_ldap(rename=False, keep_fields=keep_fields, ignore_fields=ignore_fields,
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
    def __to_utf(x):
        l = []
        for i in x:
            try:
                i = i.decode('utf-8')
            except:
                i = str(i)
            l.append(i)
        return l
    batch1 = get_object_or_404(LDAPObjectBatch, pk=pk)
    batch2 = get_object_or_404(LDAPObjectBatch, pk=pk2)
    objects1 = batch1.ldapobjects.all().prefetch_related('fields')
    objects2 = batch2.ldapobjects.order_by('dn').prefetch_related('fields')
    obj1_dicts = {}
    # prepare dict for object matching later
    id_dict_list = ("dn", "objectSid", "upn", "uid")
    for key in id_dict_list:
        obj1_dicts[key] = dict()
    for obj1 in objects1:
        d = model_to_dict(obj1, fields=id_dict_list)
        for key in id_dict_list:
            val = d.get(key, None)
            if val is not None:
                val = val.upper()
            obj1_dicts[key][val] = obj1
    for key in id_dict_list:
        obj1_dicts[key].pop(None, None)
    allowed_values = {}
    for i in DEFAULT_IGNORE_FIELDS:
        allowed_values[i] = None
    # TODO handle allowed values for memberof based on autogroups
    allowed_values.pop('MEMBEROF')
    missing_objs = list()
    added_obj_dns = set(obj1_dicts["dn"].keys())
    changed_objs = []
    unchanged_objs = []
    for obj2 in objects2:
        # find best matching obj1
        obj2_dict = model_to_dict(obj2, fields=id_dict_list)
        for key in id_dict_list:
            val = obj2_dict.get(key, None)
            if val is not None:
                val = val.upper()
            obj1 = obj1_dicts[key].get(val, None)
            if obj1 is not None:
                break
        if obj1 is not None:
            added_obj_dns.discard(obj1.dn.upper())
            # group diffs by field
            d_groupped = []
            for i in obj1.diff(obj2, allowed_values):
                l = []
                for k, v in itertools.groupby(i, lambda x: x.field):
                    l.append((k, list(v)))
                d_groupped.append(l)
            # groupping done
            in_this, in_other, in_both, ignored = d_groupped
            keys_in_this = set(k for (k, v) in in_this)
            keys_in_this = keys_in_this.union(set(k for (k, v) in in_both))
            changed_in_other = []
            only_in_other = []
            for (k, v) in in_other:
                if k in keys_in_this:
                    changed_in_other.append((k, v))
                else:
                    only_in_other.append((k, v))
            if len(in_this) > 0 or len(changed_in_other) > 0:
                changed_objs.append({"obj": obj1, "obj2": obj2,
                                     "in_this": in_this,
                                     "changed_in_other": changed_in_other,
                                     "only_in_other": only_in_other,
                                     "in_both": in_both,
                                     "ignored": ignored})
            else:
                unchanged_objs.append({"obj": obj1, "obj2": obj2,
                                     "in_this": [],
                                     "changed_in_other": changed_in_other,
                                     "only_in_other": only_in_other,
                                     "unchanged": in_both,
                                     "ignored": ignored})
        else:
            missing_objs.append(obj2)
    added_objs = []
    for dn in sorted(added_obj_dns):
        added_objs.append(obj1_dicts["dn"][dn])
    return render(request, 'apis_rilec/ldapobjectbatch_diff.html',
                  {'add_batches': [batch1.id], 'rm_batches': [batch2.id],
                   'added_objs': added_objs,
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
def ldapobjectbatch_latest_diff(request):
    batches = LDAPObjectBatch.objects.order_by('-timestamp')
    latest_rilec = batches.filter(name__startswith='save_rilec').first()
    latest_ldap = batches.filter(name__startswith='save_ldap').first()
    if latest_ldap is None:
        latest_ldap = save_ldap()
    if latest_rilec is None:
        userdata = MergedUserData.objects.prefetch_related('data', 'data__fields', 'data__dataset__source').all()
        latest_rilec = save_rilec(userdata)
    pk, pk2 = latest_rilec.id, latest_ldap.id
    return redirect(reverse("apis_rilec:ldapobjectbatch_diff", kwargs={"pk": pk, "pk2": pk2}))


@staff_member_required
def ldapobjectbatch_fields_to_ldap(request):
    if request.method != "POST":
        return redirect(reverse("apis_rilec:ldapobjectbatch_list"))
    simulate = False
    applybatch = LDAPApplyBatch(name="fields to ldap")
    applybatch.save()
    applies = list()
    if not simulate:
        ldap_conn = try_init_ldap(ldap_conn=None)
    else:
        ldap_conn = None
    addobj_ids = request.POST.getlist("objadd", [])
    for obj in LDAPObject.objects.filter(id__in = addobj_ids).prefetch_related("fields"):
        applies.append(obj.to_ldap(
            ldap_conn=ldap_conn,
            rename=False, simulate=simulate))
    rmobj_ids = request.POST.getlist("objrm", [])
    for obj in LDAPObject.objects.filter(id__in = rmobj_ids):
        dn = obj.dn
        try:
            if simulate:
                messages += f"ACT: delete {dn}\n"
            else:
                messages += f"DELETE: {dn}\n"
                ldap_conn.delete(dn)
            messages += "  SUCCESS\n"
        except Exception as e:
            error = True
            messages += f"Failed to rm {dn}\n"
        applies.append(LDAPApply(obj, obj.dn, message))
    for (postfield, ldap_op) in [("frm", ldap.MOD_DELETE), ("fadd", ldap.MOD_ADD)]:
        mod_fields = defaultdict(set)
        for objfield in request.POST.getlist(postfield, []):
            try:
                obj_id, field_id = objfield.split("_")
                mod_fields[int(obj_id)].add(int(field_id))
            except:
                pass
        for obj in LDAPObject.objects.filter(
                id__in = mod_fields.keys()).prefetch_related("fields"):
            real_dn = obj.find_in_ldap(ldap_conn)
            # real_dn = obj.dn
            op_dict = defaultdict(list)
            for f in obj.fields.all():
                if f.id in mod_fields[obj.id]:
                    if f.field == 'MEMBEROF':
                        op_dict[f.value].append((ldap_op, 'member', [real_dn]))
                    else:
                        op_dict[real_dn].append((ldap_op, f.field, [f.value]))
            messages = ""
            error = False
            for dn, op_list in op_dict.items():
                for op in op_list:
                    try:
                        if simulate:
                            messages += f"ACT: {dn}: {op}\n"
                        else:
                            messages += f"MODIFY: {dn}: {op}\n"
                            ldap_conn.modify_s(dn, [op])
                            messages += "  SUCCESS\n"
                    except Exception as e:
                        error = True
                        messages += "Failed to write {}: {}: {}\n".format(dn, op[1], e)
            applies.append(LDAPApply(ldapobject=obj, messages=messages, error=error))
    for a in applies:
        a.batch = applybatch
    LDAPApply.objects.bulk_create(applies)
    return redirect(reverse("apis_rilec:ldapapplybatch_detail", kwargs={"pk": applybatch.id}))


@silk_profile(name='ldapapplybatch_list')
@staff_member_required
def ldapapplybatch_list(request):
    objs = LDAPApplyBatch.objects.order_by('-timestamp')
    return render(request, 'apis_rilec/ldapapplybatch_list.html', {'object_list': objs})

@silk_profile(name='ldapapplybatch_detail')
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
