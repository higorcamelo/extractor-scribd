# extractor.py

import os
import time
import base64
import requests
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager


def setup_driver():
    """
    Cria e retorna uma instância do Edge WebDriver em modo headless,
    necessária para executar o CDP (Chrome DevTools Protocol).
    """
    options = Options()
    options.add_argument("--headless")  # modo headless
    options.add_argument("--disable-gpu")
    # Para permitir usar Page.captureScreenshot, não colocamos nenhuma limitação de tamanho via window_size
    service = EdgeService(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.set_window_size(1920, 2000)  # tamanho “mínimo”; não importa muito, pois vamos “clipar” via CDP
    return driver


def scroll_page_smooth(driver, pause=0.2):
    """
    Faz um scroll suave do topo ao fim da página, pulando 500px a cada passo
    e aguardando `pause` segundos entre cada salto. Isso ativa o lazy loading
    de todas as páginas do Scribd.
    """
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    current = 0

    while current < scroll_height:
        driver.execute_script(f"window.scrollTo(0, {current});")
        current += 500
        time.sleep(pause)
        scroll_height = driver.execute_script("return document.body.scrollHeight")

    # Garante que role até o fim
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)  # aguarda um instante para carregar o final


def hardcore_block(driver):
    """
    Interrompe qualquer carregamento pendente e remove todos os <script> e modais conhecidos
    do Scribd (paywall, popups, etc.), para que eles não reapareçam.
    """
    driver.execute_script("window.stop();")
    driver.execute_script("""
        document.querySelectorAll('script').forEach(e => e.remove());
        document.querySelectorAll('.overlay, .modal, .paywall, .popup, .login-prompt, .container-overlay').forEach(e => e.remove());
    """)
    time.sleep(0.5)  # aguarda JS residual ser interrompido


def detect_document_type(url):
    """
    Abre o URL no Edge, limpa paywalls e faz scroll mínimo para renderizar.
    Retorna:
      - "text" se detectar pelo menos um <div class="text_layer">
      - "scan" se detectar pelo menos um <img class="absimg">
      - "unknown" caso contrário
    """
    driver = setup_driver()
    driver.get(url)

    hardcore_block(driver)
    scroll_page_smooth(driver, pause=0.2)

    time.sleep(1)  # dá tempo para renderizar

    has_text = driver.execute_script("return document.querySelectorAll('div.text_layer').length")
    has_images = driver.execute_script("return document.querySelectorAll('img.absimg').length")

    driver.quit()

    if has_text > 0:
        return "text"
    elif has_images > 0:
        return "scan"
    else:
        return "unknown"


def extract_images(url, output_folder):
    """
    Extrai as imagens (<img class="absimg">) de cada página do Scribd, salva em JPG
    dentro de output_folder e retorna a lista de caminhos completos desses arquivos.
    """
    driver = setup_driver()
    driver.get(url)

    hardcore_block(driver)
    scroll_page_smooth(driver)

    # Força cada página a ficar visível
    driver.execute_script("""
        document.querySelectorAll('div.outer_page_container > div[id^="outer_page_"]').forEach(c => c.scrollIntoView());
    """)
    time.sleep(1)

    document_container = driver.find_element(By.ID, "document_container")
    pages = document_container.find_elements(By.CSS_SELECTOR, "div.outer_page_container > div[id^='outer_page_']")

    img_urls = []
    for page_div in pages:
        imgs = page_div.find_elements(By.CSS_SELECTOR, "img.absimg")
        for img in imgs:
            src = img.get_attribute('src')
            if src and src.startswith("http"):
                img_urls.append(src)

    os.makedirs(output_folder, exist_ok=True)
    images = []
    for i, img_url in enumerate(img_urls):
        try:
            resp = requests.get(img_url, timeout=15)
            resp.raise_for_status()
            file_path = os.path.join(output_folder, f"page_{i+1:03}.jpg")
            with open(file_path, "wb") as f:
                f.write(resp.content)
            images.append(file_path)
            print(f"✅ Baixada página {i+1} de {len(img_urls)}")
        except Exception as e:
            print(f"❌ Erro ao baixar página {i+1}: {e}")

    driver.quit()
    return images


def extract_text(url):
    """
    Captura screenshots das páginas de livros com texto renderizado no Scribd,
    usando CDP para “clipar” exatamente a bounding‐box de cada elemento.
    Retorna lista de caminhos dos PNGs gerados.
    """
    driver = setup_driver()
    driver.get(url)

    hardcore_block(driver)
    scroll_page_smooth(driver, pause=0.2)

    # Remove banners, headers e elementos fixos incômodos
    driver.execute_script("""
        document.querySelectorAll(
            'div[class*="cookie"], div[class*="Cookie"], div[id*="cookie"], '
            + 'div[class*="privacy"], div[id*="privacy"], '
            + 'header, nav, .navbar, .site-header'
        ).forEach(e => e.remove());

        Array.from(document.querySelectorAll('body *')).forEach(el => {
            const style = window.getComputedStyle(el);
            if ((style.position === 'fixed' || style.position === 'sticky')
                && !el.closest('#document_container')) {
                el.remove();
            }
        });
    """)
    time.sleep(0.5)

    # Garante que cada página esteja visível para lazy load
    driver.execute_script("""
        document.querySelectorAll('div.outer_page_container > div[id^="outer_page_"]').forEach(c => c.scrollIntoView());
    """)
    time.sleep(0.5)

    document_container = driver.find_element(By.ID, "document_container")
    pages = document_container.find_elements(
        By.CSS_SELECTOR,
        "div.outer_page_container > div[id^='outer_page_']"
    )

    os.makedirs("output", exist_ok=True)
    screenshots = []
    total = len(pages)
    print(f"📄 Documento de texto com {total} páginas. Salvando screenshots via CDP...")

    for i, page_div in enumerate(pages):
        # 1) Medir a bounding‐box: x, y, width, height (pixels reais)
        bbox = page_div.rect
        x = int(bbox['x'])
        y = int(bbox['y'])
        width = int(bbox['width'])
        height = int(bbox['height'])

        # 2) ScrollIntoView (para garantir que o elemento não esteja parcialmente fora de tela)
        driver.execute_script("arguments[0].scrollIntoView({block: 'start'});", page_div)
        time.sleep(0.1)

        # 3) Montar objeto “clip” para CDP, sem margem de zoom (scale = 1)
        clip = {
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "scale": 1
        }

        # 4) Invocar Page.captureScreenshot via CDP
        result = driver.execute_cdp_cmd("Page.captureScreenshot", {
            "format": "png",
            "fromSurface": True,
            "clip": clip
        })

        # 5) Decodificar base64 e salvar como PNG
        png_data = base64.b64decode(result["data"])
        file_path = os.path.join("output", f"page_{i+1:03}.png")
        with open(file_path, "wb") as f:
            f.write(png_data)
        screenshots.append(file_path)
        print(f"📸 Screenshot página {i+1} de {total} salva (via CDP).")

    driver.quit()
    return screenshots
