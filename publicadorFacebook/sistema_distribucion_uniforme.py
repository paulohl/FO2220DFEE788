# -*- coding: utf-8 -*-
"""
🎯 SISTEMA DEFINITIVO - Distribución Uniforme Basada en Total de Publicaciones

FUNCIONAMIENTO:
1. Lee total_de_publicaciones del anuncio (ej: 10, 50, 100)
2. Calcula: espaciado = (días_vigencia × horas_disponibles) / total_publicaciones
3. Distribuye uniformemente en todo el período
4. Rota grupos disponibles
5. Respeta horarios estrictos
"""

from django.utils import timezone
from datetime import timedelta
import random
import logging

logger = logging.getLogger(__name__)


def obtener_grupos_rotados_simple():
    """
    Obtiene grupos en orden aleatorio
    """
    from publicadorFacebook.models import GrupoFacebook
    
    grupos = list(GrupoFacebook.objects.filter(activo=True).order_by('?'))
    random.shuffle(grupos)
    return grupos


def calcular_parametros_distribucion_uniforme(anuncio):
    """
    Calcula parámetros para distribución uniforme basada en total_de_publicaciones
    
    Returns:
        dict con parámetros calculados
    """
    
    logger.info(f"\n{'🔢'*40}")
    logger.info(f"🔢 CÁLCULO DE DISTRIBUCIÓN UNIFORME")
    logger.info(f"{'🔢'*40}\n")
    
    # Obtener horarios
    active_time_start = getattr(anuncio, 'active_time_start', 9)
    active_time_end = getattr(anuncio, 'active_time_end', 21)
    horas_disponibles_dia = active_time_end - active_time_start
    
    logger.info(f"⏰ HORARIOS:")
    logger.info(f"   active_time_start: {active_time_start}:00")
    logger.info(f"   active_time_end: {active_time_end}:00")
    logger.info(f"   → Rango válido: {active_time_start}:00 - {active_time_end-1}:59")
    logger.info(f"   → Horas disponibles/día: {horas_disponibles_dia} horas")
    
    # Calcular días de vigencia
    dias_vigencia = None
    
    if hasattr(anuncio, 'fecha_fin') and anuncio.fecha_fin:
        fecha_inicio = getattr(anuncio, 'fecha_inicio', None) or getattr(anuncio, 'fecha_creacion', timezone.now())
        dias_vigencia = (anuncio.fecha_fin - fecha_inicio).days
        if dias_vigencia <= 0:
            dias_vigencia = 30
        logger.info(f"\n📅 VIGENCIA:")
        logger.info(f"   Desde: {fecha_inicio.strftime('%Y-%m-%d')}")
        logger.info(f"   Hasta: {anuncio.fecha_fin.strftime('%Y-%m-%d')}")
        logger.info(f"   → Total días: {dias_vigencia}")
    elif hasattr(anuncio, 'dias_activo') and anuncio.dias_activo:
        dias_vigencia = anuncio.dias_activo
        logger.info(f"\n📅 VIGENCIA:")
        logger.info(f"   → Días configurados: {dias_vigencia}")
    else:
        dias_vigencia = 30
        logger.info(f"\n📅 VIGENCIA (default):")
        logger.info(f"   → Días por defecto: {dias_vigencia}")
    
    # CRÍTICO: Leer total_de_publicaciones configurado
    total_publicaciones = None
    
    # Probar diferentes nombres de campo
    for campo in ['total_de_publicaciones', 'total_publicaciones', 'publicaciones_totales']:
        if hasattr(anuncio, campo):
            total_publicaciones = getattr(anuncio, campo)
            if total_publicaciones and total_publicaciones > 0:
                logger.info(f"\n📊 TOTAL DE PUBLICACIONES:")
                logger.info(f"   Campo: {campo}")
                logger.info(f"   → Total configurado: {total_publicaciones} publicaciones")
                break
    
    if not total_publicaciones or total_publicaciones <= 0:
        # Default: 1 publicación por grupo disponible
        from publicadorFacebook.models import GrupoFacebook
        total_grupos = GrupoFacebook.objects.filter(activo=True).count()
        total_publicaciones = total_grupos if total_grupos > 0 else 10
        logger.info(f"\n📊 TOTAL DE PUBLICACIONES (default):")
        logger.info(f"   → Usando número de grupos: {total_publicaciones}")
    
    # CÁLCULO CLAVE: Tiempo total disponible
    tiempo_total_horas = dias_vigencia * horas_disponibles_dia
    
    logger.info(f"\n⏱️  TIEMPO TOTAL DISPONIBLE:")
    logger.info(f"   Fórmula: {dias_vigencia} días × {horas_disponibles_dia} horas/día")
    logger.info(f"   → Total: {tiempo_total_horas} horas disponibles")
    
    # ESPACIADO INTELIGENTE: Distribuir uniformemente
    espaciado_horas = tiempo_total_horas / total_publicaciones
    espaciado_minutos = espaciado_horas * 60
    
    logger.info(f"\n🎯 ESPACIADO CALCULADO:")
    logger.info(f"   Fórmula: {tiempo_total_horas}h totales ÷ {total_publicaciones} publicaciones")
    logger.info(f"   → Espaciado: {espaciado_horas:.2f} horas ({espaciado_minutos:.0f} minutos)")
    logger.info(f"   → Cada publicación cada ~{espaciado_horas/24:.1f} días")
    
    # Validar que sea factible
    if espaciado_horas < 1:
        logger.warning(f"⚠️  Espaciado muy pequeño ({espaciado_horas:.2f}h)")
        logger.warning(f"   Considerar reducir total_publicaciones o aumentar vigencia")
    
    logger.info(f"{'🔢'*40}\n")
    
    return {
        'dias_vigencia': dias_vigencia,
        'active_time_start': active_time_start,
        'active_time_end': active_time_end,
        'horas_disponibles_dia': horas_disponibles_dia,
        'total_publicaciones': total_publicaciones,
        'tiempo_total_horas': tiempo_total_horas,
        'espaciado_horas': espaciado_horas,
        'espaciado_minutos': espaciado_minutos
    }


def programar_distribucion_uniforme(anuncio_id):
    """
    🎯 PROGRAMADOR CON DISTRIBUCIÓN UNIFORME
    
    Lee total_de_publicaciones del anuncio y distribuye uniformemente
    en todo el período de vigencia
    
    Returns:
        dict con resultado
    """
    from publicadorFacebook.models import Anuncio, PublicacionGrupoFacebook
    
    logger.info(f"\n{'='*80}")
    logger.info(f"🎯 PROGRAMADOR CON DISTRIBUCIÓN UNIFORME")
    logger.info(f"{'='*80}\n")
    
    try:
        # Obtener anuncio
        anuncio = Anuncio.objects.get(id=anuncio_id)
        
        logger.info(f"📋 Anuncio: {anuncio.titulo}")
        logger.info(f"   ID: {anuncio.id}")
        
        # Calcular parámetros
        params = calcular_parametros_distribucion_uniforme(anuncio)
        
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
                        logger.info(f"\n👥 Usuarios: {usuarios.count()} activos")
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
        
        # Obtener grupos (rotarán durante las publicaciones)
        grupos_disponibles = obtener_grupos_rotados_simple()
        
        if not grupos_disponibles:
            logger.error("❌ No hay grupos activos")
            return {
                'exitosa': False,
                'mensaje': 'No hay grupos activos',
                'anuncio_id': anuncio_id
            }
        
        logger.info(f"\n📊 GRUPOS DISPONIBLES: {len(grupos_disponibles)}")
        logger.info(f"   Se rotarán durante las {params['total_publicaciones']} publicaciones")
        
        # Calcular fecha de inicio
        ultima_pub = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio
        ).order_by('-fecha_programada').first()
        
        if ultima_pub and ultima_pub.fecha_programada > timezone.now():
            fecha_actual = ultima_pub.fecha_programada
            logger.info(f"\n📅 Fecha inicio: {fecha_actual.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"   (continúa desde última programación)")
        else:
            ahora = timezone.now()
            
            if ahora.hour >= params['active_time_end']:
                fecha_actual = ahora.replace(
                    hour=params['active_time_start'],
                    minute=0,
                    second=0,
                    microsecond=0
                ) + timedelta(days=1)
            elif ahora.hour < params['active_time_start']:
                fecha_actual = ahora.replace(
                    hour=params['active_time_start'],
                    minute=0,
                    second=0,
                    microsecond=0
                )
            else:
                fecha_actual = ahora.replace(
                    minute=0,
                    second=0,
                    microsecond=0
                )
            
            logger.info(f"\n📅 Fecha inicio: {fecha_actual.strftime('%Y-%m-%d %H:%M')}")
        
        # CREAR PUBLICACIONES CON DISTRIBUCIÓN UNIFORME
        logger.info(f"\n{'📊'*40}")
        logger.info(f"📊 CREANDO {params['total_publicaciones']} PUBLICACIONES")
        logger.info(f"   Espaciadas cada {params['espaciado_horas']:.2f} horas")
        logger.info(f"{'📊'*40}\n")
        
        publicaciones_creadas = []
        
        for i in range(params['total_publicaciones']):
            # Seleccionar grupo (rotando)
            grupo = grupos_disponibles[i % len(grupos_disponibles)]
            
            # Seleccionar usuario
            usuario = random.choice(list(usuarios))
            
            # Calcular fecha programada
            # Para i=0: fecha_actual
            # Para i>0: fecha_actual + (i × espaciado)
            fecha_programada = fecha_actual + timedelta(hours=params['espaciado_horas'] * i)
            
            # AJUSTAR SI ESTÁ FUERA DE HORARIO
            while fecha_programada.hour < params['active_time_start'] or fecha_programada.hour >= params['active_time_end']:
                if fecha_programada.hour >= params['active_time_end']:
                    # Muy tarde → mover al día siguiente, hora de inicio
                    dias_adelante = 1
                    fecha_programada = fecha_programada.replace(
                        hour=params['active_time_start'],
                        minute=random.randint(0, 59),
                        second=0,
                        microsecond=0
                    ) + timedelta(days=dias_adelante)
                elif fecha_programada.hour < params['active_time_start']:
                    # Muy temprano → mismo día, hora de inicio
                    fecha_programada = fecha_programada.replace(
                        hour=params['active_time_start'],
                        minute=random.randint(0, 59),
                        second=0,
                        microsecond=0
                    )
            
            # Crear publicación
            pub = PublicacionGrupoFacebook.objects.create(
                anuncio=anuncio,
                grupo=grupo,
                usuario_facebook=usuario,
                fecha_programada=fecha_programada,
                publicado=False
            )
            
            publicaciones_creadas.append({
                'numero': i + 1,
                'grupo': grupo.nombre,
                'fecha': fecha_programada
            })
            
            logger.info(f"✅ Publicación {i+1}/{params['total_publicaciones']}")
            logger.info(f"   Grupo: {grupo.nombre}")
            logger.info(f"   Fecha: {fecha_programada.strftime('%Y-%m-%d %H:%M')}")
            logger.info(f"   Usuario: {usuario.email}")
            
            if i > 0:
                anterior = publicaciones_creadas[i-1]
                diferencia = fecha_programada - anterior['fecha']
                horas_dif = diferencia.total_seconds() / 3600
                dias_dif = diferencia.days
                logger.info(f"   Espaciado: {horas_dif:.2f}h (~{dias_dif} días) desde anterior")
            
            logger.info("")
        
        # Marcar como programado
        anuncio.publicaciones_programadas = True
        anuncio.save(update_fields=['publicaciones_programadas'])
        
        # Resumen
        logger.info(f"{'='*80}")
        logger.info(f"✅ PROGRAMACIÓN COMPLETADA")
        logger.info(f"{'='*80}")
        logger.info(f"📊 Publicaciones creadas: {len(publicaciones_creadas)}")
        logger.info(f"📅 Período: {params['dias_vigencia']} días")
        logger.info(f"⏱️  Espaciado: {params['espaciado_horas']:.2f} horas (~cada {params['espaciado_horas']/24:.1f} días)")
        logger.info(f"🔀 Grupos: Rotando entre {len(grupos_disponibles)} disponibles")
        logger.info(f"📅 Primera: {publicaciones_creadas[0]['fecha'].strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"📅 Última: {publicaciones_creadas[-1]['fecha'].strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"{'='*80}\n")
        
        return {
            'exitosa': True,
            'mensaje': 'Distribución uniforme completada',
            'anuncio_id': anuncio_id,
            'publicaciones_creadas': len(publicaciones_creadas),
            'parametros': params,
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


def limpiar_y_reprogramar_uniforme(anuncio_id):
    """
    Limpia y reprograma con distribución uniforme
    """
    from publicadorFacebook.models import Anuncio, PublicacionGrupoFacebook
    
    logger.info(f"\n{'🔄'*40}")
    logger.info(f"🔄 LIMPIEZA Y REPROGRAMACIÓN UNIFORME")
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
            logger.info(f"✅ Eliminadas\n")
        
        # Marcar como no programado
        anuncio.publicaciones_programadas = False
        anuncio.save(update_fields=['publicaciones_programadas'])
        
        # Reprogramar
        resultado = programar_distribucion_uniforme(anuncio_id)
        
        return resultado
    
    except Exception as e:
        logger.error(f"💥 Error: {e}", exc_info=True)
        return {
            'exitosa': False,
            'mensaje': str(e),
            'anuncio_id': anuncio_id
        }


def verificar_distribucion(anuncio_id):
    """
    Verifica la distribución uniforme
    """
    from publicadorFacebook.models import Anuncio, PublicacionGrupoFacebook
    
    logger.info(f"\n{'🔍'*40}")
    logger.info(f"🔍 VERIFICACIÓN DE DISTRIBUCIÓN")
    logger.info(f"{'🔍'*40}\n")
    
    try:
        anuncio = Anuncio.objects.get(id=anuncio_id)
        
        publicaciones = PublicacionGrupoFacebook.objects.filter(
            anuncio=anuncio,
            publicado=False
        ).order_by('fecha_programada')
        
        if not publicaciones.exists():
            logger.info("ℹ️  No hay publicaciones pendientes")
            return
        
        logger.info(f"📋 Anuncio: {anuncio.titulo}")
        logger.info(f"📊 Total publicaciones: {publicaciones.count()}\n")
        
        pubs_lista = list(publicaciones)
        
        # Mostrar primeras 10
        for i, pub in enumerate(pubs_lista[:10], 1):
            logger.info(f"✅ {i}. {pub.fecha_programada.strftime('%Y-%m-%d %H:%M')} - {pub.grupo.nombre}")
            
            if i > 1:
                anterior = pubs_lista[i-2]
                diferencia = pub.fecha_programada - anterior.fecha_programada
                horas = diferencia.total_seconds() / 3600
                dias = diferencia.days
                logger.info(f"      Espaciado: {horas:.2f}h (~{dias} días)\n")
        
        if len(pubs_lista) > 10:
            logger.info(f"... y {len(pubs_lista) - 10} más\n")
        
        logger.info(f"{'='*60}\n")
        
    except Exception as e:
        logger.error(f"Error: {e}")