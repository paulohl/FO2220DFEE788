#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🔄 SCRIPT: Reprogramar todas las publicaciones fuera de horario

USO:
    docker cp reprogramar_publicaciones.py facebook_144_ultima_version-web-1:/app/
    docker exec -it facebook_144_ultima_version-web-1 python /app/reprogramar_publicaciones.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, '/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tuProyecto.settings')  # Cambiar 'tuProyecto' por tu proyecto
django.setup()

from publicadorFacebook.models import PublicacionGrupoFacebook, Anuncio
from datetime import timedelta
import random

def reprogramar_todas():
    """
    Reprograma TODAS las publicaciones pendientes que estén fuera de horario
    """
    
    print("\n" + "="*80)
    print("🔄 REPROGRAMACIÓN MASIVA DE PUBLICACIONES")
    print("="*80 + "\n")
    
    # Obtener todas las publicaciones pendientes
    pendientes = PublicacionGrupoFacebook.objects.filter(
        publicado=False
    ).select_related('anuncio', 'grupo')
    
    total = pendientes.count()
    
    if total == 0:
        print("ℹ️  No hay publicaciones pendientes")
        return
    
    print(f"📊 Total de publicaciones pendientes: {total}\n")
    
    reprogramadas = 0
    sin_cambios = 0
    errores = 0
    
    for i, pub in enumerate(pendientes, 1):
        try:
            anuncio = pub.anuncio
            
            if not anuncio:
                print(f"⚠️  Publicación {pub.id} sin anuncio asociado - Saltando")
                errores += 1
                continue
            
            # Obtener horarios
            active_start = getattr(anuncio, 'active_time_start', 0)
            active_end = getattr(anuncio, 'active_time_end', 23)
            
            fecha_original = pub.fecha_programada
            hora = fecha_original.hour
            
            # Verificar si está fuera de rango
            if hora < active_start or hora >= active_end:
                print(f"\n[{i}/{total}] ❌ Fuera de rango:")
                print(f"   Anuncio: {anuncio.titulo}")
                print(f"   Grupo: {pub.grupo.nombre}")
                print(f"   Hora original: {fecha_original.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Horario permitido: {active_start}:00 - {active_end}:00")
                
                # Ajustar según el caso
                if hora >= active_end:
                    # Muy tarde → día siguiente
                    nueva_fecha = fecha_original.replace(
                        hour=active_start,
                        minute=random.randint(0, 59),
                        second=0,
                        microsecond=0
                    ) + timedelta(days=1)
                else:
                    # Muy temprano → mismo día
                    nueva_fecha = fecha_original.replace(
                        hour=active_start,
                        minute=random.randint(0, 59),
                        second=0,
                        microsecond=0
                    )
                
                # Guardar
                pub.fecha_programada = nueva_fecha
                pub.save(update_fields=['fecha_programada'])
                
                print(f"   ✅ Reprogramada: {nueva_fecha.strftime('%Y-%m-%d %H:%M:%S')}")
                reprogramadas += 1
            else:
                print(f"[{i}/{total}] ✅ OK: {pub.grupo.nombre} → {fecha_original.strftime('%H:%M')}")
                sin_cambios += 1
        
        except Exception as e:
            print(f"❌ Error con publicación {pub.id}: {e}")
            errores += 1
    
    # Resumen
    print("\n" + "="*80)
    print("✅ REPROGRAMACIÓN COMPLETADA")
    print("="*80)
    print(f"📊 Total revisadas: {total}")
    print(f"🔄 Reprogramadas: {reprogramadas}")
    print(f"✅ Sin cambios: {sin_cambios}")
    print(f"❌ Errores: {errores}")
    print("="*80 + "\n")
    
    # Verificación final
    if reprogramadas > 0:
        print("🔍 Verificación final...")
        verificar_horarios()

def verificar_horarios():
    """
    Verifica que todas las publicaciones pendientes estén en horario
    """
    pendientes = PublicacionGrupoFacebook.objects.filter(
        publicado=False
    ).select_related('anuncio')
    
    fuera_rango = 0
    
    for pub in pendientes:
        anuncio = pub.anuncio
        if not anuncio:
            continue
        
        active_start = getattr(anuncio, 'active_time_start', 0)
        active_end = getattr(anuncio, 'active_time_end', 23)
        hora = pub.fecha_programada.hour
        
        if hora < active_start or hora >= active_end:
            fuera_rango += 1
    
    if fuera_rango == 0:
        print("✅ Todas las publicaciones están dentro de horario")
    else:
        print(f"⚠️  Todavía hay {fuera_rango} publicaciones fuera de horario")
    
    print()

if __name__ == '__main__':
    try:
        reprogramar_todas()
    except Exception as e:
        print(f"\n💥 ERROR FATAL: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
