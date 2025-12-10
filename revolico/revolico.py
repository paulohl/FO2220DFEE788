# revolico.py
from playwright.sync_api import sync_playwright

def publish_ad(ad_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto('https://www.revolico.com/')

            # Aquí debes reemplazar los selectores con los adecuados para tu formulario de publicación
            page.click('selector_del_boton_de_publicar')
            page.fill('selector_del_campo_de_texto', ad_url)
            page.click('selector_del_boton_de_enviar')

            # Espera a que se complete la publicación (ajusta el selector según sea necesario)
            page.wait_for_selector('selector_de_confirmacion_de_publicacion')

            print("Publicación exitosa.")
        except Exception as e:
            print(f"Error al publicar el anuncio: {e}")
        finally:
            browser.close()
