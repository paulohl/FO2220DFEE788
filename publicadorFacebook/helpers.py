import asyncio
from .playwright_utils import iniciar_publicacion_en_grupo 

async def publicar_anuncio(usuario, contrasena, mensaje, grupo_url, imagen_ruta):
  await iniciar_publicacion_en_grupo(
    usuario, 
    contrasena, 
    mensaje, 
    grupo_url, 
    imagen_ruta
  )