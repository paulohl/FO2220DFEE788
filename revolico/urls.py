# revolico/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.publish_ad_view, name='publish_ad'),
    # Otras URLs de tu aplicación
]
