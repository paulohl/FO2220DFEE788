# tasks.py
from celery import shared_task
import asyncio
from playwright.async_api import async_playwright

@shared_task
def publish_ad(ad_url):
    asyncio.get_event_loop().run_until_complete(publish_ad_async(ad_url))


async def publish_ad_async(ad_url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto('https://www.revolico.com/')
                # Aquí debes reemplazar los selectores con los adecuados para tu formulario de publicación
                await page.click('selector_del_boton_de_publicar')
                await page.fill('selector_del_campo_de_texto', ad_url)
                await page.click('selector_del_boton_de_enviar')
                # Espera a que se complete la publicación (ajusta el selector según sea necesario)
                await page.wait_for_selector('selector_de_confirmacion_de_publicacion')
                #instance.status = 'published'
                #instance.save()
                print("Publicación exitosa.")
            except Exception as e:
                #instance.status = 'failed'
                #instance.save()
                print(f"Error al publicar el anuncio: {e}")
            finally:
                await browser.close()
    except Exception as e:
        print(f"Error en Playwright: {e}")
