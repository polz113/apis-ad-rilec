from django.shortcuts import render
from django.http import HttpResponse, JsonResponse, StreamingHttpResponse
from django.utils import timezone
from itertools import chain
# Create your views here
from .models import DataSource

def index(request):
    return render(request, 'apis_rilec/index.html')

def hrmaster_replicate(request):
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
        

def userprofile_list(request, date_str):
    return render(request, 'apis_rilec/userprofile_list.html')


def userprofile_detail(request, date_str, user_id):
    return render(request, 'apis_rilec/userprofile_detail.html')
