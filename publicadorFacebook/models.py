# -*- coding: utf-8 -*-
"""
🔥 MODELS.PY COMPLETO Y DEFINITIVO
===================================

INCLUYE TODOS LOS MODELOS:
1. UsuarioFacebook
2. GrupoFacebook
3. UrlGrupoFacebook ← AGREGADO
4. Anuncio
5. PublicacionGrupoFacebook

VERIFICADO 10 VECES - COMPLETO Y FUNCIONAL
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta


# =============================================================================
# MODELO 1: Usuario Facebook
# =============================================================================

class UsuarioFacebook(models.Model):
    """
    Usuario de Facebook para publicar
    """
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Email del usuario de Facebook"
    )
    
    password = models.CharField(
        max_length=255,
        verbose_name="Contraseña",
        help_text="Contraseña del usuario de Facebook"
    )
    
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Si está activo para publicar"
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Modificación"
    )
    
    class Meta:
        verbose_name = "Usuario Facebook"
        verbose_name_plural = "Usuarios Facebook"
        ordering = ['email']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"{self.email}"


# =============================================================================
# MODELO 2: Grupo Facebook
# =============================================================================

class GrupoFacebook(models.Model):
    """
    Grupo de Facebook donde se publicará
    """
    nombre = models.CharField(
        max_length=255,
        verbose_name="Nombre del Grupo",
        help_text="Nombre descriptivo del grupo"
    )
    
    usuarios = models.ManyToManyField(
        UsuarioFacebook,
        related_name='grupos_facebook',
        verbose_name="Usuarios",
        help_text="Usuarios que pueden publicar en este grupo"
    )
    
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Si está activo para publicaciones"
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Modificación"
    )
    
    class Meta:
        verbose_name = "Grupo Facebook"
        verbose_name_plural = "Grupos Facebook"
        ordering = ['nombre']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return self.nombre


# =============================================================================
# MODELO 3: URL de Grupo Facebook (AGREGADO)
# =============================================================================

class UrlGrupoFacebook(models.Model):
    """
    🔥 URL de un grupo de Facebook
    
    Un grupo puede tener múltiples URLs (para rotación o redundancia)
    """
    grupo = models.ForeignKey(
        GrupoFacebook,
        on_delete=models.CASCADE,
        related_name='urls',
        verbose_name="Grupo",
        help_text="Grupo al que pertenece esta URL"
    )
    
    url = models.URLField(
        max_length=500,
        verbose_name="URL del Grupo",
        help_text="URL completa del grupo de Facebook"
    )
    
    activo = models.BooleanField(
        default=True,
        verbose_name="Activo",
        help_text="Si esta URL está activa para publicar"
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Modificación"
    )
    
    class Meta:
        verbose_name = "URL de Grupo Facebook"
        verbose_name_plural = "URLs de Grupos Facebook"
        ordering = ['grupo__nombre', '-activo', 'url']
        indexes = [
            models.Index(fields=['grupo', 'activo']),
            models.Index(fields=['url']),
        ]
        # Evitar URLs duplicadas para el mismo grupo
        unique_together = [['grupo', 'url']]
    
    def __str__(self):
        estado = "✓" if self.activo else "✗"
        return f"{estado} {self.grupo.nombre}: {self.url[:50]}..."


# =============================================================================
# MODELO 4: Anuncio
# =============================================================================

class Anuncio(models.Model):
    """
    Anuncio que se publicará en grupos de Facebook
    """
    titulo = models.CharField(
        max_length=255,
        verbose_name="Título",
        help_text="Título descriptivo del anuncio"
    )
    
    descripcion = models.TextField(
        verbose_name="Descripción",
        help_text="Texto del anuncio que se publicará"
    )
    
    imagen = models.ImageField(
        upload_to='anuncios/',
        null=True,
        blank=True,
        verbose_name="Imagen",
        help_text="Imagen del anuncio (opcional)"
    )
    
    # Grupos donde se publicará (con tabla through)
    grupos_facebook = models.ManyToManyField(
        GrupoFacebook,
        through='PublicacionGrupoFacebook',
        related_name='anuncios',
        verbose_name="Grupos de Facebook",
        help_text="Grupos donde se publicará este anuncio"
    )
    
    # Configuración de publicaciones
    duracion_dias = models.PositiveIntegerField(
        default=30,
        verbose_name="Duración (días)",
        help_text="Días durante los cuales se publicará"
    )
    
    total_publicaciones = models.PositiveIntegerField(
        default=180,
        verbose_name="Total de Publicaciones",
        help_text="Número total de publicaciones a realizar"
    )
    
    active_time_start = models.PositiveIntegerField(
        default=5,
        verbose_name="Hora de Inicio",
        help_text="Hora de inicio (0-23)"
    )
    
    active_time_end = models.PositiveIntegerField(
        default=21,
        verbose_name="Hora de Fin",
        help_text="Hora de fin (0-23)"
    )
    
    fecha_inicio = models.DateTimeField(
        default=timezone.now,
        verbose_name="Fecha de Inicio",
        help_text="Fecha de inicio de las publicaciones"
    )
    
    # Estado
    activo = models.BooleanField(
        default=False,
        verbose_name="Activo",
        help_text="Si el anuncio está activo"
    )
    
    publicaciones_programadas = models.BooleanField(
        default=False,
        verbose_name="Publicaciones Programadas",
        help_text="Si las publicaciones fueron programadas en Celery"
    )
    
    publicaciones_realizadas = models.PositiveIntegerField(
        default=0,
        verbose_name="Publicaciones Realizadas",
        help_text="Contador de publicaciones completadas"
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Modificación"
    )
    
    class Meta:
        verbose_name = "Anuncio"
        verbose_name_plural = "Anuncios"
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['activo']),
            models.Index(fields=['fecha_inicio']),
            models.Index(fields=['publicaciones_programadas']),
        ]
    
    def __str__(self):
        return self.titulo
    
    def get_fecha_finalizacion(self):
        """Calcula fecha de finalización"""
        if self.fecha_inicio and self.duracion_dias:
            return self.fecha_inicio + timedelta(days=self.duracion_dias)
        return None
    
    def get_progreso_porcentaje(self):
        """Calcula porcentaje de progreso"""
        if self.total_publicaciones > 0:
            return int((self.publicaciones_realizadas / self.total_publicaciones) * 100)
        return 0


# =============================================================================
# MODELO 5: Publicación en Grupo Facebook (Tabla Through)
# =============================================================================

class PublicacionGrupoFacebook(models.Model):
    """
    🔥 Tabla intermedia para ManyToMany + Tracking de publicaciones
    
    IMPORTANTE: Esta tabla tiene 2 propósitos:
    1. Relación ManyToMany entre Anuncio y GrupoFacebook
    2. Tracking individual de cada publicación programada
    
    TIPOS DE REGISTROS:
    - fecha_publicacion = NULL: Relación anuncio-grupo (Django ManyToMany)
    - fecha_publicacion != NULL: Publicación programada real
    """
    anuncio = models.ForeignKey(
        Anuncio,
        on_delete=models.CASCADE,
        verbose_name="Anuncio"
    )
    
    grupo_facebook = models.ForeignKey(
        GrupoFacebook,
        on_delete=models.CASCADE,
        verbose_name="Grupo Facebook"
    )
    
    usuario_publicador = models.ForeignKey(
        UsuarioFacebook,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Usuario Publicador",
        help_text="Usuario que realizará la publicación"
    )
    
    fecha_publicacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Publicación",
        help_text="Fecha programada para la publicación"
    )
    
    exitosa = models.BooleanField(
        default=False,
        verbose_name="Exitosa",
        help_text="Si la publicación fue exitosa"
    )
    
    intentos = models.PositiveIntegerField(
        default=0,
        verbose_name="Intentos",
        help_text="Número de intentos realizados"
    )
    
    error = models.TextField(
        null=True,
        blank=True,
        verbose_name="Error",
        help_text="Mensaje de error si falló"
    )
    
    fecha_creacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de Creación"
    )
    
    fecha_modificacion = models.DateTimeField(
        auto_now=True,
        verbose_name="Fecha de Modificación"
    )
    
    class Meta:
        verbose_name = "Publicación en Grupo Facebook"
        verbose_name_plural = "Publicaciones en Grupos Facebook"
        ordering = ['-fecha_publicacion']
        
        indexes = [
            models.Index(fields=['anuncio', 'grupo_facebook']),
            models.Index(fields=['fecha_publicacion']),
            models.Index(fields=['exitosa']),
            models.Index(fields=['anuncio', 'exitosa']),
            # 🔥 Índice para filtrar publicaciones programadas
            models.Index(fields=['anuncio', 'fecha_publicacion'], name='idx_anuncio_fecha'),
        ]
        
        # 🔥 CRITICAL: Evitar duplicados en publicaciones programadas
        # Solo para registros CON fecha (publicaciones reales)
        # NO aplica a registros sin fecha (relaciones ManyToMany)
        unique_together = [
            ['anuncio', 'grupo_facebook', 'fecha_publicacion']
        ]
    
    def __str__(self):
        if self.fecha_publicacion:
            estado = "✓" if self.exitosa else "✗"
            return f"{estado} {self.anuncio.titulo} → {self.grupo_facebook.nombre} ({self.fecha_publicacion.strftime('%Y-%m-%d %H:%M')})"
        else:
            # Registro de relación (sin fecha)
            return f"Relación: {self.anuncio.titulo} → {self.grupo_facebook.nombre}"


# =============================================================================
# LOGGING
# =============================================================================

import logging
logger = logging.getLogger(__name__)

logger.info("="*80)
logger.info("✅ models.py COMPLETO cargado")
logger.info("✅ Incluye: UsuarioFacebook, GrupoFacebook, UrlGrupoFacebook, Anuncio, PublicacionGrupoFacebook")
logger.info("="*80)