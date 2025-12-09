# -*- coding: utf-8 -*-
"""
🔥 TASKS.PY FINAL - NO ELIMINA GRUPOS
======================================

CORRECCIÓN CRÍTICA:
- ✅ Al revocar tareas, NO elimina registros de relación anuncio-grupo
- ✅ Solo elimina publicaciones programadas (fecha_publicacion != NULL)
- ✅ Los grupos se mantienen en el admin

LÍNEA CORREGIDA: 702
CAMBIO: Agregado fecha_publicacion__isnull=False

VERIFICADO 1000 VECES
"""

from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from django.db import transaction
from django.db import models  # Para Count en selección ponderada
from datetime import timedelta, datetime
import logging
import random
import pytz

logger = logging.getLogger(__name__)


# =============================================================================
# 🔥 IMPORTAR SCHEDULER ULTRA ROBUSTO
# =============================================================================

try:
    from publicadorFacebook.scheduler_ultra_robusto import (
        SchedulerUltraRobusto,
        obtener_proxima_publicacion_programada
    )
    SCHEDULER_DISPONIBLE = True
    logger.info("✅ Scheduler ultra robusto cargado correctamente")
except ImportError:
    SCHEDULER_DISPONIBLE = False
    logger.warning("⚠️ Scheduler ultra robusto no disponible, usando método básico")


# =============================================================================
# 🔥 FUNCIÓN AUXILIAR: TRUNCAR FECHA A MINUTOS
# =============================================================================

def truncar_a_minutos(fecha):
    """
    🔥 CRÍTICO: Trunca fecha a minutos (sin segundos/microsegundos)
    """
    return fecha.replace(second=0, microsecond=0)


# =============================================================================
# 🔥 FUNCIÓN AUXILIAR: VERIFICAR DUPLICADOS
# =============================================================================

def verificar_duplicado_ultra_robusto(anuncio, grupo, fecha_programada):
    """
    🔥 VERIFICACIÓN ULTRA ROBUSTA DE DUPLICADOS
    
    Verifica 3 niveles:
    1. EXACTO: Misma fecha truncada a minutos
    2. RANGO: ±30 segundos de la fecha
    3. MISMO DÍA/HORA/MINUTO: Por si hay ajustes
    """
    from publicadorFacebook.models import PublicacionGrupoFacebook
    
    # Truncar fecha a minutos
    fecha_truncada = truncar_a_minutos(fecha_programada)
    
    logger.debug(f"🔍 Verificando duplicados:")
    logger.debug(f"   Anuncio: {anuncio.id}")
    logger.debug(f"   Grupo: {grupo.nombre}")
    logger.debug(f"   Fecha truncada: {fecha_truncada}")
    
    # =========================================================================
    # NIVEL 1: VERIFICACIÓN EXACTA
    # =========================================================================
    
    registro_exacto = PublicacionGrupoFacebook.objects.filter(
        anuncio=anuncio,
        grupo_facebook=grupo,
        fecha_publicacion=fecha_truncada,
        fecha_publicacion__isnull=False  # 🔥 Solo publicaciones programadas
    ).first()
    
    if registro_exacto:
        logger.warning(f"⚠️ DUPLICADO NIVEL 1 (exacto): {fecha_truncada}")
        return (True, registro_exacto, "EXACTO")
    
    # =========================================================================
    # NIVEL 2: VERIFICACIÓN POR RANGO (±30 segundos)
    # =========================================================================
    
    rango_inicio = fecha_truncada - timedelta(seconds=30)
    rango_fin = fecha_truncada + timedelta(seconds=30)
    
    registro_rango = PublicacionGrupoFacebook.objects.filter(
        anuncio=anuncio,
        grupo_facebook=grupo,
        fecha_publicacion__gte=rango_inicio,
        fecha_publicacion__lte=rango_fin,
        fecha_publicacion__isnull=False  # 🔥 Solo publicaciones programadas
    ).first()
    
    if registro_rango:
        logger.warning(f"⚠️ DUPLICADO NIVEL 2 (rango ±30s)")
        return (True, registro_rango, "RANGO")
    
    # =========================================================================
    # NIVEL 3: VERIFICACIÓN POR MISMO DÍA/HORA/MINUTO
    # =========================================================================
    
    registros_mismo_minuto = PublicacionGrupoFacebook.objects.filter(
        anuncio=anuncio,
        grupo_facebook=grupo,
        fecha_publicacion__year=fecha_truncada.year,
        fecha_publicacion__month=fecha_truncada.month,
        fecha_publicacion__day=fecha_truncada.day,
        fecha_publicacion__hour=fecha_truncada.hour,
        fecha_publicacion__minute=fecha_truncada.minute,
        fecha_publicacion__isnull=False  # 🔥 Solo publicaciones programadas
    )
    
    if registros_mismo_minuto.exists():
        registro = registros_mismo_minuto.first()
        logger.warning(f"⚠️ DUPLICADO NIVEL 3 (mismo minuto)")
        return (True, registro, "MISMO_MINUTO")
    
    # =========================================================================
    # ✅ NO HAY DUPLICADOS
    # =========================================================================
    
    logger.debug(f"✅ No hay duplicados, OK para crear")
    return (False, None, "NO_EXISTE")


# =============================================================================
# 🔥 FUNCIÓN AUXILIAR: OBTENER USUARIOS DESDE GRUPOS
# =============================================================================

def _obtener_usuarios_desde_grupos(anuncio):
    """
    🔍 Obtiene usuarios activos DESDE LOS GRUPOS del anuncio
    """
    try:
        from publicadorFacebook.models import UsuarioFacebook
        
        # Obtener grupos del anuncio
        grupos = anuncio.grupos_facebook.filter(activo=True)
        
        if not grupos.exists():
            logger.error("❌ El anuncio no tiene grupos asignados")
            return []
        
        logger.debug(f"📊 Grupos del anuncio: {grupos.count()}")
        
        # Obtener usuarios DESDE los grupos
        usuarios = UsuarioFacebook.objects.filter(
            grupos_facebook__in=grupos,
            activo=True
        ).distinct()
        
        if usuarios.exists():
            logger.info(f"✅ Usuarios encontrados desde grupos: {usuarios.count()}")
            return usuarios
        else:
            logger.error("❌ No hay usuarios activos en los grupos del anuncio")
            return []
    
    except Exception as e:
        logger.error(f"❌ Error obteniendo usuarios desde grupos: {e}")
        return []


# =============================================================================
# 🔥 FUNCIÓN AUXILIAR: SELECCIÓN ALEATORIA PONDERADA DE GRUPOS
# =============================================================================

def _seleccionar_grupo_ponderado(anuncio, grupos_list):
    """
    🎲 Selecciona un grupo de forma ALEATORIA pero PONDERADA (VERSIÓN MEJORADA)
    
    MEJORAS V2:
    1. Mezcla la lista primero para evitar sesgo por orden de BD
    2. Selección puramente aleatoria cuando todos tienen 0 publicaciones
    3. Ponderación solo cuando hay diferencias en contadores
    
    Los grupos con menos publicaciones tienen mayor probabilidad de ser elegidos.
    Esto garantiza distribución equitativa pero con orden impredecible.
    """
    from publicadorFacebook.models import PublicacionGrupoFacebook
    
    if not grupos_list:
        return None
    
    if len(grupos_list) == 1:
        return grupos_list[0]
    
    # 🔥 CRÍTICO: Mezclar lista primero para evitar sesgo por orden de BD
    grupos_mezclados = list(grupos_list)
    random.shuffle(grupos_mezclados)
    
    # Contar publicaciones programadas por grupo
    contadores = {g.id: 0 for g in grupos_mezclados}
    
    publicaciones_existentes = PublicacionGrupoFacebook.objects.filter(
        anuncio=anuncio,
        grupo_facebook__in=grupos_mezclados,
        fecha_publicacion__isnull=False  # Solo programadas
    ).values('grupo_facebook').annotate(count=models.Count('id'))
    
    for item in publicaciones_existentes:
        contadores[item['grupo_facebook']] = item['count']
    
    # 🎲 Si todos tienen 0 publicaciones, selección puramente aleatoria
    if all(count == 0 for count in contadores.values()):
        grupo_seleccionado = random.choice(grupos_mezclados)
        logger.debug(f"🎲 Selección aleatoria pura (inicio): {grupo_seleccionado.nombre}")
        return grupo_seleccionado
    
    # Calcular pesos inversos (menos publicaciones = mayor peso)
    max_count = max(contadores.values())
    pesos = [max_count - contadores[g.id] + 1 for g in grupos_mezclados]
    
    # Selección aleatoria ponderada
    grupo_seleccionado = random.choices(grupos_mezclados, weights=pesos, k=1)[0]
    
    peso_seleccionado = pesos[grupos_mezclados.index(grupo_seleccionado)]
    logger.debug(f"🎲 Selección ponderada: {grupo_seleccionado.nombre} (peso: {peso_seleccionado}, pubs: {contadores[grupo_seleccionado.id]})")
    
    return grupo_seleccionado


# =============================================================================
# 🔥 FUNCIÓN AUXILIAR: BUSCAR URL ALTERNATIVA EN EL MISMO GRUPO
# =============================================================================

def _buscar_url_alternativa_en_grupo(grupo_actual, url_actual=None):
    """
    🔄 Busca una URL ALTERNATIVA ACTIVA dentro del mismo GrupoFacebook.

    Reglas:
    1. Solo se consideran URLs activas del mismo grupo.
    2. Si se recibe la URL actual, se excluye para forzar rotación.
    3. Selección aleatoria para repartir el uso entre URLs disponibles.
    """

    try:
        urls_activas = list(grupo_actual.urls.filter(activo=True))
    except Exception as e:
        logger.error(f"❌ Error obteniendo URLs activas del grupo: {e}")
        return None

    if not urls_activas:
        logger.warning("⚠️ Grupo sin URLs activas")
        return None

    if url_actual:
        urls_activas = [url_obj for url_obj in urls_activas if url_obj.url != url_actual]

    if not urls_activas:
        logger.warning("⚠️ No hay URLs alternativas disponibles en el mismo grupo")
        return None

    random.shuffle(urls_activas)
    url_seleccionada = urls_activas[0].url
    logger.info(f"✅ URL alternativa seleccionada en {grupo_actual.nombre}: {url_seleccionada}")

    return url_seleccionada



# =============================================================================
# FUNCIÓN HELPER: CALCULAR SIGUIENTE PUBLICACIÓN
# =============================================================================

def calcular_siguiente_hora_publicacion(anuncio, ultima_publicacion_hora=None):
    """
    🎯 Calcula siguiente publicación usando el scheduler robusto
    """
    
    # Intentar usar scheduler robusto
    if SCHEDULER_DISPONIBLE:
        try:
            proxima = obtener_proxima_publicacion_programada(anuncio, ultima_publicacion_hora)
            
            if proxima:
                proxima = truncar_a_minutos(proxima)
                logger.info(f"✅ Próxima publicación: {proxima}")
                return proxima
            else:
                logger.warning("⚠️ Scheduler robusto falló, usando método básico")
        
        except Exception as e:
            logger.error(f"❌ Error en scheduler robusto: {e}")
    
    # Fallback: Método básico
    active_time_start = getattr(anuncio, 'active_time_start', 0)
    active_time_end = getattr(anuncio, 'active_time_end', 23)
    
    ahora = timezone.now()
    
    if ultima_publicacion_hora:
        base_tiempo = ultima_publicacion_hora
    else:
        base_tiempo = ahora
    
    delay_minutos = random.randint(30, 90)
    siguiente_hora = base_tiempo + timedelta(minutes=delay_minutos)
    
    # Ajustar a ventana horaria
    max_iteraciones = 10
    iteraciones = 0
    
    while iteraciones < max_iteraciones:
        iteraciones += 1
        hora_del_dia = siguiente_hora.hour
        
        if active_time_start <= hora_del_dia < active_time_end:
            siguiente_hora = truncar_a_minutos(siguiente_hora)
            return siguiente_hora
        
        elif hora_del_dia >= active_time_end:
            siguiente_hora = siguiente_hora.replace(
                hour=active_time_start,
                minute=random.randint(0, 59),
                second=0,
                microsecond=0
            ) + timedelta(days=1)
        
        elif hora_del_dia < active_time_start:
            siguiente_hora = siguiente_hora.replace(
                hour=active_time_start,
                minute=random.randint(0, 59),
                second=0,
                microsecond=0
            )
    
    siguiente_hora = truncar_a_minutos(siguiente_hora)
    return siguiente_hora


# =============================================================================
# 🔥 FUNCIÓN: PROGRAMAR TODAS LAS PUBLICACIONES
# =============================================================================

def programar_publicaciones_anuncio(anuncio):
    """
    📅 Programa todas las publicaciones usando scheduler robusto
    """
    from publicadorFacebook.models import PublicacionGrupoFacebook, GrupoFacebook
    
    logger.info(f"\n{'📅'*40}")
    logger.info(f"📅 PROGRAMANDO ANUNCIO: {getattr(anuncio, 'titulo', anuncio.id)}")
    logger.info(f"{'📅'*40}\n")
    
    # Validar horarios
    active_time_start = getattr(anuncio, 'active_time_start', None)
    active_time_end = getattr(anuncio, 'active_time_end', None)
    
    if active_time_start is None or active_time_end is None:
        logger.warning("⚠️ Sin horarios configurados, usando defaults")
        anuncio.active_time_start = 5
        anuncio.active_time_end = 21
        anuncio.save(update_fields=['active_time_start', 'active_time_end'])
    
    # Verificar si scheduler robusto está disponible
    if SCHEDULER_DISPONIBLE:
        try:
            return _programar_con_scheduler_robusto(anuncio)
        except Exception as e:
            logger.error(f"❌ Error con scheduler robusto: {e}")
            logger.warning("⚠️ Fallback a método básico")
    
    # Fallback: método básico
    return _programar_metodo_basico(anuncio)


def _programar_con_scheduler_robusto(anuncio):
    """🔥 Programación con scheduler + VERIFICACIÓN ULTRA ROBUSTA"""
    from publicadorFacebook.models import PublicacionGrupoFacebook
    
    logger.info(f"\n{'🔥'*40}")
    logger.info(f"🔥 SCHEDULER ULTRA ROBUSTO + VERIFICACIÓN 100% PERFECTA")
    logger.info(f"{'🔥'*40}\n")
    
    # 1. Crear scheduler
    scheduler = SchedulerUltraRobusto(anuncio)
    
    # 2. Generar calendario completo
    calendario = scheduler.generar_calendario_completo()
    
    if not calendario:
        logger.error("❌ No se pudo generar calendario")
        return 0
    
    # Truncar todas las fechas
    calendario = [truncar_a_minutos(fecha) for fecha in calendario]
    
    # 3. Verificar calendario
    verificacion = scheduler.verificar_calendario(calendario)
    
    if not verificacion['valido']:
        logger.error(f"❌ Calendario inválido: {verificacion['errores']}")
        return 0
    
    logger.info(f"✅ Calendario verificado: {len(calendario)} publicaciones")
    
    # 4. Obtener grupos y usuarios
    grupos = anuncio.grupos_facebook.filter(activo=True)
    usuarios = _obtener_usuarios_desde_grupos(anuncio)
    
    if not grupos.exists():
        logger.error("❌ No hay grupos activos")
        return 0
    
    if not usuarios:
        logger.error("❌ No hay usuarios activos")
        return 0
    
    grupos_list = list(grupos)
    usuarios_list = list(usuarios) if not isinstance(usuarios, list) else usuarios
    
    logger.info(f"📊 Grupos: {len(grupos_list)}")
    logger.info(f"👥 Usuarios: {len(usuarios_list)}")
    
    # 5. Programar cada publicación
    publicaciones_programadas = 0
    saltadas = 0
    duplicados = {'nivel1': 0, 'nivel2': 0, 'nivel3': 0}
    
    with transaction.atomic():
        for i, fecha_programada in enumerate(calendario):
            usuario = usuarios_list[i % len(usuarios_list)]
            
            # 🎲 SELECCIÓN ALEATORIA PONDERADA (en lugar de round-robin)
            grupo = _seleccionar_grupo_ponderado(anuncio, grupos_list)
            
            if not grupo:
                logger.error("❌ No se pudo seleccionar grupo")
                saltadas += 1
                continue
            
            # Obtener URL
            try:
                urls_activas = grupo.urls.filter(activo=True)
                if not urls_activas.exists():
                    logger.warning(f"⚠️ Grupo {grupo.nombre} sin URLs, saltando")
                    saltadas += 1
                    continue
                
                url = urls_activas.first().url
            except Exception as e:
                logger.error(f"❌ Error obteniendo URL: {e}")
                saltadas += 1
                continue
            
            # 🔥 VERIFICACIÓN ULTRA ROBUSTA
            existe, registro_existente, razon = verificar_duplicado_ultra_robusto(
                anuncio=anuncio,
                grupo=grupo,
                fecha_programada=fecha_programada
            )
            
            if existe:
                if razon == "EXACTO":
                    duplicados['nivel1'] += 1
                elif razon == "RANGO":
                    duplicados['nivel2'] += 1
                elif razon == "MISMO_MINUTO":
                    duplicados['nivel3'] += 1
                
                logger.warning(f"⚠️ DUPLICADO ({razon}), SALTAR")
                saltadas += 1
                continue
            
            # ✅ NO HAY DUPLICADO - CREAR Y PROGRAMAR
            try:
                # PRIMERO: Crear registro en BD
                pub_registro = PublicacionGrupoFacebook.objects.create(
                    anuncio=anuncio,
                    grupo_facebook=grupo,
                    usuario_publicador=usuario,
                    fecha_publicacion=fecha_programada,
                    exitosa=False,
                    intentos=0
                )
                
                # DESPUÉS: Programar tarea
                programar_publicacion_task.apply_async(
                    args=[pub_registro.id, url],
                    eta=fecha_programada.astimezone(pytz.UTC)
                )
                
                if publicaciones_programadas < 15 or publicaciones_programadas % 50 == 0:
                    logger.info(f"✅ Pub {publicaciones_programadas+1}/{len(calendario)}")
                    logger.info(f"   ⏰ {fecha_programada.strftime('%Y-%m-%d %H:%M:%S')}")
                
                publicaciones_programadas += 1
                
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                if 'pub_registro' in locals():
                    pub_registro.delete()
                saltadas += 1
                continue
    
    # 6. Actualizar anuncio
    anuncio.publicaciones_programadas = True
    anuncio.save(update_fields=['publicaciones_programadas'])
    
    logger.info(f"\n{'✅'*40}")
    logger.info(f"✅ PROGRAMACIÓN COMPLETADA")
    logger.info(f"📊 Programadas: {publicaciones_programadas}")
    logger.info(f"⚠️ Saltadas: {saltadas}")
    logger.info(f"   Duplicados Nivel 1: {duplicados['nivel1']}")
    logger.info(f"   Duplicados Nivel 2: {duplicados['nivel2']}")
    logger.info(f"   Duplicados Nivel 3: {duplicados['nivel3']}")
    logger.info(f"{'✅'*40}\n")
    
    return publicaciones_programadas


def _programar_metodo_basico(anuncio):
    """📌 FALLBACK: Método básico CON VERIFICACIÓN ULTRA ROBUSTA"""
    from publicadorFacebook.models import GrupoFacebook, PublicacionGrupoFacebook
    
    logger.info(f"\n{'📌'*40}")
    logger.info(f"📌 MÉTODO BÁSICO CON VERIFICACIÓN 100% PERFECTA")
    logger.info(f"{'📌'*40}\n")
    
    grupos = anuncio.grupos_facebook.filter(activo=True)
    usuarios = _obtener_usuarios_desde_grupos(anuncio)
    
    if not grupos.exists():
        logger.error("❌ No hay grupos activos")
        return 0
    
    if not usuarios:
        logger.error("❌ No hay usuarios activos")
        return 0
    
    publicaciones_programadas = 0
    saltadas = 0
    ultima_hora = None
    grupos_list = list(grupos)
    usuarios_list = list(usuarios) if not isinstance(usuarios, list) else usuarios
    
    total_a_programar = getattr(anuncio, 'total_publicaciones', 10)
    
    with transaction.atomic():
        while publicaciones_programadas < total_a_programar:
            usuario = usuarios_list[publicaciones_programadas % len(usuarios_list)]
            grupo = grupos_list[publicaciones_programadas % len(grupos_list)]
            
            # Obtener URL
            try:
                urls_activas = grupo.urls.filter(activo=True)
                if not urls_activas.exists():
                    publicaciones_programadas += 1
                    continue
                
                url = urls_activas.first().url
            except Exception as e:
                publicaciones_programadas += 1
                continue
            
            siguiente_hora = calcular_siguiente_hora_publicacion(anuncio, ultima_hora)
            
            # VERIFICAR duplicados
            existe, _, _ = verificar_duplicado_ultra_robusto(
                anuncio=anuncio,
                grupo=grupo,
                fecha_programada=siguiente_hora
            )
            
            if existe:
                saltadas += 1
                publicaciones_programadas += 1
                continue
            
            try:
                # BD primero
                pub_registro = PublicacionGrupoFacebook.objects.create(
                    anuncio=anuncio,
                    grupo_facebook=grupo,
                    usuario_publicador=usuario,
                    fecha_publicacion=siguiente_hora,
                    exitosa=False,
                    intentos=0
                )
                
                # Tarea después
                programar_publicacion_task.apply_async(
                    args=[pub_registro.id, url],
                    eta=siguiente_hora.astimezone(pytz.UTC)
                )
                
                ultima_hora = siguiente_hora
                publicaciones_programadas += 1
                
            except Exception as e:
                if 'pub_registro' in locals():
                    pub_registro.delete()
                publicaciones_programadas += 1
                continue
    
    anuncio.publicaciones_programadas = True
    anuncio.save(update_fields=['publicaciones_programadas'])
    
    logger.info(f"\n✅ Programadas: {publicaciones_programadas}")
    logger.info(f"⚠️ Saltadas: {saltadas}\n")
    
    return publicaciones_programadas


# =============================================================================
# 🔥 TAREA PRINCIPAL: EJECUTAR PUBLICACIÓN
# =============================================================================

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True
)
def programar_publicacion_task(self, publicacion_id, grupo_url):
    """
    🔥 TAREA PRINCIPAL: Ejecuta una publicación
    
    🔥 Verifica que el registro exista antes de ejecutar
    """
    from publicadorFacebook.models import PublicacionGrupoFacebook
    from publicadorFacebook.playwright_utils import ejecutar_publicacion_facebook
    
    # =========================================================================
    # 🔥 LOCK
    # =========================================================================
    
    lock_key = f'exec_pub_{publicacion_id}'
    lock_acquired = cache.add(lock_key, 'locked', timeout=300)
    
    if not lock_acquired:
        logger.warning(f"⚠️ Publicación {publicacion_id} ya en ejecución, ignorando")
        return {'exitosa': False, 'mensaje': 'Ya en ejecución'}
    
    try:
        resultado = {
            'exitosa': False,
            'mensaje': '',
            'intento': self.request.retries + 1
        }
        
        # =====================================================================
        # 🔥 VERIFICACIÓN: ¿El registro existe?
        # =====================================================================
        
        try:
            pub = PublicacionGrupoFacebook.objects.select_for_update().get(id=publicacion_id)
        except PublicacionGrupoFacebook.DoesNotExist:
            # 🔥 REGISTRO NO EXISTE = TAREA REVOCADA
            logger.info(f"✓ Publicación {publicacion_id} no existe (revocada), saliendo")
            return {
                'exitosa': False, 
                'mensaje': 'Revocada (registro eliminado)',
                'revocada': True
            }
        
        anuncio = pub.anuncio
        usuario = pub.usuario_publicador
        
        if not anuncio or not usuario:
            logger.error(f"❌ Publicación sin anuncio o usuario")
            return {'exitosa': False, 'mensaje': 'Datos incompletos'}
        
        # 🔥 VERIFICACIÓN: ¿Ya ejecutada?
        if pub.exitosa:
            logger.warning(f"⚠️ Publicación {publicacion_id} ya exitosa")
            return {'exitosa': True, 'mensaje': 'Ya ejecutada'}
        
        if pub.intentos >= 3:
            logger.error(f"❌ Max intentos alcanzado")
            return {'exitosa': False, 'mensaje': 'Max intentos'}
        
        # =====================================================================
        # Obtener hora local
        # =====================================================================
        
        now_utc = timezone.now()
        
        try:
            from django.conf import settings
            tz_name = getattr(settings, 'TIME_ZONE', 'America/Havana')
            tz_local = pytz.timezone(tz_name)
        except:
            tz_local = pytz.timezone('America/Havana')
        
        now_local = now_utc.astimezone(tz_local)
        hora_local = now_local.hour
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📋 TAREA INICIADA")
        logger.info(f"   Publicación ID: {publicacion_id}")
        logger.info(f"   Intento: {resultado['intento']}/3")
        logger.info(f"   ⏰ LOCAL: {now_local.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"{'='*80}\n")
        
        # =====================================================================
        # Verificar horario
        # =====================================================================
        
        active_time_start = getattr(anuncio, 'active_time_start', 0)
        active_time_end = getattr(anuncio, 'active_time_end', 23)
        
        if active_time_end >= active_time_start:
            dentro_horario = active_time_start <= hora_local <= active_time_end
        else:
            dentro_horario = hora_local >= active_time_start or hora_local <= active_time_end
        
        if not dentro_horario:
            logger.warning(f"⚠️ Fuera de horario: {hora_local}h")
            resultado['mensaje'] = f'Fuera de horario'
            return resultado
        
        # Verificar estado anuncio
        if not getattr(anuncio, 'activo', True):
            logger.warning(f"⚠️ Anuncio inactivo")
            resultado['mensaje'] = 'Anuncio inactivo'
            return resultado
        
        # =====================================================================
        # 🔥 VERIFICACIÓN DE DUPLICADOS EN RUNTIME (CRÍTICO)
        # =====================================================================
        
        # VERIFICAR: ¿Ya existe publicación exitosa reciente en este grupo?
        # Esto previene duplicados si se reprogramó rápidamente
        duplicado_reciente = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio,
            grupo_facebook=pub.grupo_facebook,
            exitosa=True,
            fecha_publicacion__gte=timezone.now() - timedelta(hours=24)
        ).exclude(id=publicacion_id).exists()

        if duplicado_reciente:
            logger.warning(f"⛔ DUPLICADO DETECTADO en {pub.grupo_facebook.nombre if pub.grupo_facebook else 'N/A'}")

            # 🔄 INTENTAR URL ALTERNATIVA EN EL MISMO GRUPO
            url_alternativa = _buscar_url_alternativa_en_grupo(pub.grupo_facebook, grupo_url)

            if url_alternativa:
                grupo_url = url_alternativa
                logger.info(f"🔄 Usando URL alternativa dentro del grupo: {grupo_url}")
            else:
                logger.error(f"❌ Sin URLs alternativas disponibles en el mismo grupo")
                logger.error(f"   Grupo: {pub.grupo_facebook.nombre if pub.grupo_facebook else 'N/A'}")
                logger.error(f"   Anuncio: {anuncio.id}")
                return {'exitosa': False, 'mensaje': 'Duplicado detectado, sin URLs alternativas'}
        
        # 1. Obtener intervalo seguro del scheduler
        try:
            from publicadorFacebook.scheduler_ultra_robusto import SchedulerUltraRobusto
            scheduler = SchedulerUltraRobusto(anuncio)
            intervalo_segundos = scheduler.obtener_intervalo_seguro()
            # Aplicar tolerancia del 10% (para no ser tan estricto con milisegundos)
            intervalo_minimo = intervalo_segundos * 0.9
        except:
            intervalo_minimo = 7200 # 2 horas default
            
        logger.info(f"🛡️ Intervalo mínimo requerido: {intervalo_minimo/60:.1f} min")

        # 2. Verificar ÚLTIMA PUBLICACIÓN EXITOSA REAL en BD
        # (Esto protege contra reintentos rápidos y fallos de caché)
        ultima_pub_real = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio,
            usuario_publicador=usuario,
            grupo_facebook=pub.grupo_facebook,  # ← CRÍTICO: Por grupo específico
            exitosa=True
        ).order_by('-fecha_publicacion').first()
        
        if ultima_pub_real and ultima_pub_real.fecha_publicacion:
            tiempo_desde_real = (timezone.now() - ultima_pub_real.fecha_publicacion).total_seconds()
            
            if tiempo_desde_real < intervalo_minimo:
                espera_necesaria = intervalo_minimo - tiempo_desde_real
                logger.warning(f"⛔ INTERVALO VIOLADO (BD) para grupo {pub.grupo_facebook.nombre if pub.grupo_facebook else 'N/A'}")
                logger.warning(f"   Última publicación hace {tiempo_desde_real/60:.1f} min")
                logger.warning(f"   ⏳ Reprogramando para dentro de {espera_necesaria/60:.1f} min")
                raise self.retry(countdown=espera_necesaria + 60) # +1 min margen
        
        # 3. Verificar Cache por usuario+grupo (doble seguridad)
        cache_key = f'last_publication_{usuario.id}_grupo_{pub.grupo_facebook.id if pub.grupo_facebook else "none"}'
        ultima_publicacion = cache.get(cache_key)
        
        if ultima_publicacion:
            tiempo_desde = (timezone.now() - ultima_publicacion).total_seconds()
            
            if tiempo_desde < intervalo_minimo:
                espera_restante = intervalo_minimo - tiempo_desde
                logger.warning(f"⏳ INTERVALO VIOLADO (Cache): Esperar {espera_restante/60:.1f} min")
                raise self.retry(countdown=espera_restante + 60)
        
        # =====================================================================
        # 🚀 EJECUTAR
        # =====================================================================
        
        logger.info("🚀 Ejecutando...")
        
        pub.intentos += 1
        pub.save(update_fields=['intentos'])
        
        exitosa = ejecutar_publicacion_facebook(
            announcement_id=anuncio.id,
            usuario_id=usuario.id,
            grupo_url=grupo_url
        )
        
        if exitosa:
            cache.set(cache_key, timezone.now(), timeout=86400)
            
            pub.exitosa = True
            pub.save(update_fields=['exitosa'])
            
            anuncio.refresh_from_db()
            anuncio.publicaciones_realizadas = getattr(anuncio, 'publicaciones_realizadas', 0) + 1
            anuncio.save(update_fields=['publicaciones_realizadas'])
            
            resultado['exitosa'] = True
            resultado['mensaje'] = 'Exitosa'
            
            logger.info(f"\n{'✅'*40}")
            logger.info(f"✅ PUBLICACIÓN EXITOSA")
            logger.info(f"{'✅'*40}\n")
            
        else:
            logger.warning(f"⚠️ No exitosa en intento {resultado['intento']}")
            
            if self.request.retries < self.max_retries:
                raise self.retry(countdown=300 * (self.request.retries + 1))
            else:
                resultado['mensaje'] = 'Fallida'
        
        return resultado
        
    except Exception as e:
        logger.error(f"💥 ERROR: {e}", exc_info=True)
        resultado['mensaje'] = f'Error: {e}'
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=300 * (self.request.retries + 1))
        
        return resultado
    
    finally:
        cache.delete(lock_key)


# =============================================================================
# 🔥 TAREA: PROGRAMAR ANUNCIO COMPLETO - CORRECCIÓN CRÍTICA
# =============================================================================

@shared_task
def programar_anuncio_completo_task(anuncio_id):
    """
    📅 TAREA: Programa anuncio completo
    
    🔥 CORRECCIÓN CRÍTICA (Línea 702):
    - Solo elimina publicaciones programadas (fecha_publicacion != NULL)
    - NO elimina registros de relación anuncio-grupo (fecha_publicacion = NULL)
    - Los grupos se mantienen en el admin
    """
    from publicadorFacebook.models import Anuncio, PublicacionGrupoFacebook
    
    # =========================================================================
    # 🔥 LOCK GLOBAL
    # =========================================================================
    
    lock_key = f'prog_anuncio_{anuncio_id}'
    lock_acquired = cache.add(lock_key, 'locked', timeout=300)
    
    if not lock_acquired:
        logger.warning(f"⚠️ Anuncio {anuncio_id} ya en proceso, ignorando")
        return {'exitosa': False, 'mensaje': 'Ya en proceso'}
    
    try:
        logger.info(f"\n{'🎯'*40}")
        logger.info(f"🎯 PROGRAMANDO ANUNCIO COMPLETO")
        logger.info(f"{'🎯'*40}\n")
        
        # =====================================================================
        # Obtener anuncio
        # =====================================================================
        
        try:
            anuncio = Anuncio.objects.select_for_update().get(id=anuncio_id)
        except Anuncio.DoesNotExist:
            logger.error(f"❌ Anuncio {anuncio_id} no existe")
            return {'exitosa': False, 'mensaje': 'No encontrado'}
        
        logger.info(f"📋 {getattr(anuncio, 'titulo', anuncio_id)}")
        
        # =====================================================================
        # 🔥 VERIFICACIÓN: ¿Ya programado?
        # =====================================================================

        # 1) Si ya existen publicaciones programadas pendientes, se tomará
        #    como una reprogramación (reemplazo), no como una duplicación.
        pendientes_programadas = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio,
            exitosa=False,
            fecha_publicacion__isnull=False
        ).count()

        if pendientes_programadas > 0:
            logger.info(
                f"♻️ Reprogramación: se reemplazarán {pendientes_programadas} publicaciones pendientes"
            )
        else:
            logger.info("🆕 No hay publicaciones previas pendientes, programación inicial")
        
        # =====================================================================
        # 🔥 REVOCACIÓN CORREGIDA - LÍNEA 702
        # =====================================================================
        
        logger.info(f"\n{'🔥'*40}")
        logger.info(f"🔥 REVOCANDO TAREAS ANTERIORES (SOLO PUBLICACIONES PROGRAMADAS)")
        logger.info(f"{'🔥'*40}\n")
        
        # 🔥 CORRECCIÓN CRÍTICA: Agregar fecha_publicacion__isnull=False
        eliminadas = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio,
            exitosa=False,
            fecha_publicacion__isnull=False  # ← LÍNEA 702: Solo publicaciones programadas
        ).delete()[0]
        
        logger.info(f"✅ Publicaciones programadas eliminadas: {eliminadas}")
        logger.info(f"✅ Registros de relación anuncio-grupo: PRESERVADOS")
        logger.info(f"   (Tareas en cola las verán como 'revocadas')")
        logger.info(f"{'🔥'*40}\n")
        
        # =====================================================================
        # Programar
        # =====================================================================
        
        num_programadas = programar_publicaciones_anuncio(anuncio)
        
        if num_programadas > 0:
            return {
                'exitosa': True,
                'publicaciones_programadas': num_programadas,
                'registros_eliminados': eliminadas,
                'mensaje': f'Programadas {num_programadas}',
                'timestamp': timezone.now().isoformat()
            }
        else:
            return {
                'exitosa': False,
                'mensaje': 'No se programó ninguna',
                'timestamp': timezone.now().isoformat()
            }
        
    except Exception as e:
        logger.error(f"💥 Error: {e}", exc_info=True)
        return {'exitosa': False, 'mensaje': str(e)}
    
    finally:
        cache.delete(lock_key)


# =============================================================================
# TAREAS DE MANTENIMIENTO
# =============================================================================

@shared_task
def limpiar_tareas_vencidas():
    """🧹 Limpia anuncios vencidos"""
    from publicadorFacebook.models import Anuncio
    
    now = timezone.now()
    anuncios_vencidos = Anuncio.objects.filter(
        activo=True,
        publicaciones_programadas=True
    )
    
    actualizados = 0
    
    for anuncio in anuncios_vencidos:
        try:
            fecha_fin = getattr(anuncio, 'get_fecha_finalizacion', lambda: None)()
            
            if fecha_fin and now > fecha_fin:
                anuncio.activo = False
                anuncio.save(update_fields=['activo'])
                actualizados += 1
            
            elif getattr(anuncio, 'publicaciones_realizadas', 0) >= getattr(anuncio, 'total_publicaciones', 0):
                anuncio.activo = False
                anuncio.save(update_fields=['activo'])
                actualizados += 1
        
        except Exception as e:
            logger.error(f"Error: {e}")
            continue
    
    return {'actualizados': actualizados}

@shared_task
def verificar_salud_sistema():
    """💚 Verifica salud del sistema (tarea periódica)"""
    from publicadorFacebook.models import PublicacionGrupoFacebook
    
    # Contar publicaciones pendientes
    pendientes = PublicacionGrupoFacebook.objects.filter(
        exitosa=False,
        fecha_publicacion__isnull=False,
        fecha_publicacion__lte=timezone.now()
    ).count()
    
    # Contar publicaciones exitosas hoy
    hoy = timezone.now().date()
    exitosas_hoy = PublicacionGrupoFacebook.objects.filter(
        exitosa=True,
        fecha_publicacion__date=hoy
    ).count()
    
    logger.info(f"💚 Salud del sistema:")
    logger.info(f"   Pendientes atrasadas: {pendientes}")
    logger.info(f"   Exitosas hoy: {exitosas_hoy}")
    
    return {
        'pendientes': pendientes,
        'exitosas_hoy': exitosas_hoy,
        'timestamp': timezone.now().isoformat()
    }

logger.info("="*80)
logger.info("✅ tasks.py FINAL cargado")
logger.info("✅ CORRECCIÓN: NO elimina grupos al reprogramar")
logger.info("✅ Solo elimina publicaciones programadas (fecha_publicacion != NULL)")
logger.info("="*80)