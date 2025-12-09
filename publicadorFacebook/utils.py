from django.core.mail import send_mail
from django.conf import settings

def notificar_administradores(mensaje):
    send_mail(
        'Error en publicación de anuncio',
        mensaje,
        settings.DEFAULT_FROM_EMAIL,
        [admin[1] for admin in settings.ADMINS],
        fail_silently=False,
    )