# admin.py
from django.contrib import admin
from django.contrib.admin.widgets import AdminDateWidget  # Asegúrate de importar el widget necesario
from django.db import models  # También asegúrate de importar el módulo models
from .models import PublishedAd

class PublishedAdAdmin(admin.ModelAdmin):
    # Lista de campos a mostrar en la vista de lista del administrador
    list_display = ('title', 'publish_date', 'duration', 'is_active')

    # Lista de campos a incluir en el formulario de creación y edición
    fields = ('title', 'ad_url', 'duration', 'is_active')

    # Configurar widgets para campos específicos
    formfield_overrides = {
        models.DateField: {'widget': AdminDateWidget},
    }

admin.site.register(PublishedAd, PublishedAdAdmin)
