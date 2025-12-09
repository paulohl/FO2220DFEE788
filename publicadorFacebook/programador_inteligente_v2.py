# -*- coding: utf-8 -*-
"""
🎯 SISTEMA INTELIGENTE DE PROGRAMACIÓN

Calcula automáticamente:
- Cuántos días estará activo el anuncio
- Cuántas publicaciones debe hacer (grupos × frecuencia)
- Espaciado óptimo según horario disponible
- Distribución uniforme en el tiempo
- Rotación aleatoria de grupos
"""

from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta, datetime
import random
import logging
import math

logger = logging.getLogger(__name__)


def obtener_grupos_rotados(anuncio_id):
    """
    Obtiene grupos en orden ALEATORIO, asegurando que nunca empiece
    por el mismo grupo dos veces consecutivas
    """
    from publicadorFacebook.models import GrupoFacebook
    
    grupos = list(GrupoFacebook.objects.filter(activo=True).order_by('?'))
    
    if not grupos:
        return []
    
    # Obtener último grupo inicial
    cache_key = f'ultimo_grupo_inicial_anuncio_{anuncio_id}'
    ultimo_grupo_id = cache.get(cache_key)
    
    # Shuffle
    random.shuffle(grupos)
    
    # Si el primero es igual al último, rotar
    intentos = 0
    while grupos and ultimo_grupo_id and grupos[0].id == ultimo_grupo_id and intentos < 10:
        grupos.append(grupos.pop(0))
        intentos += 1
    
    # Guardar nuevo primero
    if grupos:
        cache.set(cache_key, grupos[0].id, timeout=2592000)
    
    return grupos


def calcular_parametros_programacion(anuncio):
    """
    Calcula los parámetros de programación basándose en:
    - Vigencia del anuncio (días activo)
    - Horario disponible (active_time_start - active_time_end)
    - Cantidad de grupos
    
    Returns:
        dict con parámetros calculados
    """
    
    logger.info(f"\n{'🔢'*40}")
    logger.info(f"🔢 CÁLCULO DE PARÁMETROS DE PROGRAMACIÓN")
    logger.info(f"{'🔢'*40}\n")
    
    # Obtener horarios
    active_time_start = getattr(anuncio, 'active_time_start', 9)
    active_time_end = getattr(anuncio, 'active_time_end', 21)
    
    # Calcular horas disponibles por día (active_time_end es exclusivo)
    horas_disponibles_dia = active_time_end - active_time_start
    
    logger.info(f"⏰ HORARIOS:")
    logger.info(f"   Inicio: {active_time_start}:00")
    logger.info(f"   Fin: {active_time_end}:00")
    logger.info(f"   → Rango válido: {active_time_start}:00 - {active_time_end-1}:59")
    logger.info(f"   → Horas disponibles/día: {horas_disponibles_dia} horas")
    
    # Calcular días de vigencia del anuncio
    dias_vigencia = None
    
    # Opción 1: Si tiene fecha_fin
    if hasattr(anuncio, 'fecha_fin') and anuncio.fecha_fin:
        fecha_inicio = getattr(anuncio, 'fecha_inicio', None) or getattr(anuncio, 'fecha_creacion', timezone.now())
        dias_vigencia = (anuncio.fecha_fin - fecha_inicio).days
        logger.info(f"\n📅 VIGENCIA (desde fecha_fin):")
        logger.info(f"   Inicio: {fecha_inicio.strftime('%Y-%m-%d')}")
        logger.info(f"   Fin: {anuncio.fecha_fin.strftime('%Y-%m-%d')}")
        logger.info(f"   → Días de vigencia: {dias_vigencia} días")
    
    # Opción 2: Si tiene dias_activo
    elif hasattr(anuncio, 'dias_activo') and anuncio.dias_activo:
        dias_vigencia = anuncio.dias_activo
        logger.info(f"\n📅 VIGENCIA (desde dias_activo):")
        logger.info(f"   → Días configurados: {dias_vigencia} días")
    
    # Opción 3: Default 30 días
    else:
        dias_vigencia = 30
        logger.info(f"\n📅 VIGENCIA (default):")
        logger.info(f"   → Días por defecto: {dias_vigencia} días")
    
    # Obtener cantidad de grupos
    from publicadorFacebook.models import GrupoFacebook
    total_grupos = GrupoFacebook.objects.filter(activo=True).count()
    
    logger.info(f"\n📊 GRUPOS:")
    logger.info(f"   Total grupos activos: {total_grupos}")
    
    if total_grupos == 0:
        logger.error("❌ No hay grupos activos")
        return None
    
    # Calcular total de publicaciones
    # Por defecto: 1 publicación por grupo por día
    publicaciones_por_grupo_por_dia = 1
    total_publicaciones = total_grupos * dias_vigencia * publicaciones_por_grupo_por_dia
    
    logger.info(f"\n📈 PUBLICACIONES:")
    logger.info(f"   Publicaciones por grupo/día: {publicaciones_por_grupo_por_dia}")
    logger.info(f"   Total publicaciones: {total_publicaciones}")
    logger.info(f"   (grupos: {total_grupos} × días: {dias_vigencia} × freq: {publicaciones_por_grupo_por_dia})")
    
    # Calcular publicaciones por día
    publicaciones_por_dia = total_grupos * publicaciones_por_grupo_por_dia
    
    logger.info(f"\n📆 DISTRIBUCIÓN DIARIA:")
    logger.info(f"   Publicaciones/día: {publicaciones_por_dia}")
    
    # Calcular espaciado entre publicaciones
    if publicaciones_por_dia > 0:
        espaciado_horas = horas_disponibles_dia / publicaciones_por_dia
        espaciado_minutos = espaciado_horas * 60
    else:
        espaciado_horas = horas_disponibles_dia
        espaciado_minutos = espaciado_horas * 60
    
    logger.info(f"\n⏱️  ESPACIADO CALCULADO:")
    logger.info(f"   Entre publicaciones: {espaciado_horas:.2f} horas ({espaciado_minutos:.0f} minutos)")
    logger.info(f"   Fórmula: {horas_disponibles_dia}h disponibles / {publicaciones_por_dia} pubs/día")
    
    parametros = {
        'dias_vigencia': dias_vigencia,
        'active_time_start': active_time_start,
        'active_time_end': active_time_end,
        'horas_disponibles_dia': horas_disponibles_dia,
        'total_grupos': total_grupos,
        'publicaciones_por_grupo_por_dia': publicaciones_por_grupo_por_dia,
        'total_publicaciones': total_publicaciones,
        'publicaciones_por_dia': publicaciones_por_dia,
        'espaciado_horas': espaciado_horas,
        'espaciado_minutos': espaciado_minutos
    }
    
    logger.info(f"{'🔢'*40}\n")
    
    return parametros


def programar_anuncio_inteligente(anuncio_id):
    """
    🎯 PROGRAMADOR INTELIGENTE
    
    Calcula automáticamente:
    - Vigencia del anuncio
    - Espaciado óptimo según horario
    - Distribución uniforme
    - Rotación de grupos
    
    Returns:
        dict con resultado
    """
    from publicadorFacebook.models import Anuncio, PublicacionGrupoFacebook
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 PROGRAMADOR INTELIGENTE - CÁLCULO AUTOMÁTICO")
    logger.info(f"{'='*80}\n")
    
    try:
        # Obtener anuncio
        anuncio = Anuncio.objects.get(id=anuncio_id)
        
        logger.info(f"📋 Anuncio: {anuncio.titulo}")
        logger.info(f"   ID: {anuncio.id}")
        
        # Calcular parámetros
        params = calcular_parametros_programacion(anuncio)
        
        if not params:
            return {
                'exitosa': False,
                'mensaje': 'No se pudieron calcular parámetros',
                'anuncio_id': anuncio_id
            }
        
        # Obtener usuarios
        usuarios = None
        for campo in ['usuarios_facebook', 'usuarios', 'usuario_set', 'usuariofacebook_set']:
            if hasattr(anuncio, campo):
                try:
                    usuarios = getattr(anuncio, campo).filter(activo=True)
                    if usuarios.exists():
                        logger.info(f"\n👥 Usuarios encontrados: {usuarios.count()}")
                        break
                except:
                    pass
        
        if not usuarios or not usuarios.exists():
            logger.error("❌ No hay usuarios activos")
            return {
                'exitosa': False,
                'mensaje': 'No hay usuarios activos',
                'anuncio_id': anuncio_id
            }
        
        # Obtener grupos con rotación
        grupos_rotados = obtener_grupos_rotados(anuncio_id)
        
        if not grupos_rotados:
            logger.error("❌ No hay grupos activos")
            return {
                'exitosa': False,
                'mensaje': 'No hay grupos activos',
                'anuncio_id': anuncio_id
            }
        
        logger.info(f"\n🔀 Grupos rotados: {len(grupos_rotados)}")
        logger.info(f"   Primer grupo: {grupos_rotados[0].nombre}")
        
        # Calcular fecha de inicio
        ultima_pub = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio
        ).order_by('-fecha_programada').first()
        
        if ultima_pub and ultima_pub.fecha_programada > timezone.now():
            fecha_actual = ultima_pub.fecha_programada
            logger.info(f"\n📅 Inicio: {fecha_actual.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"   (continúa desde última programación)")
        else:
            # Empezar desde ahora, ajustado al horario
            ahora = timezone.now()
            
            if ahora.hour >= params['active_time_end']:
                # Muy tarde, empezar mañana
                fecha_actual = ahora.replace(
                    hour=params['active_time_start'],
                    minute=0,
                    second=0,
                    microsecond=0
                ) + timedelta(days=1)
            elif ahora.hour < params['active_time_start']:
                # Muy temprano, empezar hoy
                fecha_actual = ahora.replace(
                    hour=params['active_time_start'],
                    minute=0,
                    second=0,
                    microsecond=0
                )
            else:
                # Dentro de horario, empezar ahora
                fecha_actual = ahora.replace(second=0, microsecond=0)
            
            logger.info(f"\n📅 Inicio: {fecha_actual.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"   (calculado desde ahora)")
        
        # Programar publicaciones
        logger.info(f"\n{'📊'*40}")
        logger.info(f"📊 CREANDO PUBLICACIONES")
        logger.info(f"{'📊'*40}\n")
        
        publicaciones_creadas = []
        dia_actual = 0
        grupos_en_dia = []
        
        for dia in range(params['dias_vigencia']):
            logger.info(f"{'─'*60}")
            logger.info(f"DÍA {dia + 1}/{params['dias_vigencia']}")
            logger.info(f"{'─'*60}\n")
            
            # Para cada grupo (1 vez por día)
            for i, grupo in enumerate(grupos_rotados):
                # Calcular hora de publicación
                minutos_desde_inicio = i * params['espaciado_minutos']
                horas = int(minutos_desde_inicio // 60)
                minutos = int(minutos_desde_inicio % 60)
                
                # Fecha programada
                fecha_programada = fecha_actual.replace(
                    hour=params['active_time_start'] + horas,
                    minute=minutos,
                    second=0,
                    microsecond=0
                ) + timedelta(days=dia)
                
                # Verificar que esté dentro de horario
                if fecha_programada.hour >= params['active_time_end']:
                    logger.info(f"⚠️  Grupo {grupo.nombre}: Fuera de horario, saltando")
                    continue
                
                # Seleccionar usuario
                usuario = random.choice(list(usuarios))
                
                # Crear publicación
                pub = PublicacionGrupoFacebook.objects.create(
                    anuncio=anuncio,
                    grupo=grupo,
                    usuario_facebook=usuario,
                    fecha_programada=fecha_programada,
                    publicado=False
                )
                
                publicaciones_creadas.append({
                    'grupo': grupo.nombre,
                    'fecha': fecha_programada,
                    'dia': dia + 1
                })
                
                logger.info(f"✅ Grupo: {grupo.nombre}")
                logger.info(f"   Fecha: {fecha_programada.strftime('%Y-%m-%d %H:%M')}")
                logger.info(f"   Usuario: {usuario.email}")
                
                if len(publicaciones_creadas) > 1:
                    anterior = publicaciones_creadas[-2]
                    diferencia = fecha_programada - anterior['fecha']
                    horas_dif = diferencia.total_seconds() / 3600
                    logger.info(f"   Espaciado: {horas_dif:.2f} horas desde anterior\n")
        
        # Marcar como programado
        anuncio.publicaciones_programadas = True
        anuncio.save(update_fields=['publicaciones_programadas'])
        
        # Resumen
        logger.info(f"{'='*80}")
        logger.info(f"✅ PROGRAMACIÓN COMPLETADA")
        logger.info(f"{'='*80}")
        logger.info(f"📊 Publicaciones creadas: {len(publicaciones_creadas)}")
        logger.info(f"📅 Primera: {publicaciones_creadas[0]['fecha'].strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"📅 Última: {publicaciones_creadas[-1]['fecha'].strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"⏱️  Espaciado usado: {params['espaciado_horas']:.2f} horas ({params['espaciado_minutos']:.0f} min)")
        logger.info(f"🔀 Primer grupo: {publicaciones_creadas[0]['grupo']}")
        logger.info(f"{'='*80}\n")
        
        return {
            'exitosa': True,
            'mensaje': 'Programación inteligente completada',
            'anuncio_id': anuncio_id,
            'publicaciones_creadas': len(publicaciones_creadas),
            'parametros': params,
            'primer_grupo': publicaciones_creadas[0]['grupo'],
            'fecha_primera': publicaciones_creadas[0]['fecha'].isoformat(),
            'fecha_ultima': publicaciones_creadas[-1]['fecha'].isoformat()
        }
    
    except Exception as e:
        logger.error(f"💥 ERROR: {e}", exc_info=True)
        return {
            'exitosa': False,
            'mensaje': str(e),
            'anuncio_id': anuncio_id
        }


def limpiar_y_reprogramar_inteligente(anuncio_id):
    """
    Limpia publicaciones existentes y reprograma con cálculo inteligente
    """
    from publicadorFacebook.models import Anuncio, PublicacionGrupoFacebook
    
    logger.info(f"\n{'🔄'*40}")
    logger.info(f"🔄 LIMPIEZA Y REPROGRAMACIÓN INTELIGENTE")
    logger.info(f"{'🔄'*40}\n")
    
    try:
        anuncio = Anuncio.objects.get(id=anuncio_id)
        
        logger.info(f"📋 Anuncio: {anuncio.titulo}")
        
        # Eliminar pendientes
        pendientes = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio,
            publicado=False
        )
        
        total_eliminadas = pendientes.count()
        
        if total_eliminadas > 0:
            logger.info(f"🗑️  Eliminando {total_eliminadas} publicaciones...")
            pendientes.delete()
            logger.info(f"✅ Eliminadas")
        
        # Marcar como no programado
        anuncio.publicaciones_programadas = False
        anuncio.save(update_fields=['publicaciones_programadas'])
        
        # Limpiar cache
        cache_key = f'ultimo_grupo_inicial_anuncio_{anuncio_id}'
        cache.delete(cache_key)
        
        # Reprogramar
        logger.info(f"\n{'▼'*40}\n")
        resultado = programar_anuncio_inteligente(anuncio_id)
        
        return resultado
    
    except Exception as e:
        logger.error(f"💥 Error: {e}", exc_info=True)
        return {
            'exitosa': False,
            'mensaje': str(e),
            'anuncio_id': anuncio_id
        }


def verificar_programacion(anuncio_id):
    """
    Verifica la programación de un anuncio
    """
    from publicadorFacebook.models import Anuncio, PublicacionGrupoFacebook
    
    logger.info(f"\n{'🔍'*40}")
    logger.info(f"🔍 VERIFICACIÓN DE PROGRAMACIÓN")
    logger.info(f"{'🔍'*40}\n")
    
    try:
        anuncio = Anuncio.objects.get(id=anuncio_id)
        
        publicaciones = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio,
            publicado=False
        ).order_by('fecha_programada').select_related('grupo')
        
        if not publicaciones.exists():
            logger.info("ℹ️  No hay publicaciones pendientes")
            return
        
        logger.info(f"📋 Anuncio: {anuncio.titulo}")
        logger.info(f"📊 Total: {publicaciones.count()}\n")
        
        active_time_start = getattr(anuncio, 'active_time_start', 9)
        active_time_end = getattr(anuncio, 'active_time_end', 21)
        
        pubs_lista = list(publicaciones)
        problemas = []
        
        for i, pub in enumerate(pubs_lista, 1):
            hora = pub.fecha_programada.hour
            
            icono = "✅" if (active_time_start <= hora < active_time_end) else "❌"
            
            logger.info(f"{icono} {i}. {pub.fecha_programada.strftime('%Y-%m-%d %H:%M')} - {pub.grupo.nombre}")
            
            if i > 1:
                anterior = pubs_lista[i-2]
                diferencia = pub.fecha_programada - anterior.fecha_programada
                horas = diferencia.total_seconds() / 3600
                logger.info(f"      Espaciado: {horas:.2f}h\n")
            
            if hora < active_time_start or hora >= active_time_end:
                problemas.append(f"Pub {i}: Fuera de horario")
        
        logger.info(f"{'='*60}")
        if problemas:
            logger.warning(f"⚠️  {len(problemas)} PROBLEMAS:")
            for p in problemas:
                logger.warning(f"   - {p}")
        else:
            logger.info(f"✅ TODO CORRECTO")
        logger.info(f"{'='*60}\n")
        
        return {'ok': len(problemas) == 0, 'problemas': problemas}
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return None