# -*- coding: utf-8 -*-
"""
🔥 ADMIN.PY DEFINITIVO (V15 - LIMPIEZA Y ALINEACIÓN TOTAL)
==========================================================

CAMBIOS VISUALES:
- 🧹 Limpieza: Ocultados (comentados) 'Estado' y 'Usuario Publicador'.
- 📏 Alineación: CSS ajustado para centrar verticalmente los elementos restantes.
- 🛡️ Robustez: Configuración verificada de autocomplete y filtros.
"""

from django.contrib import admin
from django.forms import ModelForm, PasswordInput
from django.utils import timezone
from django.contrib import messages
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from datetime import timedelta

# Importamos tus modelos
from .models import (
    Anuncio, 
    GrupoFacebook, 
    PublicacionGrupoFacebook, 
    UrlGrupoFacebook, 
    UsuarioFacebook
)

# =============================================================================
# 1. INLINES
# =============================================================================

class UrlGrupoFacebookInline(admin.TabularInline):
    model = UrlGrupoFacebook
    extra = 0
    fields = ('url', 'activo')
    classes = ('collapse', 'show')


class PublicacionGrupoFacebookInline(admin.TabularInline):
    model = PublicacionGrupoFacebook
    
    extra = 0           # No mostrar filas vacías
    can_delete = True   # 🔥 Permitir eliminar (las publicaciones las gestiona Celery)
    max_num = 0         # 🔥 No permitir agregar nuevos (previene duplicados)
    
    autocomplete_fields = ['grupo_facebook']
    ordering = ('-fecha_publicacion',)
    
    fields = (
        'grupo_facebook',
        # 'status_visual',      # 👁️ COMENTADO PARA FUTURO USO
        # 'usuario_publicador', # 👁️ COMENTADO PARA FUTURO USO
        'intentos',
        'error_visual',
        'estilo_css' # Inyección de estilos
    )
    
    readonly_fields = (
        'fecha_publicacion', 
        # 'status_visual',      # 👁️ COMENTADO
        # 'usuario_publicador', # 👁️ COMENTADO
        'intentos',
        'error_visual',
        'estilo_css'
    )
    
    # 🔥 CSS DE ALINEACIÓN "PIXEL PERFECT"
    def estilo_css(self, obj):
        return mark_safe('''
            <style>
                /* 1. Ocultar texto de relación */
                .inline-group .tabular tr.has_original td.original p { display: none !important; }
                .inline-group .tabular tr.has_original td.original { padding: 0 !important; width: 0 !important; }
                
                /* 2. Alineación Vertical y Espaciado */
                .inline-group .tabular td { 
                    vertical-align: middle !important; 
                    padding-top: 8px !important; 
                    padding-bottom: 8px !important;
                }
                
                /* 3. Ajuste del selector de Grupos para que se vea limpio */
                .related-widget-wrapper {
                    display: flex !important;
                    align-items: center !important;
                    margin: 0 !important;
                }
                
                /* 4. Centrar columnas numéricas y de error */
                .field-intentos { text-align: center !important; width: 100px; }
                .field-error_visual { text-align: left !important; }
                
                /* 5. Ajuste de la columna de eliminación */
                .inline-group .tabular td.delete {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding-top: 12px !important;
                }
            </style>
        ''')
    estilo_css.short_description = "" 
    
    # --- MÉTODOS DE VISUALIZACIÓN (Se mantienen por si descomentas) ---
    
    def status_visual(self, obj):
        if obj.exitosa:
            return format_html('<span style="color: white; background: #28a745; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">EXITOSA</span>')
        elif obj.intentos > 0:
            return format_html('<span style="color: white; background: #dc3545; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">FALLIDA</span>')
        elif obj.fecha_publicacion:
            return format_html('<span style="color: #666; background: #e9ecef; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">PROGRAMADA</span>')
        else:
            return format_html('<span style="color: #007bff; background: #e7f1ff; padding: 3px 8px; border-radius: 10px; font-size: 10px; font-weight: bold;">CONFIGURADO</span>')
    status_visual.short_description = "Estado"

    def error_visual(self, obj):
        if obj.error:
            return format_html(
                '<div style="color: #dc3545; font-size: 12px; line-height: 1.2;">{}</div>',
                obj.error
            )
        return '-'
    error_visual.short_description = "Error"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ocultamos lo programado a futuro para limpiar la vista
        return qs.exclude(
            fecha_publicacion__isnull=False, 
            intentos=0,                      
            exitosa=False                    
        )


# =============================================================================
# 2. USUARIO FACEBOOK
# =============================================================================

class UsuarioFacebookForm(ModelForm):
    class Meta:
        model = UsuarioFacebook
        fields = ['email', 'password', 'activo']
        widgets = {
            'password': PasswordInput(render_value=True),
        }

@admin.register(UsuarioFacebook)
class UsuarioFacebookAdmin(admin.ModelAdmin):
    form = UsuarioFacebookForm
    list_display = ('email', 'password_oculto', 'activo', 'grupos_count')
    list_filter = ('activo',)
    search_fields = ('email',)
    ordering = ('email',) 

    def password_oculto(self, obj):
        if obj.password: return '••••••••'
        return '-'
    password_oculto.short_description = 'Contraseña'
    
    def grupos_count(self, obj):
        count = obj.grupos_facebook.count()
        color = '#28a745' if count > 0 else '#6c757d'
        return format_html('<strong style="color: {};">{}</strong>', color, count)
    grupos_count.short_description = 'Grupos'


# =============================================================================
# 3. GRUPO FACEBOOK
# =============================================================================

@admin.register(GrupoFacebook)
class GrupoFacebookAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'status_icon', 'usuarios_badge', 'urls_badge')
    list_filter = ('activo',)
    search_fields = ('nombre',) # 🔥 Requerido para el autocomplete del Inline
    inlines = [UrlGrupoFacebookInline]
    autocomplete_fields = ['usuarios']
    
    fieldsets = (
        ('🏢 Información del Grupo', {
            'fields': ('nombre', 'activo'),
            'description': 'Configuración básica del grupo destino.'
        }),
        ('👥 Gestión de Miembros', {
            'fields': ('usuarios',),
            'description': 'Seleccione los usuarios que tendrán permiso para publicar en este grupo.'
        }),
    )

    def status_icon(self, obj):
        if obj.activo:
            return format_html('<span style="color: #28a745; font-size: 16px;">●</span> Activo')
        return format_html('<span style="color: #dc3545; font-size: 16px;">●</span> Inactivo')
    status_icon.short_description = "Estado"

    def usuarios_badge(self, obj):
        count = obj.usuarios.count()
        bg_color = '#17a2b8' if count > 0 else '#6c757d'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: bold;">{}</span>',
            bg_color, count
        )
    usuarios_badge.short_description = 'Usuarios Asignados'
    
    def urls_badge(self, obj):
        count = obj.urls.filter(activo=True).count()
        bg_color = '#28a745' if count > 0 else '#dc3545'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; font-weight: bold;">{}</span>',
            bg_color, count
        )
    urls_badge.short_description = 'URLs Activas'


# =============================================================================
# 4. ANUNCIO
# =============================================================================

@admin.register(Anuncio)
class AnuncioAdmin(admin.ModelAdmin):
    list_display = (
        'titulo', 
        'status_icon',
        'barra_progreso', 
        'fecha_inicio_fmt',
        'fecha_fin_fmt',
        'total_publicaciones'
    )
    
    list_filter = ('activo', 'publicaciones_programadas', 'fecha_inicio')
    search_fields = ('titulo', 'descripcion')
    inlines = [PublicacionGrupoFacebookInline]
    actions = ['activar_anuncios', 'desactivar_anuncios', 'generar_reporte']
    
    fieldsets = (
        ('📢 Contenido', {
            'fields': ('titulo', 'descripcion', 'imagen', 'activo')
        }),
        ('⏱️ Programación y Metas', {
            'fields': (
                'fecha_inicio', 
                'duracion_dias', 
                'total_publicaciones', 
                'active_time_start', 
                'active_time_end'
            ),
            'description': 'Define cuándo, cuánto y con qué frecuencia se publicará.'
        }),
        ('📊 Progreso de Ejecución', { 
            'fields': (
                'publicaciones_realizadas',
                'publicaciones_programadas'
            ),
            'description': 'Monitoreo del estado actual de la campaña.'
        }),
    )
    
    readonly_fields = ('publicaciones_realizadas', 'publicaciones_programadas')

    # --- MÉTODOS VISUALES ---
    def status_icon(self, obj):
        if obj.activo:
            return format_html(
                '''
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle;">
                    <circle cx="12" cy="12" r="10" fill="#44b700" />
                    <path d="M8 12L11 15L16 9" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                '''
            )
        else:
            return format_html(
                '''
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style="vertical-align: middle; opacity: 0.5;">
                    <circle cx="12" cy="12" r="10" fill="#dc3545" />
                    <path d="M8 8L16 16M16 8L8 16" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                '''
            )
    status_icon.short_description = "Activo"
    status_icon.admin_order_field = 'activo'

    def fecha_inicio_fmt(self, obj):
        if obj.fecha_inicio:
            return obj.fecha_inicio.strftime('%d/%m/%Y %H:%M')
        return '-'
    fecha_inicio_fmt.short_description = "Fecha Inicio"
    fecha_inicio_fmt.admin_order_field = 'fecha_inicio'

    def fecha_fin_fmt(self, obj):
        if obj.fecha_inicio and obj.duracion_dias:
            fin = obj.fecha_inicio + timedelta(days=obj.duracion_dias)
            estilo = "color: #dc3545; font-weight: bold;" if fin < timezone.now() else ""
            return format_html('<span style="{}">{}</span>', estilo, fin.strftime('%d/%m/%Y %H:%M'))
        return '-'
    fecha_fin_fmt.short_description = "Fecha Fin"

    def barra_progreso(self, obj):
        total = obj.total_publicaciones
        realizadas = obj.publicaciones_realizadas
        porcentaje = min(100, int((realizadas / total) * 100)) if total > 0 else 0
        
        color = '#007bff' 
        if porcentaje > 50: color = '#ffc107'
        if porcentaje >= 90: color = '#28a745'
        
        return format_html(
            '''
            <div style="width: 120px; background-color: #e9ecef; border-radius: 4px; height: 18px; position: relative;">
                <div style="width: {}%; background-color: {}; height: 100%; border-radius: 4px; transition: width 0.5s;"></div>
                <div style="position: absolute; top: 0; width: 100%; text-align: center; font-size: 10px; line-height: 18px; color: #333; font-weight: bold;">
                    {}% ({}/{})
                </div>
            </div>
            ''',
            porcentaje, color, porcentaje, realizadas, total
        )
    barra_progreso.short_description = "Progreso"

    # --- LÓGICA ---
    def save_model(self, request, obj, form, change):
        reprogramar = False
        if change:
            try:
                old_obj = Anuncio.objects.get(pk=obj.pk)
                if not old_obj.activo and obj.activo:
                    reprogramar = True
            except Anuncio.DoesNotExist: pass
        else:
            if obj.activo: reprogramar = True

        if reprogramar:
            obj.publicaciones_realizadas = 0
            obj.publicaciones_programadas = False
            messages.success(request, f"🚀 Anuncio '{obj.titulo}' activado.")
        
        super().save_model(request, obj, form, change)

    def activar_anuncios(self, request, queryset):
        count = queryset.update(activo=True, publicaciones_programadas=False)
        for anuncio in queryset: anuncio.save()
        self.message_user(request, f"✅ {count} anuncios activados.")
    activar_anuncios.short_description = "▶️ Activar"

    def desactivar_anuncios(self, request, queryset):
        count = queryset.update(activo=False)
        self.message_user(request, f"⏸️ {count} anuncios pausados.", messages.WARNING)
    desactivar_anuncios.short_description = "⏸️ Pausar"
    
    def generar_reporte(self, request, queryset):
        if queryset.count() > 1:
            self.message_user(request, "⚠️ Selecciona solo un anuncio", messages.WARNING)
            return
        anuncio = queryset.first()
        pubs = PublicacionGrupoFacebook.objects.filter(anuncio=anuncio)
        exitosas = pubs.filter(exitosa=True).count()
        fallidas = pubs.filter(exitosa=False, intentos__gt=0).count()
        self.message_user(request, f"📊 Reporte: {exitosas} Exitosas | {fallidas} Fallidas", messages.INFO)
    generar_reporte.short_description = "📊 Generar Reporte"


# =============================================================================
# CONFIGURACIÓN GENERAL
# =============================================================================
admin.site.site_header = "🤖 Facebook Auto-Poster"
admin.site.site_title = "Admin Panel"
admin.site.index_title = "Panel de Control"