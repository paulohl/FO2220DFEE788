def iniciar_publicacion_en_grupo(announcement_id, usuario, contrasena, mensaje, grupo_url, imagen_ruta=None, grupo_urls=None, max_intentos=3):
    """
    🔥 FUNCIÓN PRINCIPAL - ULTRA ROBUSTA
    """
    
    print("\n" + "🚀"*40)
    print(f"🚀 NUEVA PUBLICACIÓN")
    print(f"📋 Anuncio: {announcement_id}")
    print(f"👤 Usuario: {usuario}")
    print(f"🎯 Grupo: {grupo_url}")
    print("🚀"*40 + "\n")
    
    if not grupo_url or not grupo_url.startswith('http'):
        print("❌ URL inválida")
        # en este punto no hay publicación posible
        return False
    
    # ---------------------------------------------------------
    # 🔥 PREPARACIÓN 1: IMAGEN ANTI-HASH
    # ---------------------------------------------------------
    ruta_imagen_final = None
    
    if imagen_ruta:
        # Resolver ruta absoluta si es relativa
        if not os.path.isabs(imagen_ruta) and not imagen_ruta.startswith('/'):
             imagen_ruta = os.path.join(default_storage.location, imagen_ruta)
    
    if imagen_ruta and os.path.exists(imagen_ruta):
        print(f"🖼️ Procesando imagen para Anti-Hash...")
        ruta_imagen_final = modificar_imagen_antihash(imagen_ruta)
    elif imagen_ruta:
        print(f"⚠️ Imagen no encontrada en ruta: {imagen_ruta}")
        imagen_ruta = None
    
    # ---------------------------------------------------------
    # 🔥 PREPARACIÓN 2: TEXTO POLIMÓRFICO
    # ---------------------------------------------------------
    print(f"✍️ Generando variación natural del texto...")
    mensaje_variado = aplicar_variacion_natural_automatica(mensaje)
    # FIRMA INVISIBLE DESACTIVADA
    texto_completo = mensaje_variado 
    
    print(f"📜 Texto final: {len(texto_completo)} caracteres")
    
    # Cargar cookies
    cache_key = f"facebook_user_cache_{usuario}"
    cookies = cache.get(cache_key, cargar_cookies_desde_json(f'cookies_{usuario}.json'))
    
    # Crear directorio de capturas si no existe
    os.makedirs('capturas', exist_ok=True)
    
    # Configuración
    config = obtener_configuracion_stealth()
    
    # Xvfb
    tiene_xvfb = detectar_xvfb()
    xvfb_process = None
    usar_headless = True
    
    if tiene_xvfb:
        xvfb_process = iniciar_xvfb()
        if xvfb_process:
            usar_headless = False
            print("✅ Xvfb activo - headless=False\n")
    
    intento_actual = 0
    resultado_final = False
    # 🔥 Seguimiento explícito del estado detectado
    estado_detectado = "DESCONOCIDO"
    
    try:
        with sync_playwright() as p:
            while intento_actual < max_intentos:
                browser = context = page = None
                estado_detectado = "DESCONOCIDO"
                
                try:
                    print(f"\n{'='*60}")
                    print(f"🔁 INTENTO {intento_actual + 1} de {max_intentos}")
                    print(f"{'='*60}\n")
                    
                    # Lanzar navegador
                    print(f"🌐 Navegador (headless={usar_headless})...")
                    browser = p.chromium.launch(
                        headless=usar_headless,
                        args=obtener_args_chromium_ultra_stealth()
                    )
                    
                    # Contexto
                    context = browser.new_context(
                        viewport=config['viewport'],
                        locale=config['locale'],
                        timezone_id=config['timezone'],
                        user_agent=config['user_agent']
                    )
                    
                    # Anti-detección
                    context.add_init_script("""
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}};
                        console.log('🛡️ Anti-detección activo');
                    """)
                    
                    # Cookies
                    if cookies and all(isinstance(c, dict) and 'name' in c for c in cookies):
                        try:
                            context.add_cookies(cookies)
                            print("✅ Cookies cargadas")
                        except Exception as e:
                            print(f"⚠️ Cookies warning: {e}")
                    
                    page = context.new_page()
                    
                    # LOGIN
                    print("\n🔐 Login...")
                    page.goto('https://www.facebook.com/login/', timeout=60000)
                    page.wait_for_load_state('networkidle', timeout=30000)
                    
                    if not verificar_inicio_sesion(page):
                        print("Login manual...")
                        
                        page.fill('input[name="email"]', usuario, timeout=15000)
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        page.fill('input[name="pass"]', contrasena, timeout=15000)
                        time.sleep(random.uniform(0.5, 1.0))
                        
                        if not hacer_clic_boton_login(page):
                            print("❌ Error en login")
                            intento_actual += 1
                            continue
                        
                        time.sleep(3)
                        page.wait_for_load_state('networkidle', timeout=30000)
                        
                        if verificar_inicio_sesion(page):
                            print("✅ Login exitoso, guardando cookies...")
                            cookies = context.cookies()
                            cache.set(cache_key, cookies, timeout=60 * 60 * 24)
                            try:
                                with open(f'cookies_{usuario}.json', 'w') as file:
                                    json.dump(cookies, file)
                            except Exception:
                                pass
                        else:
                            print("❌ Login fallido")
                            intento_actual += 1
                            continue
                    
                    # Navegar al grupo
                    print(f"\n🔎 Navegando al grupo...")
                    page.goto(grupo_url, timeout=60000)
                    page.wait_for_load_state('networkidle', timeout=30000)
                    esperar_tiempo_aleatorio(2, 3)
                    
                    # 📸 CAPTURA PASO 1
                    try:
                        page.screenshot(path="capturas/paso1_grupo.png") 
                    except Exception:
                        pass
                    
                    # Interacciones avanzadas
                    interacciones_aleatorias_avanzadas(page)
                    
                    # Abrir cuadro
                    print("\n📝 PASO 2: Abriendo cuadro...")
                    
                    cuadro_abierto = False
                    selectores_iniciar = [
                        'div[role="button"]:has-text("¿Qué estás pensando")',
                        'div[role="button"]:has-text("Escribe algo")',
                        'span:has-text("Escribe algo")'
                    ]
                    
                    for selector in selectores_iniciar:
                        try:
                            if page.locator(selector).count() > 0:
                                page.click(selector, timeout=8000)
                                cuadro_abierto = True
                                print(f"✅ Cuadro abierto (selector: {selector})")
                                break
                        except Exception:
                            continue
                    
                    if not cuadro_abierto:
                        # Intento tecla 'p'
                        page.keyboard.press('p')
                        time.sleep(2)
                        if page.locator('div[role="dialog"]').count() > 0:
                            cuadro_abierto = True
                            print(f"✅ Cuadro abierto (tecla P)")
                        else:
                            raise Exception("No se pudo abrir cuadro de publicación")
                    
                    esperar_tiempo_aleatorio(2, 3)
                    # 📸 CAPTURA PASO 2
                    try:
                        page.screenshot(path="capturas/paso2_cuadro.png")
                    except Exception:
                        pass
                    
                    # 🔥 INSERCIÓN ULTRA ROBUSTA
                    print("\n✍️ PASO 3: Insertando texto (ultra robusto)...")
                    
                    selectores_texto = [
                        'div[role="dialog"] div[contenteditable="true"]',
                        'div[role="dialog"] div[aria-label*="públicas"]',
                        'div[role="dialog"] p[data-placeholder]'
                    ]
                    
                    texto_insertado = False
                    for selector in selectores_texto:
                        try:
                            if page.locator(selector).count() > 0:
                                print(f"\n🎯 Usando selector: {selector}")
                                insertar_texto_ultra_robusto(page, selector, texto_completo)
                                texto_insertado = True
                                break
                        except Exception as e:
                            print(f"⚠️ Falló con selector {selector}: {e}")
                            continue
                    
                    if not texto_insertado:
                        raise Exception("No se pudo insertar texto con ningún selector")
                    
                    # 📸 CAPTURA PASO 3
                    try:
                        page.screenshot(path="capturas/paso3_texto.png")
                    except Exception:
                        pass
                    esperar_tiempo_aleatorio(2, 3)
                    
                    # Subir imagen
                    if ruta_imagen_final:
                        print(f"\n🖼️ PASO 4: Subiendo imagen única...")
                        
                        try:
                            page.click('div[role="dialog"] div[aria-label="Foto/vídeo"]', timeout=10000)
                        except Exception:
                            # A veces es un icono
                            try:
                                page.locator("div[aria-label='Foto/vídeo']").first.click()
                            except Exception:
                                pass
                        
                        esperar_tiempo_aleatorio(2, 3)
                        
                        inputs = page.locator('div[role="dialog"] input[type="file"]')
                        if inputs.count() > 0:
                            inputs.first.set_input_files(ruta_imagen_final)
                            print("✅ Imagen subida")
                        else:
                            raise Exception("No se pudo subir imagen (input no encontrado)")
                        
                        # 📸 CAPTURA PASO 4
                        try:
                            page.screenshot(path="capturas/paso4_imagen.png")
                        except Exception:
                            pass
                        esperar_tiempo_aleatorio(3, 5)
                    
                    # Publicar
                    print("\n📤 PASO 5: Publicando...")
                    
                    print("⏳ Esperando habilitación del botón...")
                    esperar_tiempo_aleatorio(3, 6)  # Aumentado
                    
                    publicado = False
                    try:
                        page.click('div[aria-label="Publicar"]:not([aria-disabled="true"])', timeout=15000)
                        publicado = True
                        print("✅ Click en Publicar")
                    except Exception:
                        try:
                            page.click('div[role="button"]:has-text("Publicar")', timeout=10000)
                            publicado = True
                            print("✅ Click en Publicar (alt)")
                        except Exception:
                            pass
                    
                    if not publicado:
                        raise Exception("No se pudo hacer click en 'Publicar'")
                    
                    # ---------------------------------------------------------
                    # 🔥 VERIFICACIÓN POST-PUBLICACIÓN (CRÍTICO)
                    # ---------------------------------------------------------
                    print("\n👀 Verificando estado de publicación...")
                    esperar_tiempo_aleatorio(5, 8)  # Esperar a que procese
                    
                    # inicializamos por si algo falla dentro del try
                    estado_detectado = "DESCONOCIDO"
                    
                    try:
                        # 1. Buscar indicadores de ÉXITO
                        indicadores_exito = [
                            'text="Hace un momento"', 
                            'text="Just now"',                
                        ]
                        
                        for ind in indicadores_exito:
                            if page.locator(ind).count() > 0:
                                estado_detectado = "PUBLICADO"
                                print(f"✅ Detectado indicador de éxito: {ind}")
                                break
                        
                        # 2. Buscar indicadores de PENDIENTE
                        if estado_detectado == "DESCONOCIDO":
                            indicadores_pendiente = [
                                'text="Tu publicación se ha enviado"',
                                'text="Your post has been submitted"',
                                'text="Pendiente"',
                                'text="Pending"',
                                'text="administrador debe aprobar"'
                            ]
                            for ind in indicadores_pendiente:
                                if page.locator(ind).count() > 0:
                                    estado_detectado = "PENDIENTE"
                                    print(f"⚠️ Detectado indicador de pendiente: {ind}")
                                    break
                                    
                        # 3. Verificar si seguimos en el cuadro (posible fallo)
                        if estado_detectado == "DESCONOCIDO":
                            if page.locator('div[role="dialog"]').count() > 0:
                                print("❌ Seguimos en el cuadro de diálogo tras intentar publicar")
                                if page.locator('text="No se pudo publicar"').count() > 0:
                                    raise Exception("Facebook rechazó la publicación explícitamente")
                    
                    except Exception as e:
                        print(f"⚠️ Error verificando estado: {e}")
                    
                    print(f"📊 ESTADO FINAL DETECTADO: {estado_detectado}")
                    # 🔎 Línea de diagnóstico por grupo
                    print(f"[DEBUG] Grupo={grupo_url} → estado_detectado={estado_detectado}")
                    
                    # 📸 CAPTURA PASO 5 (Estado Final)
                    try:
                        page.screenshot(path=f"capturas/paso5_estado_{estado_detectado}.png")
                    except Exception:
                        pass
                    
                    # Registrar actividad (independiente del estado)
                    usuario_hash = hashlib.md5(usuario.encode()).hexdigest()[:8]
                    gestor_suspension.registrar_actividad(usuario_hash, grupo_url)
                    
                    # 🔥 Aquí decidimos si consideramos la publicación como "ok"
                    # Variante suave: ok si al menos llegó a PUBLICADO o PENDIENTE
                    if estado_detectado in ("PUBLICADO", "PENDIENTE"):
                        resultado_final = True
                    else:
                        resultado_final = False
                    
                    print(f"[DEBUG] Resultado final interno: grupo={grupo_url}, ok={resultado_final}, estado={estado_detectado}")
                    
                    print("\n" + "✅"*40)
                    print("✅ PUBLICACIÓN COMPLETADA (según lógica interna)")
                    print("✅"*40 + "\n")
                    
                    break  # salimos del while de intentos
                
                except Exception as e:
                    print(f"\n❌ ERROR INTENTO {intento_actual + 1}: {e}")
                    
                    if page:
                        try:
                            page.screenshot(path=f"capturas/error_{intento_actual + 1}_{int(time.time())}.png")
                        except Exception:
                            pass
                    
                    intento_actual += 1
                    
                    if intento_actual >= max_intentos:
                        print(f"\n❌ MÁXIMO DE INTENTOS ({max_intentos})")
                        break
                    
                    delay = random.uniform(5, 10)
                    print(f"\n⏳ Reintentando en {delay:.1f}s...")
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
        # 🧹 LIMPIEZA DE ARCHIVOS TEMPORALES (CRÍTICO)
        if ruta_imagen_final and ruta_imagen_final != imagen_ruta:
            try:
                if os.path.exists(ruta_imagen_final):
                    os.remove(ruta_imagen_final)
                    print("🧹 Imagen temporal eliminada correctamente")
            except Exception:
                pass
            
        if xvfb_process:
            try:
                xvfb_process.terminate()
                xvfb_process.wait(timeout=5)
                print("✅ Xvfb cerrado")
            except Exception:
                try:
                    xvfb_process.kill()
                except Exception:
                    pass
    
    # 🔚 Punto único de salida con trazas claras
    print(f"[DEBUG] Retorno final desde iniciar_publicacion_en_grupo: ok={resultado_final}, estado={estado_detectado}, grupo={grupo_url}")
    return resultado_final
