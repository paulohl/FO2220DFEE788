from django.shortcuts import render
from .models import Anuncio
from .playwright_utils import iniciar_publicacion_en_grupo

def obtener_ruta_imagen_anuncio(anuncio_id):
    try:
        anuncio = Anuncio.objects.get(id=anuncio_id)
        return anuncio.imagen.path
    except Anuncio.DoesNotExist:
        return None

def publicar_en_facebook(request):
    if request.method == "POST":
        mensaje = request.POST.get("mensaje")
        anuncio_id = request.POST.get("anuncio_id")

        ruta_imagen = obtener_ruta_imagen_anuncio(anuncio_id)
        if ruta_imagen:
            try:
                anuncio = Anuncio.objects.get(id=anuncio_id)
                grupos_facebook = anuncio.grupos_facebook.all()
                
                for grupo in grupos_facebook:
                    usuario = grupo.usuario_principal  # Utiliza solo el usuario principal del grupo
                    if usuario and usuario.activo:
                        iniciar_publicacion_en_grupo(
                            anuncio_id,
                            usuario.facebook_user,
                            usuario.facebook_password,
                            mensaje,
                            [],  # Signatures should be handled in the task
                            grupo.urls.first().url if grupo.urls.exists() else None,  # Verifica si hay URLs activas
                            ruta_imagen,
                            [url.url for url in grupo.urls.all()]
                        )
                
                return render(request, 'publicadorFacebook/publicacion_exitosa.html', {'mensaje': mensaje})
            except Exception as e:
                return render(request, 'publicadorFacebook/error_publicacion.html', {'error': str(e)})
        else:
            return render(request, 'publicadorFacebook/error_publicacion.html', {'error': 'Imagen del anuncio no encontrada o anuncio inexistente'})

    else:
        return render(request, 'publicadorFacebook/formulario_publicacion.html')
