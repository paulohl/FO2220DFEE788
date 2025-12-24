# playwright_utils.py — Reference & Architecture Notes      

## Purpose       

This module automates __Facebook group posting__ using __Playwright (sync)_, while applying:      

- “stealth” browser settings (UA/viewport/locale/timezone),
- human-like interaction patterns (scrolling, reading, mouse movement, typing),
- anti-duplicate strategies for text and images,
- a post-publication verification step that checks “__Tu contenido__” inside the group.


The module is designed to run inside a Django + Celery environment (cookies cached via Django cache, and wrappers call Django models). 

playwright_utils_vXY.py      


## Key design decisions      


__1) “Human-like” behavior is implemented as *timing + interaction noise*__     

The code intentionally adds:       

- randomized delays before/after actions,
- scrolling/reading simulation,
- limited “random interactions” (likes/comments/profile visit),
- human typing with occasional “mistakes”.

This does not “bypass” Facebook moderation; it only reduces obvious automation patterns. 

playwright_utils_vXY.py      

__2) Cuba time is enforced at browser-context level__      

The Playwright context is created with:      

       timezone_id = 'America/Havana'      

So all JavaScript time perceived by the page (and many UI elements / scheduling views) aligns to Cuba time, even if the server is hosted elsewhere.      

playwright_utils_vXY.py

__3) Post verification uses the group’s “Tu contenido” pages__      

Instead of trusting UI toasts or feed signals, the code navigates to:      

- `.../my_pending_content` (Pendiente)
- `.../my_posted_content` (Publicado)

And decides status using signals like “Hace un momento / Just now” and/or a partial text match.       

playwright_utils_vXY.py

## Runtime Flow (High level)      

### Entry pints (Wrappers)      

These are called externally (Celery tasks / views / management command):     

- `ejecutar_publicacion_facebook(announcement_id, usuario_id, grupo_url)`
- `publicar_en_facebook(...)`
- `realizar_publicacion(...)`

They load Django models (`Anuncio`, `UsuarioFacebooko`, resolve image path, and then call the core function:      

      - iniciar_publicacion_en_grupo(...)      

playwright_utils_vXY.py

__Main function__: `iniciar_publicacion_en_grupo(...)`      


__Inputs__      

- `announcement_id`: ID of the ad (for logging / tracking)
- `usuario`, `contrasena`: Facebook credentials
- `mensaje`: post text
- `grupo_url`: group URL
- `imagen_ruta`: optional local path (Django media path)
- `max_intentos`: retry attempts inside this function

### Steps (in order)      

1. Validate group URL
- Must exist and start with http.
- Otherwise returns False.
2. Image anti-hash (optional)
- If image exists: modificar_imagen_antihash(imagen_ruta)
- Produces a temp .jpg that changes the file hash via tiny transformations (brightness/contrast/saturation/crop/pixels/quality). 
3. 
playwright_utils_FINAL_CUBA

Text polymorphism

aplicar_variacion_natural_automatica(mensaje)

Currently does “space variation” and light punctuation jitter.

Zero-width injection is present but disabled (safer). 

playwright_utils_FINAL_CUBA

Load cookies

Uses Django cache key: facebook_user_cache_<usuario>

Fallback: read cookies_<usuario>.json 

playwright_utils_FINAL_CUBA

Xvfb / Headless strategy

detectar_xvfb() then iniciar_xvfb() if available.

If Xvfb runs: headless=False; else headless=True. 

playwright_utils_FINAL_CUBA

Launch browser + context

p.chromium.launch(...args...)

browser.new_context(viewport, locale, timezone_id, user_agent)

Adds init script to unset navigator.webdriver etc.

Adds cookies if valid. 

playwright_utils_FINAL_CUBA

Login

Go to https://www.facebook.com/login/

If verificar_inicio_sesion(page) fails → do manual fill:

fill email

fill password

click login with hacer_clic_boton_login(page)

If success: save cookies to cache and to cookies_<usuario>.json. 

playwright_utils_FINAL_CUBA

Navigate to group

page.goto(grupo_url)

capture screenshot: capturas/paso1_grupo.png

run interacciones_aleatorias_avanzadas(page) to simulate normal browsing. 

playwright_utils_FINAL_CUBA

Open composer dialog

Tries several selectors like “¿Qué estás pensando?” / “Escribe algo”

If not found, tries pressing p

capture screenshot: capturas/paso2_cuadro.png 

playwright_utils_FINAL_CUBA

Insert text

Tries multiple selectors inside dialog.

Calls insertar_texto_ultra_robusto(page, selector, texto)

Currently prioritized method is “Human Typing Real”.

capture screenshot: capturas/paso3_texto.png 

playwright_utils_FINAL_CUBA

Upload image (optional)

Click “Foto/vídeo” and find input[type=file] inside dialog.

set_input_files(ruta_imagen_final)

capture screenshot: capturas/paso4_imagen.png 

playwright_utils_FINAL_CUBA

Click Publish

Clicks:

div[aria-label="Publicar"]:not([aria-disabled="true"])

fallback div[role="button"]:has-text("Publicar")

If both fail: raises exception. 

playwright_utils_FINAL_CUBA

Post-publication verification

Waits 6–10s to let FB process.

Quick detection for “pending” indicators (toast / text).

Then calls real verification:

verificar_estado_en_tu_contenido(page, grupo_url, texto_completo)

Takes screenshot:

capturas/paso5_estado_<ESTADO>.png 

playwright_utils_FINAL_CUBA

Return logic

estado_detectado can be: PUBLICADO, PENDIENTE, DESCONOCIDO

Current result behavior intentionally avoids failing the whole Celery job on “false negatives”:

If estado is Publicado/Pendiente → ok=True

Else → ok=True but state remains DESCONOCIDO (for review) 

playwright_utils_FINAL_CUBA

Cleanup

Close context/browser always.

Delete temp image file if created.

Stop Xvfb if started. 

playwright_utils_FINAL_CUBA

Module Components (by category)
A) Xvfb utilities

detectar_xvfb(): checks if Xvfb exists in path.

iniciar_xvfb(): starts Xvfb on :99, sets DISPLAY. 

playwright_utils_FINAL_CUBA

Why it exists: some servers behave better with a real display even when automated.

B) Anti-duplicate / anti-hash
aplicar_variacion_natural_automatica(texto)

Produces a visually identical variant:

occasional double spaces,

punctuation jitter (remove last period or add trailing space sometimes). 

playwright_utils_FINAL_CUBA

modificar_imagen_antihash(ruta_imagen)

Uses Pillow to:

normalize to RGB,

tiny brightness/contrast/saturation changes,

micro-crop 1–2px,

flip a few random pixels,

save with a random JPEG quality.
Outputs temp_hash_<timestamp>_<rand>.jpg. 

playwright_utils_FINAL_CUBA

Maintenance note: if Pillow isn’t installed, image anti-hash is skipped gracefully.

C) Human-behavior simulation

simular_escritura_humana_con_errores(...): types word-by-word with occasional typos/backspaces.

mover_mouse_humanamente(...): Bezier-like mouse curve with jitter.

scroll_como_humano(...): segmented scroll with occasional backscroll.

simular_lectura_post(...): waits based on word count / punctuation.

interacciones_aleatorias_avanzadas(page): reads a few posts, sometimes likes/comments/opens profiles. 

playwright_utils_FINAL_CUBA

Safety note: keep these conservative. Too much interaction can also look unnatural.

D) Text insertion system
verificar_texto_insertado(page, selector, texto)

Reads DOM content of the composer and checks if ~80% of expected length is present. 

playwright_utils_FINAL_CUBA

“Methods”

adaptador_humano_avanzado(...) uses human typing + verification.

metodo_1_fill_con_eventos(...) fill + dispatch input/change/keyup.

metodo_2_clipboard_paste(...) simulate paste-like input.

metodo_3_type_con_eventos(...) type line-by-line.

metodo_4_javascript_directo(...) set innerHTML and dispatch events (note: in this code it has True in JS which would be invalid if executed; currently it’s not used). 

playwright_utils_FINAL_CUBA

insertar_texto_ultra_robusto(...)

Orchestrates the chosen insertion strategy. Right now, only “Human Typing Real” is enabled. 

playwright_utils_FINAL_CUBA

E) Stealth configuration

obtener_configuracion_stealth()

random UA + viewport

locale es-ES

timezone America/Havana 

playwright_utils_FINAL_CUBA

obtener_args_chromium_ultra_stealth()

disables automation flags/features/extensions, etc. 

playwright_utils_FINAL_CUBA

F) Cookies + timing helpers

cargar_cookies_desde_json(filename)

esperar_tiempo_aleatorio(min, max) 

playwright_utils_FINAL_CUBA

G) Session status + login helpers

verificar_inicio_sesion(page): checks URL is FB and not login page.

hacer_clic_boton_login(page): tries a list of login button selectors. 

playwright_utils_FINAL_CUBA

H) Post-state verification (“Tu contenido”)
URL helpers

normalizar_grupo_base_url(grupo_url): strips query/fragment, ensures trailing /.

verificar_estado_en_tu_contenido(page, grupo_url, texto_publicado="")

Visits:

<group>/my_pending_content → if “recent” signal or partial text match → PENDIENTE

<group>/my_posted_content → if signal/match → PUBLICADO
Else → DESCONOCIDO

It also aborts a tab if Facebook displays “Este contenido no está disponible…”. 

playwright_utils_FINAL_CUBA

Important operational note: if FB shows “recency” on the page due to older posts or other noise, you may want to tighten matching later using a stronger “fingerprint” (e.g., first 10–15 words, or a stable unique marker that remains human-safe).

I) Anti-suspension tracker
GestorAntiSuspension

Tracks:

daily post counts by user,

last activity time,

recent pattern list.

Used by gestor_suspension.registrar_actividad(...). 

playwright_utils_FINAL_CUBA

obtener_estadisticas_suspension()

Returns a dict of today counts, last activity hours, pattern count, active users. 

playwright_utils_FINAL_CUBA

Known “gotchas” to document for the next maintainer

“DESCONOCIDO” does not necessarily mean failure
Facebook UI is inconsistent. The code may click publish successfully but fail to “prove” it via the verification screens.

Some groups block or expel users
That can trigger “contenido no disponible”, redirects, or access-denied variants. This is not fixable purely by selectors.

metodo_4_javascript_directo has JS literals
It uses True instead of true in JS event options; if you re-enable it, correct that first.

Timezone
Server IP is Germany; browser timezone is Cuba. This can look “odd” but is common: FB relies more on behavior/risk signals than raw timezone alone. If issues arise, the safer compromise is to keep Cuba timezone but make posting windows and pacing consistent and conservative.

