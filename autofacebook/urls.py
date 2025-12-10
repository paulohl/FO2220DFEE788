# miProyecto/urls.py

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from publicadorFacebook import views as publicador_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('publicar/', publicador_views.publicar_en_facebook, name='publicar'),
    path('revolico/', include('revolico.urls')),
]

# Esto es solo para desarrollo local (DEBUG = True)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
