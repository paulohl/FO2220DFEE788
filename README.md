# FO2220DFEE788
Facebook Posting Flow Optimization (Playwright + Django)       

# Walkthrough: What the script does 

1) __Receives a posting job__
- It’s called with: Facebook user credentials, a target group URL, the message text, and optionally an image path (plus an `announcement_id` for tracking/logging).

2) __Validates the group URL__
- If the URL is missing or not an `http...` link, it stops immediately and returns `False`.

3) __Prepares the image (optional)__
- If an image path was provided and exists, it creates a __temporary variant__ of the image (tiny harmless changes) to avoid uploading the exact same binary every time.
- If the image path is invalid/missing, it continues without an image.

4) __Prepares the text__
- It creates a __slightly varied__ version of the message text (small spacing/punctuation variations) so posts are not byte-identical every time.

5) __Loads session cookies (if available)__
- It tries to reuse cookies for that Facebook user from cache / JSON.
- This helps avoid repeated logins.

6) __Starts the browser__
- It launches Chromium using Playwright with “stealth-ish” flags (reduce automation fingerprints).
- If Xvfb is available, it can run with a virtual display (often more stable than pure headless).

7) __Creates a browser context with Cuba time__
- It sets locale and __timezone__ (America/Havana) in the browser context so the session behaves in Cuba time.

8) __Injects anti-detection script__
- It disables obvious automation markers like `navigator.webdriver` and sets a few “chrome-like” fields.

9) __Restores cookies into the session__
- If cookies exist and are valid, it loads them into the context.

10) __Opens Facebook and ensures the user is logged in__
- It goes to the Facebook login page.
- If it detects the session is already logged in, it continues.
- If not logged in, it fills email/password, clicks login, and if successful it __saves cookies__ for future runs.

11) __Navigates to the target Facebook group__
- It loads the group URL and waits for the page to settle.
- It takes an early screenshot for debugging.

12) __Performs light “human browsing” behavior__
- It scrolls, pauses, and performs a few safe interactions (the intent is to avoid a “teleport → post → leave” bot pattern).

13) __Opens the post composer__
- It tries multiple selectors (e.g., “¿Qué estás pensando?” / “Escribe algo”).
- If those fail, it tries a keyboard shortcut fallback.
- It takes a screenshot once the composer is open.

14) __Inserts the message text__
- It locates the `contenteditable` area inside the composer dialog.
- It types the message using a “human typing” method with realistic delays (and optionally minor mistakes).
- It verifies the text is present and takes a screenshot.

15) __Uploads the image (if provided)__      
- It clicks the “Photo/Video” UI and finds the file input inside the dialog.
- It uploads the temporary image file.
- It waits for the upload to settle and takes a screenshot.

15) __Clicks “Publish”__
- It waits a bit (human hesitation), then clicks the Publish button.
- If the primary selector fails, it tries a fallback selector.

17) __Waits briefly for Facebook to process the post__
- It pauses a few seconds so Facebook can accept the post and update UI.

18) __Verifies the result using “Tu contenido”__
- Instead of trusting “toast” messages or assumptions, it navigates to the group’s “__Tu contenido__” pages:
- checks __Pending__ page (Pendiente).
- checks __Posted__ page (Publicado).
- Based on what it finds, it sets `estado_detectado` to:
- `PUBLICADO`, or.
- `PENDIENTE`, or.
- `DESCONOCIDO` (couldn’t confirm either way).

19) __Captures a final screenshot__
- It saves `paso5_best_<ESTADO>` for evidence of what it detected

20) __Logs activity and returns__
- It records activity in the anti-suspension tracker.
- It returns a final boolean ok and logs the detected state.

21) __Cleans up__
- Closes Playwright context and browser.
- Deletes the temporary image file (if created).
- Stops Xvfb (if started).


# Walkthrough with functions and responsibilities
This section explains what happens, where, and why, using the real structure of the code.

### 1️⃣ Entry point: main publication flow
iniciar_publicacion_en_grupo(...)      

__Role__:       

This is the __orchestrator__. Nothing else publishes by itself.      
It controls retries, browser lifecycle, logging, and the final return value.     

__Responsibilities__:       

- Validate inputs
- Prepare text & image
- Launch browser + context
- Drive login → group → publish → verification
- Decide final `ok / estado_detectado`



### 2️⃣ Input validation
Inside `iniciar_publicacion_en_grupo`      

```
if not grupo_url or not grupo_url.startswith('http'):
    return False
```

__Why__:      

Fail fast. Prevents wasted browser sessions and confusing downstream errors.      


### 3️⃣ Image preparation (anti-hash)      
`modificar_imagen_antihash(imagen_ruta)`      

Called from:      
`iniciar_publicacion_en_grupo`       


__Role__:

- Creates a __temporary image variant__ (tiny pixel / metadata changes)      
- Avoids uploading byte-identical images repeatedly

__Lifecycle__:      

- Temporary file is created
- Used once
- Deleted in `finally` cleanup


### 4️⃣ Text preparation (polymorphism)
`aplicar_variacion_natural_automatica(mensaje)`      

__Role__:      

- Produces a semantically identical message
- With tiny harmless variations (spacing, punctuation, invisible changes)

__Why__:       

Prevents Facebook seeing identical payloads across posts.      


### 5️⃣ Cookie management      

`cargar_cookies_desde_json(...)`      

__Django__ `cache.get(...)` / `cache.set(...)`      

__Role__:      

- Restore previous login sessions
- Reduce repeated logins (major risk factor)

__Flow__:      

- Try cache
- Fallback to JSON
- Save cookies again after successful login


### 6️⃣ Stealth configuration      

`obtener_configuracion_stealth()`      

__Provides__:      

- `viewport`
- `locale`
- `timezone` → __America/Havana__
- `user_agent`

__Used in__:      

`context = browser.new_context(...)`      

__Why__:      

Ensures browser “lives” in Cuba time, regardless of server IP (Germany).      

      
### 7️⃣ Virtual display (Xvfb)      

      `detectar_xvfb()`      
 
      `iniciar_xvfb()`      

__Role__:      

- If available, runs Chromium non-headless inside virtual display
- More stable + closer to real browser behavior


### 8️⃣ Browser & context creation      

__Playwright core calls__      

      browser = p.chromium.launch(...)      
      context = browser.new_context(...)
      page = context.new_page()
     

__Plus anti-detection injection__:
      
      context.add_init_script(...)

__Purpose__:      

Remove obvious automation fingerprints `(navigator.webdriver)`      


### 9️⃣ Login verification & execution      

      verificar_inicio_sesion(page)      

      hacer_clic_boton_login(page)      


__Logic__:      

- If already logged in → continue
- Else:
- Fill email
- Fill password
- Click login
- Verify again
- Save cookies

__Key point__:       

Login logic is __idempotent and__ safe to entry.     


#### 🔟 Navigation to group       

      page.goto(grupo_url)      
      
__Followed by__:      

      - esperar_tiempo_aleatorio(...)      

      - page.screenshot(...)      

      
__Why screenshots exist__:      

Every major phase leaves forensic evidence      


#### 1️⃣1️⃣ Human interaction warm-up      

      interacciones_aleatorias_avanzadas(page)      
      
__Role__:      

- Scrolls
- Small pauses
- Light interactions

__Why__:      

Avoid “cold teleport → post → exit” pattern.      


#### 1️⃣2️⃣ Open post composer      

__Selectors tried in order__"     

- Buttons with “¿Qué estás pensando?”
- “Escribe algo”      
- Keyboard fallback (p)

__Failure here = hard stop__      
(no post possible).


#### 1️⃣3️⃣ Insert text (ultra-robust)      

      insertar_texto_ultra_robusto(page, selector, texto)      

__Behavior__:      

- Human typing simulation
- Random delays
- Optional micro-errors
- Verifies visible text count

__Why__:     

Direct `fill()` is risky and detectable      


#### 1️⃣4️⃣ Image upload      

__Flow__:      

- Click “Foto/Video”
- Find `<input type="file">`
- 'set_input_files(...)'
- Wait + screenshot

__Important__:      

Image upload is optional and isolated.    


#### 1️⃣5️⃣ Publish click
Two attempts:


Primary selector (aria-label="Publicar")


Fallback text-based selector


Includes:


Pre-click hesitation


Post-click pause



#### 1️⃣6️⃣ Post-publication verification (CRITICAL)
verificar_estado_en_tu_contenido(page, grupo_url, texto_completo)
This is the heart of the fix.
Steps:


Navigate to:


/my_pending_content


/my_posted_content




Look for:


“Hace un momento”


“Just now”


Partial text fingerprint




__Decide__:


PUBLICADO


PENDIENTE


DESCONOCIDO




Key design choice:


DESCONOCIDO ≠ failure


Avoids Celery repost loops



#### 1️⃣7️⃣ Result handling
Inside iniciar_publicacion_en_grupo:
if estado_detectado in ("PUBLICADO", "PENDIENTE"):
    resultado_final = True
else:
    resultado_final = False

Why:
Celery must not retry posts that likely succeeded.

#### 1️⃣8️⃣ Activity tracking
gestor_suspension.registrar_actividad(...)      

__Role__:


Tracks per-user / per-group activity


Helps avoid overposting patterns



#### 1️⃣9️⃣ Cleanup (always runs)
In `finally` blocks:      
- Close context
- Close browser
- Delete temp image
- Stop Xvfb

__No resource leaks__. __No ghost browsers__.

#### 2️⃣0️⃣ Single exit point      
```
return resultado_final
```

With full debug log:      
```
[DEBUG] Retorno final desde iniciar_publicacion_en_grupo
```


## Architecture Diagram - Why this is compliant

### System-level (components + data flow)      

```
flowchart LR
  U[Admin / Operator] -->|Creates Announcement + Schedule| DJ[Django Admin + DB]
  DJ -->|enqueue job| CQ[Celery Queue / Broker]
  CQ -->|execute task| CW[Celery Worker]
  CW -->|calls| PU[playwright_utils.py]

  subgraph PU[playwright_utils.py]
    P0[Input Validation]
    P1[Text Polymorphism\naplicar_variacion_natural_automatica]
    P2[Image Anti-Hash\nmodificar_imagen_antihash]
    P3[Cookie Load/Save\ncache + cookies_*.json]
    P4[Playwright Context\nstealth + locale + timezone=America/Havana]
    P5[Login Flow\nverificar_inicio_sesion + hacer_clic_boton_login]
    P6[Group Navigation\npage.goto(grupo_url)]
    P7[Composer + Typing\ninsertar_texto_ultra_robusto]
    P8[Upload Image\nset_input_files]
    P9[Publish Click\nprimary + fallback]
    P10[Verification via “Tu contenido”\nverificar_estado_en_tu_contenido]
    P11[Activity Tracking\ngestor_suspension.registrar_actividad]
    P12[Cleanup\nclose context/browser + delete temp image]
  end

  PU -->|state_detectado + ok| CW
  CW -->|update status| DJ
  P  PU -->|screenshots + logs| LOG[Capturas/Logs]

```

### Sequence (runtime steps)      

```

sequenceDiagram
  participant DJ as Django Admin/DB
  participant CQ as Celery Queue
  participant CW as Celery Worker
  participant PU as playwright_utils.py
  participant FB as Facebook (Web UI)

  DJ->>CQ: enqueue(programar_publicacion_task)
  CQ->>CW: deliver job
  CW->>PU: iniciar_publicacion_en_grupo(...)

  PU->>PU: validar grupo_url
  PU->>PU: aplicar_variacion_natural_automatica(texto)
  PU->>PU: modificar_imagen_antihash(imagen)
  PU->>PU: cargar cookies (cache/json)
  PU->>PU: crear browser/context (timezone=America/Havana)
  PU->>FB: goto /login
  PU->>FB: verificar_inicio_sesion / login si necesario
  PU->>FB: goto grupo_url
  PU->>FB: abrir composer + insertar texto + subir imagen
  PU->>FB: click Publicar
  PU->>FB: ir a /my_pending_content y /my_posted_content
  PU->>PU: estado_detectado = PUBLICADO|PENDIENTE|DESCONOCIDO
  PU->>PU: cleanup + screenshots
  PU-->>CW: return ok + estado_detectado
  CW-->>DJ: per  CW-->>DJ: persist res

```

1) ### Why this is compliant__” No bypassing / no “control” over Facebook  

This implementation does not attempt to circumvent Facebook’s moderation, review queues, or enforcement systems.      
It accepts that some groups will route posts to Pending, and it avoids any “guaranteed approval” claims because approval is controlled by Facebook and group admins—not by code.

2) ### Verification is “honest,” not evasive

The verification step checks the official UI outcome      
(“Tu contenido” → _Publicado / Pendiente_) rather than assuming success based on a click or a feed indicator.       
That reduces false positives and prevents automated retries that could look like spam.

3) ### Minimizes risk signals instead of exploiting vulnerabilities

The “human pacing” and stability measures are used to:      
- reduce brittle automation failures (timing/race conditions),
- keep behavior closer to normal interactive browsing,
- avoid hammering actions too quickly.

They are __not__ designed to defeat security controls or exploit vulnerabilities.

4) ### Data handling is limited and operationally necessary

The system stores only what it needs to operate:      

- session cookies for the configured accounts,
- screenshots/logs for debugging,
- nimal status outcomes per post attempt.

No attempt is made to harvest unrelated user data, scrape private content, or expand access beyond the authenticated account’s normal visibility.



5) ### Respectful execution patterns

Operationally, the design supports safer usage patterns:      
- rate limiting via pacing and activity tracking (gestor_suspension),
- retries are controlled, and DESCONOCIDO can be treated carefully to avoid repost storms,
- per-account distribution can reduce concentration risk (while still respecting platform rules).

6) ### Prefer official APIs when available

Where Meta provides supported APIs for a given publishing scenario, __the compliant path is to use the official API__. Browser automation is inherently fragile and policy-sensitive; this implementation is structured to remain conservative and observable, and to enable a future migration to official endpoints when feasible.
