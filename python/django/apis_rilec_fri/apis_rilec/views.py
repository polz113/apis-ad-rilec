from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from itertools import chain

import logging

from .models import DataSource

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
        

def userprofile_list(request, date_str):
    return render(request, 'apis_rilec/userprofile_list.html')

def userproperty_list(request):
    return render(request, 'apis_rilec/userproperty_list.html')

def userprofile_detail(request, date_str, user_id):
    return render(request, 'apis_rilec/userprofile_detail.html')
