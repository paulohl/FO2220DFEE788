# Patch: Timezone Cuba (America/Havana) + log visible
# Apply manually to your playwright_utils.py

1) Add (near imports):

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

PUBLICATION_TZ = "America/Havana"

def now_publication_tz() -> datetime:
    if ZoneInfo:
        return datetime.now(ZoneInfo(PUBLICATION_TZ))
    return datetime.now()

2) In obtener_configuracion_stealth(), set:
'timezone': PUBLICATION_TZ

3) Wherever you use datetime.now() for daily keys / stats, replace with:
now_publication_tz()

4) After config = obtener_configuracion_stealth() in iniciar_publicacion_en_grupo(), add:
logger.info(f"🕒 Publication timezone configured: {config.get('timezone')}")

5) Ensure Playwright context uses:
timezone_id=config['timezone']
