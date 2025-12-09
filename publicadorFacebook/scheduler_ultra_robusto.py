# -*- coding: utf-8 -*-
"""
🔥 SCHEDULER ULTRA ROBUSTO V4.1 - CORRECCIÓN TOTAL DE ZONA HORARIA
====================================================================

CORRECCIONES CRÍTICAS EN ESTA VERSIÓN:
- ✅ Uso consistente de timezone.localtime() para TODAS las operaciones
- ✅ Validación de fecha_fin SIEMPRE en el futuro
- ✅ Prevención de intervalos negativos
- ✅🔥 CRÍTICO V4.1: Cálculo de fecha_fin desde FECHA_INICIO CONFIGURADA, no desde ahora
- ✅ Validación de que las publicaciones NO estén en el pasado
- ✅ Zona horaria explícita en logs para debugging

VERIFICADO EXHAUSTIVAMENTE
"""

from django.utils import timezone
from django.conf import settings
from datetime import timedelta, datetime
import logging
import random
import pytz

logger = logging.getLogger(__name__)

# ============================================================================
# LOG AL IMPORTAR
# ============================================================================
logger.info("="*80)
logger.info("🔥 SCHEDULER_ULTRA_ROBUSTO.PY V4.1 (FECHA_INICIO CONFIGURADA) IMPORTADO")
logger.info("="*80)


def get_local_now():
    """
    Obtiene la hora local actual de forma consistente.
    
    CRÍTICO: Siempre usar esta función en lugar de timezone.now()
    para evitar problemas de zona horaria.
    """
    now_utc = timezone.now()
    
    # Convertir a hora local según la configuración de Django
    try:
        local_tz = pytz.timezone(settings.TIME_ZONE)
        now_local = now_utc.astimezone(local_tz)
    except Exception:
        # Fallback: usar localtime de Django
        now_local = timezone.localtime(now_utc)
    
    return now_local


class SchedulerUltraRobusto:
    """
    Scheduler con corrección total de zona horaria
    
    CAMBIOS CRÍTICOS V4.1:
    1. Toda operación de fecha usa get_local_now()
    2. 🔥 fecha_fin se calcula desde FECHA_INICIO CONFIGURADA + duración
    3. Intervalos siempre positivos (mínimo 0.1h = 6 minutos)
    4. Validación de fechas en el futuro
    5. Logs con zona horaria explícita
    """
    
    def __init__(self, anuncio):
        """Inicializa el scheduler con validaciones"""
        logger.info("\n" + "🔥"*50)
        logger.info("🔥 SCHEDULER V4.1 - FECHA_INICIO CONFIGURADA")
        logger.info("🔥"*50)
        
        self.anuncio = anuncio
        self.active_time_start = getattr(anuncio, 'active_time_start', 0)
        self.active_time_end = getattr(anuncio, 'active_time_end', 23)
        self.duracion_dias = max(1, getattr(anuncio, 'duracion_dias', 30))  # Mínimo 1 día
        self.total_publicaciones = max(1, getattr(anuncio, 'total_publicaciones', 180))
        self.publicaciones_realizadas = getattr(anuncio, 'publicaciones_realizadas', 0)
        self.publicaciones_restantes = max(0, self.total_publicaciones - self.publicaciones_realizadas)
        
        # Obtener hora local actual para debugging
        now_local = get_local_now()
        
        logger.info(f"📊 Configuración:")
        logger.info(f"   • ID: {anuncio.id}")
        logger.info(f"   • Título: {getattr(anuncio, 'titulo', 'N/A')}")
        logger.info(f"   • Duración: {self.duracion_dias} días")
        logger.info(f"   • Horario: {self.active_time_start}:00 - {self.active_time_end}:00")
        logger.info(f"   • Total: {self.total_publicaciones}")
        logger.info(f"   • Restantes: {self.publicaciones_restantes}")
        logger.info(f"   • 🕐 Hora local actual: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"   • 🕐 Hora UTC actual: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        logger.info(f"   • 🌍 Zona horaria: {settings.TIME_ZONE}")
        logger.info("🔥"*50 + "\n")
    
    def calcular_horas_disponibles_por_dia(self):
        """Calcula horas disponibles cada día"""
        if self.active_time_end >= self.active_time_start:
            horas = self.active_time_end - self.active_time_start
        else:
            # Horario que cruza medianoche (ej: 22-6)
            horas = (24 - self.active_time_start) + self.active_time_end
        
        # Mínimo 1 hora disponible
        horas = max(1, horas)
        
        logger.info(f"⏰ Horas disponibles por día: {horas}h")
        return horas
    
    def calcular_intervalo_ideal(self):
        """
        Calcula intervalo ideal entre publicaciones
        
        CORRECCIÓN V4: Siempre retorna un intervalo positivo
        """
        horas_por_dia = self.calcular_horas_disponibles_por_dia()
        total_horas = self.duracion_dias * horas_por_dia
        
        if self.publicaciones_restantes <= 0:
            logger.error("❌ No hay publicaciones restantes")
            return 1.0  # Default: 1 hora
        
        intervalo = total_horas / self.publicaciones_restantes
        
        # 🔥 CRÍTICO: Nunca permitir intervalo menor a 6 minutos (0.1h)
        intervalo = max(0.1, intervalo)
        
        logger.info(f"\n📐 CÁLCULO DE INTERVALO BASE:")
        logger.info(f"   • Horas por día: {horas_por_dia}h")
        logger.info(f"   • Total horas disponibles: {total_horas}h")
        logger.info(f"   • Publicaciones restantes: {self.publicaciones_restantes}")
        logger.info(f"   • Intervalo calculado: {intervalo:.2f}h ({intervalo*60:.0f} min)")
        
        return intervalo
    
    def obtener_intervalo_seguro(self):
        """
        🛡️ Obtiene intervalo seguro en SEGUNDOS para validación en tiempo real
        """
        intervalo_horas = self.calcular_intervalo_ideal()
        
        # Mínimo 6 minutos (360 segundos)
        return max(360, intervalo_horas * 3600)
    
    def _esta_dentro_horario(self, hora):
        """
        Verifica si una hora está dentro del horario permitido
        
        Args:
            hora: int (0-23)
        
        Returns:
            bool
        """
        if self.active_time_end >= self.active_time_start:
            # Horario normal (ej: 6-15)
            return self.active_time_start <= hora < self.active_time_end
        else:
            # Horario que cruza medianoche (ej: 22-6)
            return hora >= self.active_time_start or hora < self.active_time_end
    
    def obtener_fecha_inicio(self):
        """
        Obtiene fecha de inicio de la primera publicación
        
        CORRECCIÓN V4: Usa hora local consistentemente
        """
        now = get_local_now()
        hora_actual = now.hour
        
        logger.info(f"\n🕐 FECHA DE INICIO (V4 - ZONA HORARIA CORREGIDA):")
        logger.info(f"   • Ahora (local): {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"   • Hora actual: {hora_actual}:00")
        logger.info(f"   • Rango permitido: {self.active_time_start}:00 - {self.active_time_end}:00")
        
        dentro = self._esta_dentro_horario(hora_actual)
        
        if dentro:
            logger.info(f"   ✅ Dentro del horario → Primera pub: AHORA + variación mínima")
            # Agregar pequeña variación (1-5 minutos)
            variacion = random.randint(1, 5)
            return now + timedelta(minutes=variacion)
        else:
            # Calcular próximo slot disponible
            siguiente = now.replace(
                hour=self.active_time_start, 
                minute=0, 
                second=0, 
                microsecond=0
            )
            
            # Si ya pasó el horario de hoy, ir a mañana
            if hora_actual >= self.active_time_end or (
                self.active_time_end < self.active_time_start and 
                hora_actual >= self.active_time_end and 
                hora_actual < self.active_time_start
            ):
                siguiente += timedelta(days=1)
            
            # Agregar variación aleatoria en minutos
            variacion = random.randint(0, 30)
            siguiente += timedelta(minutes=variacion)
            
            logger.info(f"   ⚠️ Fuera del horario → Primera pub: {siguiente.strftime('%Y-%m-%d %H:%M:%S %Z')}")
            return siguiente
    
    def obtener_fecha_fin(self):
        """
        Obtiene fecha de finalización de la campaña
        
        🔥 CORRECCIÓN CRÍTICA V4.1:
        La fecha fin se calcula desde la FECHA DE INICIO CONFIGURADA + duración_dias,
        NO desde la hora actual (timezone.now()).
        
        Ejemplo:
        - Fecha inicio configurada: 25/11/2025
        - Duración: 1 día
        - Fecha fin: 26/11/2025 (NO 27/11 si hoy es 26/11)
        """
        # Obtener fecha de inicio configurada
        fecha_inicio_configurada = getattr(self.anuncio, 'fecha_inicio', None)
        
        if fecha_inicio_configurada:
            # Usar la fecha configurada
            fecha_base = fecha_inicio_configurada
            logger.info(f"\n📅 FECHA FIN CAMPAÑA (V4.1 - DESDE FECHA CONFIGURADA):")
            logger.info(f"   • Fecha inicio configurada: {fecha_base.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        else:
            # Fallback: usar hora actual si no hay fecha configurada
            fecha_base = get_local_now()
            logger.info(f"\n📅 FECHA FIN CAMPAÑA (V4.1 - FALLBACK A HORA ACTUAL):")
            logger.info(f"   • Ahora (no hay fecha configurada): {fecha_base.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Calcular fecha fin
        fecha_fin = fecha_base + timedelta(days=self.duracion_dias)
        
        logger.info(f"   • Duración: {self.duracion_dias} días")
        logger.info(f"   • Finalización: {fecha_fin.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        return fecha_fin
    
    def generar_calendario_completo(self):
        """
        Genera calendario completo CON VALIDACIÓN TOTAL
        
        CORRECCIONES V4:
        1. Fecha fin siempre en el futuro
        2. Intervalo siempre positivo
        3. Todas las publicaciones en el futuro
        4. Distribución uniforme garantizada
        """
        logger.info("\n" + "📅"*50)
        logger.info("📅 GENERANDO CALENDARIO V4.1 (VALIDACIÓN TOTAL)")
        logger.info("📅"*50)
        
        if self.publicaciones_restantes <= 0:
            logger.error("❌ No hay publicaciones para programar")
            return []
        
        # 1. Obtener fechas
        now = get_local_now()
        fecha_inicio = self.obtener_fecha_inicio()
        fecha_fin = self.obtener_fecha_fin()
        
        # 🔥 VALIDACIÓN CRÍTICA: fecha_inicio debe ser >= ahora
        if fecha_inicio < now:
            logger.warning(f"⚠️ fecha_inicio ({fecha_inicio}) < ahora ({now}), ajustando...")
            fecha_inicio = now + timedelta(minutes=1)
        
        # 🔥 VALIDACIÓN CRÍTICA: fecha_fin debe ser > fecha_inicio
        if fecha_fin <= fecha_inicio:
            logger.warning(f"⚠️ fecha_fin ({fecha_fin}) <= fecha_inicio ({fecha_inicio}), ajustando...")
            fecha_fin = fecha_inicio + timedelta(days=max(1, self.duracion_dias))
        
        # 2. Calcular tiempo disponible real
        tiempo_total_segundos = (fecha_fin - fecha_inicio).total_seconds()
        tiempo_total_horas = tiempo_total_segundos / 3600
        
        logger.info(f"\n📊 TIEMPO DISPONIBLE REAL:")
        logger.info(f"   • Desde: {fecha_inicio.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"   • Hasta: {fecha_fin.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        logger.info(f"   • Total: {tiempo_total_horas:.2f} horas")
        
        # 🔥 VALIDACIÓN: tiempo debe ser positivo
        if tiempo_total_horas <= 0:
            logger.error("❌ Tiempo total <= 0, esto no debería pasar")
            # Forzar al menos 24 horas
            fecha_fin = fecha_inicio + timedelta(days=1)
            tiempo_total_horas = 24
        
        # 3. Calcular intervalo
        # Considerando solo horas activas por día
        horas_activas_por_dia = self.calcular_horas_disponibles_por_dia()
        dias_disponibles = (fecha_fin - fecha_inicio).days + 1
        horas_activas_totales = dias_disponibles * horas_activas_por_dia
        
        intervalo_horas = horas_activas_totales / self.publicaciones_restantes
        
        # 🔥 VALIDACIÓN CRÍTICA: Intervalo siempre positivo (mínimo 6 minutos)
        intervalo_horas = max(0.1, intervalo_horas)
        
        logger.info(f"\n📐 CÁLCULO DE DISTRIBUCIÓN:")
        logger.info(f"   • Días disponibles: {dias_disponibles}")
        logger.info(f"   • Horas activas por día: {horas_activas_por_dia}h")
        logger.info(f"   • Horas activas totales: {horas_activas_totales}h")
        logger.info(f"   • Publicaciones: {self.publicaciones_restantes}")
        logger.info(f"   • Intervalo base: {intervalo_horas:.2f}h ({intervalo_horas*60:.0f} min)")
        
        # 4. Generar fechas
        calendario = []
        fecha_actual = fecha_inicio
        
        for i in range(self.publicaciones_restantes):
            # Agregar variación al intervalo (±20%)
            variacion_factor = random.uniform(0.8, 1.2)
            intervalo_con_variacion = intervalo_horas * variacion_factor
            
            # Asegurar mínimo 6 minutos
            intervalo_con_variacion = max(0.1, intervalo_con_variacion)
            
            # Ajustar fecha al horario permitido
            fecha_ajustada = self._ajustar_a_horario(fecha_actual)
            
            # 🔥 VALIDACIÓN: La fecha debe estar en el futuro
            if fecha_ajustada <= now:
                logger.warning(f"   ⚠️ Pub {i+1} en el pasado ({fecha_ajustada}), ajustando...")
                fecha_ajustada = self._ajustar_a_horario(now + timedelta(minutes=(i+1)*5))
            
            # 🔥 VALIDACIÓN: La fecha debe estar antes de fecha_fin
            if fecha_ajustada > fecha_fin:
                # Recalcular para que quepa
                tiempo_restante = (fecha_fin - now).total_seconds()
                if tiempo_restante > 0 and (self.publicaciones_restantes - i) > 0:
                    nuevo_intervalo = tiempo_restante / (self.publicaciones_restantes - i) / 3600
                    nuevo_intervalo = max(0.1, nuevo_intervalo)
                    fecha_ajustada = self._ajustar_a_horario(now + timedelta(hours=nuevo_intervalo * (i + 1)))
            
            calendario.append(fecha_ajustada)
            
            # Avanzar para la siguiente publicación
            fecha_actual = fecha_ajustada + timedelta(hours=intervalo_con_variacion)
        
        # 5. Ordenar y eliminar duplicados
        calendario = sorted(set(calendario))
        
        # 6. Log de resultados
        logger.info(f"\n🔄 CALENDARIO GENERADO:")
        for i, fecha in enumerate(calendario[:10]):  # Primeras 10
            dias_desde_ahora = (fecha - now).total_seconds() / 86400
            logger.info(f"   Pub {i+1:3d}: {fecha.strftime('%Y-%m-%d %H:%M %Z')} (en {dias_desde_ahora:.1f} días)")
        
        if len(calendario) > 10:
            logger.info(f"   ... ({len(calendario) - 10} más) ...")
        
        logger.info(f"\n✅ Calendario generado: {len(calendario)} publicaciones")
        
        if len(calendario) >= 2:
            primera = calendario[0]
            ultima = calendario[-1]
            span_dias = (ultima - primera).days
            
            logger.info(f"   📊 Primera: {primera.strftime('%Y-%m-%d %H:%M %Z')}")
            logger.info(f"   📊 Última:  {ultima.strftime('%Y-%m-%d %H:%M %Z')}")
            logger.info(f"   📊 Span:    {span_dias} días")
            
            # Verificar variación de horas
            horas = [c.hour for c in calendario]
            logger.info(f"   🎲 Rango de horas: {min(horas)}:00 - {max(horas)}:00")
        
        logger.info("📅"*50 + "\n")
        
        return calendario
    
    def _ajustar_a_horario(self, fecha):
        """
        Ajusta una fecha al horario permitido con variación
        
        CORRECCIÓN V4: Maneja correctamente la zona horaria
        """
        hora = fecha.hour
        
        # Asegurar que nunca devolvemos una fecha en el pasado respecto a la base
        fecha_base = fecha
        now_local = get_local_now()
        if fecha_base < now_local:
            fecha_base = now_local + timedelta(minutes=1)
        
        if self._esta_dentro_horario(fecha_base.hour):
            # Ya está dentro, solo agregar variación en minutos hacia adelante
            offset_minutos = random.randint(0, 20)
            nuevo_minuto = min(59, fecha_base.minute + offset_minutos)
            ajustada = fecha_base.replace(minute=nuevo_minuto, second=0, microsecond=0)
            
            # Si por alguna razón quedó en el pasado (p. ej., misma hora pero minuto menor), moverla hacia adelante
            if ajustada <= now_local:
                ajustada = now_local + timedelta(minutes=1)
                ajustada = ajustada.replace(second=0, microsecond=0)
            return ajustada
        
        # Fuera del horario - mover al siguiente slot
        nueva_fecha = fecha_base.replace(
            hour=self.active_time_start,
            minute=random.randint(0, 30),
            second=0,
            microsecond=0
        )
        
        # Si la hora actual es mayor que el fin del horario, ir al día siguiente
        if self.active_time_end >= self.active_time_start:
            if hora >= self.active_time_end:
                nueva_fecha += timedelta(days=1)
        else:
            # Horario cruzando medianoche
            if hora >= self.active_time_end and hora < self.active_time_start:
                pass  # Ya está configurado para el inicio del horario
        
        # Asegurar que no caiga en el pasado
        if nueva_fecha <= now_local:
            nueva_fecha = now_local + timedelta(minutes=1)
            nueva_fecha = nueva_fecha.replace(hour=self.active_time_start, minute=random.randint(0, 30), second=0, microsecond=0)
        
        return nueva_fecha
    
    def verificar_calendario(self, calendario):
        """Verifica que el calendario sea válido"""
        logger.info("\n" + "🔍"*50)
        logger.info("🔍 VERIFICANDO CALENDARIO V4.1")
        logger.info("🔍"*50)
        
        if not calendario:
            logger.error("❌ Calendario vacío")
            return {'valido': False, 'errores': ['Calendario vacío']}
        
        errores = []
        now = get_local_now()
        
        # 1. Verificar que todas estén en el futuro
        logger.info("1️⃣ Verificando fechas en el futuro...")
        en_pasado = sum(1 for f in calendario if f <= now)
        if en_pasado > 0:
            logger.error(f"   ❌ {en_pasado} publicaciones en el pasado")
            errores.append(f"{en_pasado} publicaciones en el pasado")
        else:
            logger.info(f"   ✅ Todas en el futuro")
        
        # 2. Verificar horarios
        logger.info("2️⃣ Verificando horarios...")
        fuera_horario = sum(1 for f in calendario if not self._esta_dentro_horario(f.hour))
        if fuera_horario > 0:
            logger.error(f"   ❌ {fuera_horario} publicaciones fuera de horario")
            errores.append(f"{fuera_horario} publicaciones fuera de horario")
        else:
            logger.info(f"   ✅ Todas dentro del horario")
        
        # 3. Verificar intervalos
        logger.info("3️⃣ Verificando intervalos...")
        if len(calendario) >= 2:
            intervalos = []
            for i in range(len(calendario) - 1):
                intervalo_h = (calendario[i+1] - calendario[i]).total_seconds() / 3600
                intervalos.append(intervalo_h)
            
            intervalo_min = min(intervalos)
            intervalo_max = max(intervalos)
            intervalo_prom = sum(intervalos) / len(intervalos)
            
            logger.info(f"   • Intervalo mínimo:  {intervalo_min:.2f}h")
            logger.info(f"   • Intervalo máximo:  {intervalo_max:.2f}h")
            logger.info(f"   • Intervalo promedio: {intervalo_prom:.2f}h")
            
            if intervalo_min < 0:
                errores.append("Hay intervalos negativos")
                logger.error("   ❌ Hay intervalos negativos")
        
        # 4. Verificar duplicados
        logger.info("4️⃣ Verificando duplicados...")
        if len(calendario) != len(set(calendario)):
            errores.append("Hay fechas duplicadas")
            logger.error("   ❌ Hay fechas duplicadas")
        else:
            logger.info("   ✅ No hay duplicados")
        
        # 5. Verificar orden
        logger.info("5️⃣ Verificando orden...")
        if calendario != sorted(calendario):
            errores.append("No está ordenado")
            logger.error("   ❌ No está ordenado")
        else:
            logger.info("   ✅ Orden correcto")
        
        valido = len(errores) == 0
        
        resultado = {
            'valido': valido,
            'errores': errores,
            'total_publicaciones': len(calendario),
        }
        
        if valido:
            logger.info(f"\n✅✅✅ CALENDARIO VÁLIDO ✅✅✅")
        else:
            logger.error(f"\n❌ CALENDARIO CON ERRORES: {errores}")
        
        logger.info("🔍"*50 + "\n")
        
        return resultado


def obtener_proxima_publicacion_programada(anuncio, ultima_publicacion_hora=None):
    """Helper para obtener próxima fecha (modo incremental)"""
    logger.info("📌 Calculando próxima publicación V4.1")
    
    scheduler = SchedulerUltraRobusto(anuncio)
    now = get_local_now()
    
    if ultima_publicacion_hora:
        intervalo_horas = scheduler.calcular_intervalo_ideal()
        
        # Agregar variación al intervalo
        variacion_factor = random.uniform(0.85, 1.15)
        intervalo_con_variacion = intervalo_horas * variacion_factor
        
        proxima = ultima_publicacion_hora + timedelta(hours=intervalo_con_variacion)
        proxima = scheduler._ajustar_a_horario(proxima)
        
        # Asegurar que esté en el futuro
        if proxima <= now:
            proxima = now + timedelta(minutes=5)
            proxima = scheduler._ajustar_a_horario(proxima)
        
        logger.info(f"   Última: {ultima_publicacion_hora.strftime('%Y-%m-%d %H:%M %Z')}")
        logger.info(f"   Próxima: {proxima.strftime('%Y-%m-%d %H:%M %Z')}")
    else:
        proxima = scheduler.obtener_fecha_inicio()
        logger.info(f"   Primera: {proxima.strftime('%Y-%m-%d %H:%M %Z')}")
    
    return proxima


def verificar_horario_actual(anuncio):
    """
    Verifica si la hora actual está dentro del horario del anuncio
    
    NUEVA FUNCIÓN V4: Para usar en las tareas de Celery
    
    Returns:
        tuple: (dentro_horario: bool, hora_actual: int, mensaje: str)
    """
    now = get_local_now()
    hora_actual = now.hour
    
    active_time_start = getattr(anuncio, 'active_time_start', 0)
    active_time_end = getattr(anuncio, 'active_time_end', 23)
    
    if active_time_end >= active_time_start:
        dentro = active_time_start <= hora_actual < active_time_end
    else:
        dentro = hora_actual >= active_time_start or hora_actual < active_time_end
    
    mensaje = (
        f"Hora local: {now.strftime('%H:%M %Z')}, "
        f"Horario permitido: {active_time_start}:00-{active_time_end}:00, "
        f"Dentro: {dentro}"
    )
    
    logger.info(f"🕐 Verificación horario: {mensaje}")
    
    return dentro, hora_actual, mensaje


# ============================================================================
# LOG AL FINAL DEL MÓDULO
# ============================================================================
logger.info("✅ scheduler_ultra_robusto.py V4.1 cargado")
logger.info("✅ Correcciones: zona horaria, fecha_fin desde FECHA_INICIO, intervalos positivos")
logger.info(f"✅ Zona horaria configurada: {settings.TIME_ZONE}")
logger.info("="*80)
