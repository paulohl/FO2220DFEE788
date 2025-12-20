# -*- coding: utf-8 -*-
"""
playwright_utils.py
Archivo autocontenido (single-file) para publicar en grupos de Facebook usando Playwright.
Incluye:
- Timezone Cuba (America/Havana)
- Wrapper ejecutar_publicacion_facebook para evitar ImportError en Celery
- Ritmo humano (pausas + micro-tiempos)
- Verificación post-publicación basada en "Tu contenido" (Publicado/Pendiente)
"""

import os
import re
import io
import json
import time
import random
import hashlib
import traceback
import subprocess
from dataclasses import dataclass
from typing import Optional, Tuple

from playwright.sync_api import sync_playwright

# Django imports (si el proyecto los tiene; si no, el módulo sigue cargando)
try:
    from django.core.cache import cache
except Exception:  # pragma: no cover
    cache = None

try:
    from django.core.files.storage import default_storage
except Exception:  # pragma: no cover
    default_storage = None


# ==========================================================
# Configuración principal
# ==========================================================

TIMEZONE_ID = "America/Havana"  # Cuba
LOCALE = "es-ES"

CAPTURAS_DIR = "capturas"
os.makedirs(CAPTURAS_DIR, exist_ok=True)


# ==========================================================
# Fallback / stubs (si tu proyecto tiene un gestor real, lo importará)
# ==========================================================

@dataclass
class _GestorSuspensionFallback:
    def registrar_actividad(self, usuario_hash: str, grupo_url: str) -> None:
        # En el proyecto real esto suele registrar actividad por usuario/grupo
        return


try:
    # Si existe en tu repo, úsalo. Si no, fallback.
    from publicadorFacebook.suspension_manager import gestor_suspension  # type: ignore
except Exception:  # pragma: no cover
    gestor_suspension = _GestorSuspensionFallback()


# ==========================================================
# Utilidades generales
# ==========================================================

def esperar_tiempo_aleatorio(a: float, b: float) -> None:
    time.sleep(random.uniform(a, b))


def _safe_print(msg: str) -> None:
    try:
        print(msg)
    except Exception:
        pass


def cargar_cookies_desde_json(path: str):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        if isinstance(cookies, list):
            return cookies
    except Exception:
        return None
    return None


def obtener_configuracion_stealth() -> dict:
    # User-Agent razonable (puedes ajustar si tu proyecto ya lo maneja)
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
    return {
        "viewport": {"width": 1366, "height": 768},
        "locale": LOCALE,
        "timezone": TIMEZONE_ID,
        "user_agent": ua,
    }


def obtener_args_chromium_ultra_stealth() -> list:
    # Set de args típicos para reducir señales de automatización
    return [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-infobars",
        "--disable-notifications",
        "--disable-gpu",
        "--lang=es-ES,es",
    ]


# ==========================================================
# Xvfb (opcional, para servidores Linux sin display)
# ==========================================================

def detectar_xvfb() -> bool:
    try:
        subprocess.check_output(["which", "Xvfb"])
        return True
    except Exception:
        return False


def iniciar_xvfb(display=":99", screen="0", resolution="1920x1080x24"):
    try:
        proc = subprocess.Popen(
            ["Xvfb", display, "-screen", screen, resolution],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.environ["DISPLAY"] = display
        return proc
    except Exception:
        return None


# ==========================================================
# “Humanización” básica: scroll + hesitación + ritmo total
# ==========================================================

def scroll_como_humano(page, px_min=200, px_max=600):
    try:
        px = random.randint(px_min, px_max)
        page.mouse.wheel(0, px)
        esperar_tiempo_aleatorio(0.4, 1.2)
    except Exception:
        pass


def interacciones_aleatorias_avanzadas(page):
    # Mantener mínimo: scroll y pequeñas pausas.
    # (Evita “ruido” excesivo que puede empeorar filtros)
    try:
        _safe_print("✅ Interacciones aleatorias...")
        if random.random() < 0.8:
            scroll_como_humano(page, 180, 420)
        if random.random() < 0.5:
            esperar_tiempo_aleatorio(0.8, 1.8)
    except Exception:
        pass


# ==========================================================
# Texto + Imagen (anti-hash simple)
# ==========================================================

def aplicar_variacion_natural_automatica(texto: str) -> str:
    # Variación muy suave: espacios/linebreaks. Evita “spintax agresivo”.
    if not texto:
        return texto
    t = texto.strip()
    # Añade un salto de línea ocasional entre párrafos
    if "\n\n" not in t and len(t) > 120 and random.random() < 0.5:
        # Inserta un salto cerca del medio
        mid = len(t) // 2
        return t[:mid].rstrip() + "\n\n" + t[mid:].lstrip()
    return t


def modificar_imagen_antihash(imagen_path: str) -> str:
    """
    Anti-hash minimalista:
    - copia el archivo a un nombre temporal distinto
    - (Si quieres manipular píxeles, aquí iría PIL. Pero lo dejamos “safe/fast”).
    """
    try:
        base, ext = os.path.splitext(imagen_path)
        temp_path = f"{base}_tmp_{int(time.time())}{ext}"
        with open(imagen_path, "rb") as fsrc:
            data = fsrc.read()
        with open(temp_path, "wb") as fdst:
            fdst.write(data)
        return temp_path
    except Exception:
        return imagen_path


# ==========================================================
# Login helpers
# ==========================================================

def verificar_inicio_sesion(page) -> bool:
    # Indicadores típicos: barra superior + avatar/menu
    try:
        if page.locator('div[role="navigation"]').count() > 0:
            return True
        if page.locator('a[aria-label="Inicio"]').count() > 0:
            return True
        if page.locator('div[aria-label="Cuenta"]').count() > 0:
            return True
    except Exception:
        pass
    return False


def hacer_clic_boton_login(page) -> bool:
    try:
        # Botón clásico
        if page.locator('button[name="login"]').count() > 0:
            page.click('button[name="login"]', timeout=15000)
            return True
        # Alternativa
        if page.locator('button:has-text("Iniciar sesión")').count() > 0:
            page.click('button:has-text("Iniciar sesión")', timeout=15000)
            return True
    except Exception:
        return False
    return False


# ==========================================================
# Inserción de texto “robusta”
# ==========================================================

def insertar_texto_ultra_robusto(page, selector: str, texto: str) -> None:
    """
    Inserta texto con estrategia:
    - click focus
    - typing con delays
    """
    loc = page.locator(selector).first
    loc.click(timeout=10000)
    esperar_tiempo_aleatorio(0.4, 1.0)

    # Limpieza suave (CTRL+A + Backspace)
    try:
        page.keyboard.press("Control+A")
        esperar_tiempo_aleatorio(0.1, 0.3)
        page.keyboard.press("Backspace")
        esperar_tiempo_aleatorio(0.2, 0.6)
    except Exception:
        pass

    # Typing humano (con pequeños delays)
    # Nota: no exagerar; demasiado lento también es sospechoso.
    delay = random.uniform(25, 55)  # ms por tecla
    page.keyboard.type(texto, delay=delay)


# ==========================================================
# Verificación post-publicación basada en "Tu contenido"
# ==========================================================

def _group_my_content_urls(grupo_url: str) -> Tuple[str, str]:
    """
    Construye:
    - /my_posted_content
    - /my_pending_content
    Compatible con URLs tipo:
    https://www.facebook.com/groups/1480.../
    """
    g = grupo_url.rstrip("/")
    posted = f"{g}/my_posted_content"
    pending = f"{g}/my_pending_content"
    return posted, pending


def _encontrar_post_en_tu_contenido(page, texto_referencia: str) -> bool:
    """
    Busca un indicio del post más reciente:
    - "Hace un momento"
    - o un fragmento del texto (primeros ~60 chars normalizados)
    """
    ref = (texto_referencia or "").strip()
    ref_norm = re.sub(r"\s+", " ", ref)[:60].strip()

    # 1) “Hace un momento”
    try:
        if page.locator('text="Hace un momento"').count() > 0:
            return True
    except Exception:
        pass

    # 2) Fragmento del texto
    if ref_norm:
        try:
            # Busca por substring; Facebook a veces colapsa espacios
            if page.locator(f'text="{ref_norm}"').count() > 0:
                return True
        except Exception:
            # fallback: búsqueda más laxa
            try:
                # Playwright text selector partial (contains)
                if page.locator(f"text={ref_norm}").count() > 0:
                    return True
            except Exception:
                pass

    return False


def verificar_estado_por_tu_contenido(page, grupo_url: str, texto_publicado: str) -> str:
    """
    Navega a "Tu contenido" y clasifica:
    - PUBLICADO si aparece en /my_posted_content
    - PENDIENTE si aparece en /my_pending_content
    - DESCONOCIDO si no aparece en ninguna (puede ser eliminado o aún procesando)
    """
    posted_url, pending_url = _group_my_content_urls(grupo_url)

    # Importante: dar tiempo a que Facebook procese
    esperar_tiempo_aleatorio(4.5, 7.5)

    # 1) Revisar Publicado
    try:
        page.goto(posted_url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        esperar_tiempo_aleatorio(1.2, 2.4)

        try:
            page.screenshot(path=os.path.join(CAPTURAS_DIR, "tu_contenido_publicado.png"))
        except Exception:
            pass

        if _encontrar_post_en_tu_contenido(page, texto_publicado):
            return "PUBLICADO"
    except Exception:
        pass

    # 2) Revisar Pendiente
    try:
        page.goto(pending_url, timeout=60000)
        page.wait_for_load_state("networkidle", timeout=30000)
        esperar_tiempo_aleatorio(1.2, 2.4)

        try:
            page.screenshot(path=os.path.join(CAPTURAS_DIR, "tu_contenido_pendiente.png"))
        except Exception:
            pass

        if _encontrar_post_en_tu_contenido(page, texto_publicado):
            return "PENDIENTE"
    except Exception:
        pass

    return "DESCONOCIDO"


# ==========================================================
# Wrapper para Celery (evita ImportError)
# ==========================================================

def ejecutar_publicacion_facebook(*args, **kwargs):
    """
    Wrapper tolerante:
    Celery suele importar ejecutar_publicacion_facebook desde playwright_utils.
    Este wrapper delega a iniciar_publicacion_en_grupo con kwargs flexibles.
    """
    return iniciar_publicacion_en_grupo(*args, **kwargs)


# ==========================================================
# FUNCIÓN PRINCIPAL
# ==========================================================

def iniciar_publicacion_en_grupo(
    announcement_id,
    usuario,
    contrasena,
    mensaje,
    grupo_url,
    imagen_ruta=None,
    grupo_urls=None,
    max_intentos=3,
):
    """
    FUNCIÓN PRINCIPAL - ULTRA ROBUSTA
    """

    _safe_print("\n" + "🚀" * 40)
    _safe_print("🚀 NUEVA PUBLICACIÓN")
    _safe_print(f"📋 Anuncio: {announcement_id}")
    _safe_print(f"👤 Usuario: {usuario}")
    _safe_print(f"🎯 Grupo: {grupo_url}")
    _safe_print("🚀" * 40 + "\n")

    if not grupo_url or not str(grupo_url).startswith("http"):
        _safe_print("❌ URL inválida")
        return False

    # ---------------------------------------------------------
    # PREPARACIÓN 1: IMAGEN ANTI-HASH
    # ---------------------------------------------------------
    ruta_imagen_final = None
    imagen_original = imagen_ruta

    if imagen_ruta and default_storage and not os.path.isabs(imagen_ruta) and not str(imagen_ruta).startswith("/"):
        try:
            imagen_ruta = os.path.join(default_storage.location, imagen_ruta)
        except Exception:
            pass

    if imagen_ruta and os.path.exists(imagen_ruta):
        _safe_print("🖼️ Procesando imagen para Anti-Hash...")
        ruta_imagen_final = modificar_imagen_antihash(imagen_ruta)
    elif imagen_ruta:
        _safe_print(f"⚠️ Imagen no encontrada en ruta: {imagen_ruta}")
        imagen_ruta = None

    # ---------------------------------------------------------
    # PREPARACIÓN 2: TEXTO POLIMÓRFICO (SUAVE)
    # ---------------------------------------------------------
    _safe_print("✍️ Generando variación natural del texto...")
    mensaje_variado = aplicar_variacion_natural_automatica(mensaje)
    texto_completo = mensaje_variado
    _safe_print(f"📜 Texto final: {len(texto_completo)} caracteres")

    # Cookies
    cache_key = f"facebook_user_cache_{usuario}"
    cookies = None
    try:
        if cache:
            cookies = cache.get(cache_key)
    except Exception:
        cookies = None

    if not cookies:
        cookies = cargar_cookies_desde_json(f"cookies_{usuario}.json")

    config = obtener_configuracion_stealth()

    # Xvfb
    tiene_xvfb = detectar_xvfb()
    xvfb_process = None
    usar_headless = True
    if tiene_xvfb:
        xvfb_process = iniciar_xvfb()
        if xvfb_process:
            usar_headless = False
            _safe_print("✅ Xvfb activo - headless=False\n")

    intento_actual = 0
    resultado_final = False
    estado_detectado = "DESCONOCIDO"

    # Para ritmo humano total por intento
    # (Publicación manual típica: 10–30s según Yariel)
    tiempo_objetivo_min = 12
    tiempo_objetivo_max = 28

    try:
        with sync_playwright() as p:
            while intento_actual < max_intentos:
                browser = context = page = None
                inicio_intento = time.time()

                try:
                    _safe_print("\n" + "=" * 60)
                    _safe_print(f"🔁 INTENTO {intento_actual + 1} de {max_intentos}")
                    _safe_print("=" * 60 + "\n")

                    # Navegador
                    _safe_print(f"🌐 Navegador (headless={usar_headless})...")
                    browser = p.chromium.launch(
                        headless=usar_headless,
                        args=obtener_args_chromium_ultra_stealth(),
                    )

                    context = browser.new_context(
                        viewport=config["viewport"],
                        locale=config["locale"],
                        timezone_id=config["timezone"],  # Cuba
                        user_agent=config["user_agent"],
                    )

                    # Anti-detección básica
                    context.add_init_script(
                        """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}};
                        """
                    )

                    # Cookies
                    if cookies and isinstance(cookies, list):
                        try:
                            context.add_cookies(cookies)
                            _safe_print("✅ Cookies cargadas")
                        except Exception as e:
                            _safe_print(f"⚠️ Cookies warning: {e}")

                    page = context.new_page()

                    # LOGIN
                    _safe_print("\n🔐 Login...")
                    page.goto("https://www.facebook.com/login/", timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=30000)

                    if not verificar_inicio_sesion(page):
                        _safe_print("Login manual...")

                        page.fill('input[name="email"]', usuario, timeout=15000)
                        esperar_tiempo_aleatorio(0.6, 1.1)

                        page.fill('input[name="pass"]', contrasena, timeout=15000)
                        esperar_tiempo_aleatorio(0.6, 1.1)

                        if not hacer_clic_boton_login(page):
                            raise Exception("No se pudo hacer clic en botón de login")

                        esperar_tiempo_aleatorio(2.8, 4.2)
                        page.wait_for_load_state("networkidle", timeout=30000)

                        if verificar_inicio_sesion(page):
                            _safe_print("✅ Login exitoso, guardando cookies...")
                            try:
                                cookies = context.cookies()
                                if cache:
                                    cache.set(cache_key, cookies, timeout=60 * 60 * 24)
                                with open(f"cookies_{usuario}.json", "w", encoding="utf-8") as f:
                                    json.dump(cookies, f)
                            except Exception:
                                pass
                        else:
                            raise Exception("Login fallido (verificar credenciales / checkpoint)")

                    # Navegar al grupo
                    _safe_print("\n🔎 Navegando al grupo...")
                    page.goto(grupo_url, timeout=60000)
                    page.wait_for_load_state("networkidle", timeout=30000)
                    esperar_tiempo_aleatorio(1.8, 2.8)

                    try:
                        page.screenshot(path=os.path.join(CAPTURAS_DIR, "paso1_grupo.png"))
                    except Exception:
                        pass

                    interacciones_aleatorias_avanzadas(page)

                    # Abrir cuadro
                    _safe_print("\n📝 PASO 2: Abriendo cuadro...")
                    cuadro_abierto = False
                    selectores_iniciar = [
                        'div[role="button"]:has-text("¿Qué estás pensando")',
                        'div[role="button"]:has-text("Escribe algo")',
                        'span:has-text("Escribe algo")',
                    ]

                    for selector in selectores_iniciar:
                        try:
                            if page.locator(selector).count() > 0:
                                page.click(selector, timeout=8000)
                                cuadro_abierto = True
                                _safe_print(f"✅ Cuadro abierto (selector: {selector})")
                                break
                        except Exception:
                            continue

                    if not cuadro_abierto:
                        # Intento tecla 'p'
                        try:
                            page.keyboard.press("p")
                            esperar_tiempo_aleatorio(1.2, 2.0)
                            if page.locator('div[role="dialog"]').count() > 0:
                                cuadro_abierto = True
                                _safe_print("✅ Cuadro abierto (tecla P)")
                        except Exception:
                            pass

                    if not cuadro_abierto:
                        raise Exception("No se pudo abrir cuadro de publicación")

                    esperar_tiempo_aleatorio(1.5, 2.5)
                    try:
                        page.screenshot(path=os.path.join(CAPTURAS_DIR, "paso2_cuadro.png"))
                    except Exception:
                        pass

                    # Insertar texto
                    _safe_print("\n✍️ PASO 3: Insertando texto...")
                    selectores_texto = [
                        'div[role="dialog"] div[contenteditable="true"]',
                        'div[role="dialog"] div[aria-label*="publicas"]',
                        'div[role="dialog"] p[data-placeholder]',
                    ]

                    texto_insertado = False
                    for selector in selectores_texto:
                        try:
                            if page.locator(selector).count() > 0:
                                _safe_print(f"🎯 Usando selector: {selector}")
                                insertar_texto_ultra_robusto(page, selector, texto_completo)
                                texto_insertado = True
                                break
                        except Exception as e:
                            _safe_print(f"⚠️ Falló con selector {selector}: {e}")
                            continue

                    if not texto_insertado:
                        raise Exception("No se pudo insertar texto con ningún selector")

                    try:
                        page.screenshot(path=os.path.join(CAPTURAS_DIR, "paso3_texto.png"))
                    except Exception:
                        pass
                    esperar_tiempo_aleatorio(1.2, 2.0)

                    # Subir imagen
                    if ruta_imagen_final:
                        _safe_print("\n🖼️ PASO 4: Subiendo imagen...")
                        # Intentar botón Foto/vídeo
                        try:
                            if page.locator('div[role="dialog"] div[aria-label="Foto/vídeo"]').count() > 0:
                                page.click('div[role="dialog"] div[aria-label="Foto/vídeo"]', timeout=10000)
                            elif page.locator("div[aria-label='Foto/vídeo']").count() > 0:
                                page.locator("div[aria-label='Foto/vídeo']").first.click(timeout=10000)
                        except Exception:
                            pass

                        esperar_tiempo_aleatorio(1.8, 2.8)

                        inputs = page.locator('div[role="dialog"] input[type="file"]')
                        if inputs.count() > 0:
                            inputs.first.set_input_files(ruta_imagen_final)
                            _safe_print("✅ Imagen subida")
                        else:
                            raise Exception("No se pudo subir imagen (input file no encontrado)")

                        try:
                            page.screenshot(path=os.path.join(CAPTURAS_DIR, "paso4_imagen.png"))
                        except Exception:
                            pass

                        esperar_tiempo_aleatorio(2.8, 4.2)

                    # Publicar
                    _safe_print("\n📤 PASO 5: Publicando...")

                    # Hesitación humana antes del clic final
                    esperar_tiempo_aleatorio(2.5, 6.0)

                    publicado = False
                    try:
                        if page.locator('div[aria-label="Publicar"]:not([aria-disabled="true"])').count() > 0:
                            page.click('div[aria-label="Publicar"]:not([aria-disabled="true"])', timeout=15000)
                            publicado = True
                            _safe_print("✅ Click en Publicar")
                    except Exception:
                        publicado = False

                    if not publicado:
                        try:
                            if page.locator('div[role="button"]:has-text("Publicar")').count() > 0:
                                page.click('div[role="button"]:has-text("Publicar")', timeout=15000)
                                publicado = True
                                _safe_print("✅ Click en Publicar (alt)")
                        except Exception:
                            publicado = False

                    if not publicado:
                        raise Exception("No se pudo hacer click en 'Publicar'")

                    # Post-publicación: no cerrar rápido
                    esperar_tiempo_aleatorio(6.5, 11.0)
                    scroll_como_humano(page, 220, 520)

                    # Verificar estado real por "Tu contenido"
                    _safe_print("\n👀 Verificando estado real en 'Tu contenido'...")
                    estado_detectado = verificar_estado_por_tu_contenido(page, grupo_url, texto_completo)

                    _safe_print(f"📊 ESTADO FINAL DETECTADO: {estado_detectado}")
                    _safe_print(f"[DEBUG] Grupo={grupo_url} → estado_detectado={estado_detectado}")

                    try:
                        page.screenshot(path=os.path.join(CAPTURAS_DIR, f"paso5_estado_{estado_detectado}.png"))
                    except Exception:
                        pass

                    # Registrar actividad (independiente del estado)
                    usuario_hash = hashlib.md5(str(usuario).encode()).hexdigest()[:8]
                    try:
                        gestor_suspension.registrar_actividad(usuario_hash, grupo_url)
                    except Exception:
                        pass

                    # Criterio final: éxito si PUBLICADO o PENDIENTE (pendiente es real, no falso positivo)
                    resultado_final = estado_detectado in ("PUBLICADO", "PENDIENTE")

                    # Ritmo humano total por intento: fuerza un mínimo total
                    tiempo_objetivo = random.randint(tiempo_objetivo_min, tiempo_objetivo_max)
                    transcurrido = time.time() - inicio_intento
                    if transcurrido < tiempo_objetivo:
                        time.sleep(tiempo_objetivo - transcurrido)

                    _safe_print(f"[DEBUG] Retorno: ok={resultado_final}, estado={estado_detectado}")
                    break

                except Exception as e:
                    _safe_print(f"\n❌ ERROR INTENTO {intento_actual + 1}: {e}")
                    _safe_print(traceback.format_exc())

                    if page:
                        try:
                            page.screenshot(path=os.path.join(CAPTURAS_DIR, f"error_{intento_actual + 1}_{int(time.time())}.png"))
                        except Exception:
                            pass

                    intento_actual += 1
                    if intento_actual >= max_intentos:
                        _safe_print(f"\n❌ MÁXIMO DE INTENTOS ({max_intentos})")
                        break

                    delay = random.uniform(6, 12)
                    _safe_print(f"\n⏳ Reintentando en {delay:.1f}s...")
                    time.sleep(delay)

                finally:
                    try:
                        if context:
                            context.close()
                    except Exception:
                        pass
                    try:
                        if browser:
                            browser.close()
                    except Exception:
                        pass

    finally:
        # Limpieza de imagen temporal
        if ruta_imagen_final and imagen_original and ruta_imagen_final != imagen_original:
            try:
                if os.path.exists(ruta_imagen_final):
                    os.remove(ruta_imagen_final)
                    _safe_print("🧹 Imagen temporal eliminada correctamente")
            except Exception:
                pass

        if xvfb_process:
            try:
                xvfb_process.terminate()
                xvfb_process.wait(timeout=5)
                _safe_print("✅ Xvfb cerrado")
            except Exception:
                try:
                    xvfb_process.kill()
                except Exception:
                    pass

    _safe_print(f"[DEBUG] Retorno final: ok={resultado_final}, estado={estado_detectado}, grupo={grupo_url}")
    return resultado_final
