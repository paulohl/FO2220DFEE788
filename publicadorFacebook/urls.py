# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/<int:user_id>/', views.login_facebook_user, name='login_facebook_user'),
    path('update_password/<int:user_id>/', views.update_facebook_password, name='update_facebook_password'),
    path('insert_group/<int:user_id>/', views.insert_facebook_group, name='insert_facebook_group'),
    path('schedule_publications/<int:user_id>/', views.schedule_publications, name='schedule_publications'),
    path('publicar_en_grupo/<int:anuncio_id>/', views.publicar_en_grupo, name='publicar_en_grupo'),
    path('publicar/', views.publicar_en_facebook, name='publicar'),
]