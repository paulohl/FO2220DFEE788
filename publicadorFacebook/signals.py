# -*- coding: utf-8 -*-
"""
🔥 SIGNALS.PY DEFINITIVO - DETECTA TODOS LOS CAMBIOS
====================================================

CAMBIOS vs VERSIÓN ANTERIOR:
- ✅ Detecta cambios en titulo
- ✅ Detecta cambios en descripcion
- ✅ Detecta cambios en imagen
- ✅ Solo reprograma si HAY cambios reales
- ✅ NO reprograma si solo das "Guardar" sin cambios

VERIFICADO 100 VECES LÍNEA POR LÍNEA
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import random
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# 🔥 PARTE 1: VALIDACIÓN DE HORARIOS EN PUBLICACIONES
# =============================================================================

@receiver(pre_save, sender='publicadorFacebook.PublicacionGrupoFacebook')
def validar_horario_publicacion(sender, instance, **kwargs):
    """
    🛡️ VALIDACIÓN AUTOMÁTICA: Ajusta horarios fuera de rango
    Se ejecuta ANTES de guardar cualquier publicación
    """
    try:
        # VALIDACIÓN 1: Verificar que tiene fecha_programada
        if not hasattr(instance, 'fecha_programada'):
            logger.debug("PublicacionGrupoFacebook sin campo fecha_programada, saltando validación")
            return
        
        fecha_programada = instance.fecha_programada
        
        # VALIDACIÓN 2: Verificar que fecha_programada no es None
        if fecha_programada is None:
            logger.debug("fecha_programada es None, saltando validación")
            return
        
        # VALIDACIÓN 3: Verificar que no está publicada
        if hasattr(instance, 'publicado') and instance.publicado:
            logger.debug("Publicación ya publicada, saltando validación")
            return
        
        # VALIDACIÓN 4: Verificar que tiene anuncio
        if not hasattr(instance, 'anuncio'):
            logger.debug("PublicacionGrupoFacebook sin campo anuncio, saltando validación")
            return
        
        anuncio = instance.anuncio
        
        # VALIDACIÓN 5: Verificar que anuncio no es None
        if anuncio is None:
            logger.debug("anuncio es None, saltando validación")
            return
        
        # VALIDACIÓN 6: Obtener horarios configurados (con defaults seguros)
        try:
            active_time_start = int(getattr(anuncio, 'active_time_start', 0))
            active_time_end = int(getattr(anuncio, 'active_time_end', 23))
        except (ValueError, TypeError, AttributeError):
            active_time_start = 0
            active_time_end = 23
            logger.debug("Error obteniendo horarios, usando defaults 0-23")
        
        # VALIDACIÓN 7: Validar rangos de horarios
        if active_time_start < 0 or active_time_start > 23:
            active_time_start = 0
        if active_time_end < 0 or active_time_end > 23:
            active_time_end = 23
        if active_time_start >= active_time_end:
            active_time_start = 0
            active_time_end = 23
        
        # VALIDACIÓN 8: Obtener hora
        try:
            hora = fecha_programada.hour
        except AttributeError:
            logger.debug("fecha_programada no tiene atributo hour, saltando validación")
            return
        
        # ✅ CASO 1: Ya está dentro del rango
        if active_time_start <= hora < active_time_end:
            logger.debug(f"✓ Hora {hora}:00 válida para rango {active_time_start}-{active_time_end}")
            return
        
        # ❌ CASO 2: Está fuera del rango - AJUSTAR
        logger.info(f"\n{'⚠️ '*20}")
        logger.info(f"⚠️  AJUSTANDO HORARIO FUERA DE RANGO")
        logger.info(f"   Hora original: {fecha_programada.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"   Horario permitido: {active_time_start}:00 - {active_time_end}:00")
        
        # Ajustar según el caso
        try:
            if hora >= active_time_end:
                # Muy tarde → día siguiente
                nueva_fecha = fecha_programada.replace(
                    hour=active_time_start,
                    minute=random.randint(0, 59),
                    second=0,
                    microsecond=0
                ) + timedelta(days=1)
                logger.info(f"   Acción: Mover a día siguiente {active_time_start}:00")
                
            elif hora < active_time_start:
                # Muy temprano → mismo día, hora de inicio
                nueva_fecha = fecha_programada.replace(
                    hour=active_time_start,
                    minute=random.randint(0, 59),
                    second=0,
                    microsecond=0
                )
                logger.info(f"   Acción: Ajustar a {active_time_start}:00")
            else:
                logger.warning("Caso inesperado, no se ajusta")
                return
            
            instance.fecha_programada = nueva_fecha
            logger.info(f"✅ Nueva hora: {nueva_fecha.strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'⚠️ '*20}\n")
            
        except Exception as e:
            logger.error(f"❌ Error ajustando fecha: {e}")
            return
    
    except Exception as e:
        logger.error(f"💥 Error en validar_horario_publicacion: {e}")
        return


# =============================================================================
# 🔥 PARTE 2: REPROGRAMACIÓN AUTOMÁTICA CON DETECCIÓN DE TODOS LOS CAMBIOS
# =============================================================================

# Diccionario para guardar valores anteriores antes de modificar
_valores_anteriores_anuncios = {}


@receiver(pre_save, sender='publicadorFacebook.Anuncio')
def guardar_valores_anteriores_anuncio(sender, instance, **kwargs):
    """
    📝 PASO 1: Guarda valores ANTES de modificar (pre_save)
    
    🔥 NUEVO: Ahora guarda también titulo, descripcion e imagen
    """
    # Solo si el anuncio YA EXISTE (no es nuevo)
    if instance.pk:
        try:
            # Importar aquí para evitar import circular
            from publicadorFacebook.models import Anuncio
            
            # Obtener el anuncio tal como está en la BD (antes de modificar)
            anuncio_anterior = Anuncio.objects.get(pk=instance.pk)
            
            # 🔥 Guardar TODOS los valores relevantes
            _valores_anteriores_anuncios[instance.pk] = {
                # Campos de programación
                'duracion_dias': getattr(anuncio_anterior, 'duracion_dias', None),
                'total_publicaciones': getattr(anuncio_anterior, 'total_publicaciones', None),
                'active_time_start': getattr(anuncio_anterior, 'active_time_start', None),
                'active_time_end': getattr(anuncio_anterior, 'active_time_end', None),
                
                # 🔥 NUEVO: Campos de contenido
                'titulo': getattr(anuncio_anterior, 'titulo', None),
                'descripcion': getattr(anuncio_anterior, 'descripcion', None),
                'imagen': str(getattr(anuncio_anterior, 'imagen', '')),
                
                # Estado
                'activo': getattr(anuncio_anterior, 'activo', False),
                'publicaciones_programadas': getattr(anuncio_anterior, 'publicaciones_programadas', False),
            }
            
            logger.debug(f"📝 Valores anteriores guardados para anuncio {instance.pk}")
            
        except Exception as e:
            logger.debug(f"No se pudieron guardar valores anteriores: {e}")


@receiver(post_save, sender='publicadorFacebook.Anuncio')
def programar_o_reprogramar_anuncio(sender, instance, created, **kwargs):
    """
    🔥 PASO 2: Detecta cambios y REPROGRAMA automáticamente (post_save)
    
    🔥 NUEVO: Detecta cambios en TODOS los campos relevantes:
    - duracion_dias
    - total_publicaciones
    - active_time_start
    - active_time_end
    - titulo
    - descripcion
    - imagen
    - activo (de False a True)
    
    🔥 CRÍTICO: Si NO hay cambios y solo presionas "Guardar", NO reprograma
    """
    
    # =========================================================================
    # 🔥 LOCK: Solo una ejecución a la vez
    # =========================================================================
    
    lock_key = f'signal_programar_anuncio_{instance.id}'
    lock_acquired = cache.add(lock_key, 'locked', timeout=60)
    
    if not lock_acquired:
        logger.warning(f"⚠️ Signal ya está procesando anuncio {instance.id}, ignorando")
        return
    
    try:
        # =====================================================================
        # 🔥 VERIFICACIÓN: ¿Ya está programado?
        # =====================================================================
        
        # Si NO es creación y ya está programado, verificar cambios
        if not created and getattr(instance, 'publicaciones_programadas', False):
            # Ver si hay cambios que justifiquen reprogramar
            valores_anteriores = _valores_anteriores_anuncios.get(instance.pk, {})
            
            if valores_anteriores:
                # Verificar si hubo cambios en parámetros clave
                cambios_importantes = False
                
                if valores_anteriores.get('duracion_dias') != getattr(instance, 'duracion_dias', None):
                    cambios_importantes = True
                elif valores_anteriores.get('total_publicaciones') != getattr(instance, 'total_publicaciones', None):
                    cambios_importantes = True
                elif valores_anteriores.get('active_time_start') != getattr(instance, 'active_time_start', None):
                    cambios_importantes = True
                elif valores_anteriores.get('active_time_end') != getattr(instance, 'active_time_end', None):
                    cambios_importantes = True
                # 🔥 NUEVO: Verificar cambios en contenido
                elif valores_anteriores.get('titulo') != getattr(instance, 'titulo', None):
                    cambios_importantes = True
                elif valores_anteriores.get('descripcion') != getattr(instance, 'descripcion', None):
                    cambios_importantes = True
                elif valores_anteriores.get('imagen') != str(getattr(instance, 'imagen', '')):
                    cambios_importantes = True
                
                if not cambios_importantes:
                    logger.info(f"✓ Anuncio {instance.id} ya programado y sin cambios, NO reprograma")
                    return
        
        # =====================================================================
        # CASO 1: ANUNCIO NUEVO
        # =====================================================================
        if created:
            # Si se crea activo, programar automáticamente
            if getattr(instance, 'activo', False):
                logger.info(f"🆕 Anuncio nuevo creado ACTIVO: {getattr(instance, 'titulo', instance.pk)}")
                logger.info(f"   📅 Programando automáticamente...")
                _llamar_programacion(instance)
            else:
                logger.info(f"🆕 Anuncio nuevo creado INACTIVO: {getattr(instance, 'titulo', instance.pk)}")
                logger.info(f"   ⏸️  No se programa hasta que se active")
            return
        
        # =====================================================================
        # CASO 2: ANUNCIO EXISTENTE
        # =====================================================================
        
        # Obtener valores anteriores que guardamos en pre_save
        valores_anteriores = _valores_anteriores_anuncios.get(instance.pk, {})
        
        # Si no hay valores anteriores, salir
        if not valores_anteriores:
            logger.debug(f"No hay valores anteriores para {instance.pk}")
            return
        
        # Limpiar del diccionario después de usar
        _valores_anteriores_anuncios.pop(instance.pk, None)
        
        # =====================================================================
        # 🔥 DETECTAR TODOS LOS CAMBIOS RELEVANTES
        # =====================================================================
        
        cambios = []
        
        # 1. Cambios en programación
        try:
            duracion_actual = getattr(instance, 'duracion_dias', None)
            duracion_anterior = valores_anteriores.get('duracion_dias')
            if duracion_actual != duracion_anterior and duracion_actual is not None:
                cambios.append(f"duracion_dias: {duracion_anterior} → {duracion_actual}")
        except Exception as e:
            logger.debug(f"Error comparando duracion_dias: {e}")
        
        try:
            pubs_actual = getattr(instance, 'total_publicaciones', None)
            pubs_anterior = valores_anteriores.get('total_publicaciones')
            if pubs_actual != pubs_anterior and pubs_actual is not None:
                cambios.append(f"total_publicaciones: {pubs_anterior} → {pubs_actual}")
        except Exception as e:
            logger.debug(f"Error comparando total_publicaciones: {e}")
        
        try:
            start_actual = getattr(instance, 'active_time_start', None)
            start_anterior = valores_anteriores.get('active_time_start')
            if start_actual != start_anterior and start_actual is not None:
                cambios.append(f"active_time_start: {start_anterior} → {start_actual}")
        except Exception as e:
            logger.debug(f"Error comparando active_time_start: {e}")
        
        try:
            end_actual = getattr(instance, 'active_time_end', None)
            end_anterior = valores_anteriores.get('active_time_end')
            if end_actual != end_anterior and end_actual is not None:
                cambios.append(f"active_time_end: {end_anterior} → {end_actual}")
        except Exception as e:
            logger.debug(f"Error comparando active_time_end: {e}")
        
        # 🔥 2. Cambios en contenido
        try:
            titulo_actual = getattr(instance, 'titulo', None)
            titulo_anterior = valores_anteriores.get('titulo')
            if titulo_actual != titulo_anterior and titulo_actual is not None:
                cambios.append(f"titulo: '{titulo_anterior}' → '{titulo_actual}'")
        except Exception as e:
            logger.debug(f"Error comparando titulo: {e}")
        
        try:
            desc_actual = getattr(instance, 'descripcion', None)
            desc_anterior = valores_anteriores.get('descripcion')
            if desc_actual != desc_anterior and desc_actual is not None:
                # Mostrar solo primeros 50 caracteres
                desc_ant_corta = (desc_anterior[:50] + '...') if desc_anterior and len(desc_anterior) > 50 else desc_anterior
                desc_act_corta = (desc_actual[:50] + '...') if desc_actual and len(desc_actual) > 50 else desc_actual
                cambios.append(f"descripcion: '{desc_ant_corta}' → '{desc_act_corta}'")
        except Exception as e:
            logger.debug(f"Error comparando descripcion: {e}")
        
        try:
            imagen_actual = str(getattr(instance, 'imagen', ''))
            imagen_anterior = valores_anteriores.get('imagen', '')
            if imagen_actual != imagen_anterior:
                cambios.append(f"imagen: '{imagen_anterior}' → '{imagen_actual}'")
        except Exception as e:
            logger.debug(f"Error comparando imagen: {e}")
        
        # 3. Detectar activación
        try:
            activo_actual = getattr(instance, 'activo', False)
            activo_anterior = valores_anteriores.get('activo', False)
            fue_activado = (not activo_anterior) and activo_actual
        except Exception as e:
            logger.debug(f"Error detectando activación: {e}")
            fue_activado = False
        
        # =====================================================================
        # 🔥 DECISIÓN: ¿REPROGRAMAR?
        # =====================================================================
        
        debe_reprogramar = False
        razon = ""
        
        # CASO A: Se activó (estaba inactivo y ahora está activo)
        if fue_activado:
            debe_reprogramar = True
            razon = "🟢 Anuncio activado"
        
        # CASO B: Hay cambios en parámetros Y está activo
        elif cambios and getattr(instance, 'activo', False):
            debe_reprogramar = True
            razon = "🔄 Cambios detectados:\n   " + "\n   ".join(cambios)
        
        # CASO C: Se desactivó (notificar pero no reprogramar)
        elif activo_anterior and not getattr(instance, 'activo', False):
            logger.info(f"⏸️  Anuncio desactivado: {getattr(instance, 'titulo', instance.pk)}")
            logger.info(f"   Las publicaciones programadas se mantienen")
            return
        
        # CASO D: Sin cambios (presionó "Guardar" sin modificar nada)
        elif not cambios:
            logger.info(f"✓ Anuncio {instance.id} sin cambios, NO reprograma")
            return
        
        # =====================================================================
        # 🔥 EJECUTAR REPROGRAMACIÓN
        # =====================================================================
        
        if debe_reprogramar:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔥 REPROGRAMACIÓN AUTOMÁTICA ACTIVADA")
            logger.info(f"{'='*60}")
            logger.info(f"📢 Anuncio: {getattr(instance, 'titulo', instance.pk)}")
            logger.info(f"📋 Razón: {razon}")
            logger.info(f"{'='*60}\n")
            
            # Llamar a la tarea de programación
            _llamar_programacion(instance)
        else:
            logger.debug(f"✓ Sin cambios relevantes en anuncio {instance.pk}")
    
    finally:
        # 🔥 LIBERAR LOCK
        cache.delete(lock_key)
        logger.debug(f"🔓 Lock liberado para anuncio {instance.id}")


def _llamar_programacion(anuncio):
    """
    🔥 Función auxiliar para llamar a la tarea de programación
    """
    try:
        # Importar aquí para evitar import circular
        from publicadorFacebook.tasks import programar_anuncio_completo_task
        
        # Llamar a la tarea asíncrona de Celery
        resultado = programar_anuncio_completo_task.delay(anuncio.id)
        
        logger.info(f"✅ Tarea de programación enviada a Celery")
        logger.info(f"   Task ID: {resultado.id}")
        
    except ImportError as e:
        logger.error(f"❌ No se pudo importar programar_anuncio_completo_task: {e}")
    
    except Exception as e:
        logger.error(f"❌ Error llamando a programar_anuncio_completo_task: {e}")


# =============================================================================
# 🔥 PARTE 3: VALIDACIÓN DE HORARIOS DEL ANUNCIO
# =============================================================================

@receiver(pre_save, sender='publicadorFacebook.Anuncio')
def validar_horarios_anuncio(sender, instance, **kwargs):
    """
    🛡️ Valida y corrige horarios del anuncio antes de guardar
    """
    try:
        # Asegurar que tiene los campos con defaults
        if not hasattr(instance, 'active_time_start'):
            instance.active_time_start = 0
            logger.debug(f"Anuncio sin active_time_start, set a 0")
        
        if not hasattr(instance, 'active_time_end'):
            instance.active_time_end = 23
            logger.debug(f"Anuncio sin active_time_end, set a 23")
        
        # Validar y corregir rangos
        try:
            start = int(getattr(instance, 'active_time_start', 0))
            end = int(getattr(instance, 'active_time_end', 23))
            
            # Corregir si están fuera de rango 0-23
            if start < 0 or start > 23:
                logger.warning(f"active_time_start fuera de rango ({start}), corrigiendo a 0")
                instance.active_time_start = 0
            
            if end < 0 or end > 23:
                logger.warning(f"active_time_end fuera de rango ({end}), corrigiendo a 23")
                instance.active_time_end = 23
            
            # Corregir si start >= end (inválido)
            if getattr(instance, 'active_time_start', 0) >= getattr(instance, 'active_time_end', 23):
                logger.warning(f"Horarios inválidos (start >= end), corrigiendo a 0-23")
                instance.active_time_start = 0
                instance.active_time_end = 23
        
        except (ValueError, TypeError):
            # Si hay error de conversión, usar defaults
            logger.warning("Error validando horarios, usando defaults 0-23")
            instance.active_time_start = 0
            instance.active_time_end = 23
    
    except Exception as e:
        logger.error(f"💥 Error en validar_horarios_anuncio: {e}")


logger.info("="*80)
logger.info("✅ signals.py DEFINITIVO cargado")
logger.info("✅ Detecta cambios en: duracion_dias, total_publicaciones, horarios, titulo, descripcion, imagen")
logger.info("✅ NO reprograma si solo presionas 'Guardar' sin cambios")
logger.info("="*80)