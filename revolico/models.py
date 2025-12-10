# models.py
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from .revolico import publish_ad  # Importa la función publish_ad desde tu archivo revolico.py

class PublishedAd(models.Model):
    ad_url = models.URLField()
    title = models.CharField(max_length=100)  # Título del anuncio
    publish_date = models.DateTimeField(auto_now_add=True)  # Fecha y hora de creación del anuncio
    duration = models.PositiveIntegerField(default=1)  # Duración del anuncio en días
    is_active = models.BooleanField(default=True)  # Campo de activación/desactivación del anuncio

    def __str__(self):
        return self.title

    def is_active_now(self):
        """Verifica si el anuncio está activo en este momento."""
        if not self.is_active:
            return False  # Si el anuncio está desactivado, retorna False

        # Calcula la fecha de desactivación sumando la duración en días a la fecha de creación
        expiration_date = self.publish_date + timezone.timedelta(days=self.duration)

        # Retorna True si la fecha de desactivación es posterior a la fecha y hora actual
        return expiration_date >= timezone.now()

@receiver(post_save, sender=PublishedAd)
def publish_ad_after_save(sender, instance, **kwargs):
    print("Hola desde la función mi_funcion")
    if kwargs['created']:
        instance.published = True
        instance.save()
        publish_ad(instance.ad_url)
