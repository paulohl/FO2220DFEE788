# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import asyncio
from .models import PublishedAd  # Importamos el modelo necesario
from .tasks import publish_ad


@csrf_exempt
def publish_ad_view(request):
    if request.method == 'POST':
        ad_url = request.POST.get('ad_url')
        process = publish_ad.apply_async(args=[ad_url])
        return JsonResponse({'message': 'Anuncio publicado correctamente', 'queue': process.task_id})

    return JsonResponse({'error': 'Este endpoint solo acepta solicitudes POST'}, status=400)
