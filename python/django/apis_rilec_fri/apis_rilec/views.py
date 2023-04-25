from django.shortcuts import render, get_object_or_404
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from itertools import chain
from django.contrib.admin.views.decorators import staff_member_required
import logging

from .models import DataSource, MergedUserData, LDAPActionBatch, LDAPAction, UserDataField, get_rules

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
def mergeduserdata_list(request, date_str):
    mudl = MergedUserData.objects.all()
    return render(request, 'apis_rilec/mergeduserdata_list.html', {'object_list': mudl})

@staff_member_required
def mergeduserdata_detail(request, date_str, user_id):
    mud = get_object_or_404(MergedUserData, uid=user_id)
    return render(request, 'apis_rilec/mergeduserdata_detail.html', {'object': mud})

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
    return render(request, 'apis_rilec/user_rules.html', {'extra_fields': extra_fields, 'user_rules': user_rules})

@staff_member_required
def generic_rule_detail(request, rules_part):
    props = get_rules(rules_part)
    return render(request, 'apis_rilec/generic_rule_detail.html', {'object_list': props})

@staff_member_required
def ldapactionbatch_list(request):
    mudl = LDAPActionBatch.objects.all()
    return render(request, 'apis_rilec/ldapactionbatch_list.html')

@staff_member_required
def ldapactionbatch_detail(request, batch_id):
    batch = get_object_or_404(LDAPActionBatch, pk=batch_id)
    return render(request, 'apis_rilec/ldapactionbatch_detail.html')

