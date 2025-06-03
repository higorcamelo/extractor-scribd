# extractor.py

import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By


def setup_driver():
    """
    Cria e retorna uma instância do Firefox WebDriver com perfil mínimo,
    sem carregar extensões e com paywalls/modais bloqueados em seguida.
    """
    options = Options()
    options.binary_location = r"D:\Program Files\Mozilla Firefox\firefox.exe"
    options.headless = False  # Mude para True se quiser rodar sem interface
    driver = webdriver.Firefox(options=options)
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
    # aguarda um instante para garantir que não há JS residual
    time.sleep(0.5)


def detect_document_type(url):
    """
    Abre o URL, bloqueia paywalls/script e faz scroll mínimo para renderizar.
    Retorna:
      - "scan" se houver mais imagens (img.absimg) do que camadas de texto (div.text_layer)
      - "text" se houver ao menos uma camada de texto (div.text_layer)
      - "unknown" caso contrário
    """
    driver = setup_driver()
    driver.get(url)

    hardcore_block(driver)
    time.sleep(1)  # aguarda renderizar o conteúdo inicial

    # Conta quantas <img class="absimg"> e quantas <div class="text_layer">
    has_images = driver.execute_script("return document.querySelectorAll('img.absimg').length")
    has_text = driver.execute_script("return document.querySelectorAll('div.text_layer').length")

    driver.quit()

    if has_images > has_text:
        return "scan"
    elif has_text > 0:
        return "text"
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

    # Após o scroll, força cada página a estar na viewport (por via das dúvidas)
    driver.execute_script("""
        document.querySelectorAll('div.outer_page_container > div[id^="outer_page_"]').forEach(c => c.scrollIntoView());
    """)
    time.sleep(1)

    # Seleciona o container principal e depois todas as páginas
    document_container = driver.find_element(By.ID, "document_container")
    pages = document_container.find_elements(By.CSS_SELECTOR, "div.outer_page_container > div[id^='outer_page_']")

    img_urls = []
    for page_div in pages:
        imgs = page_div.find_elements(By.CSS_SELECTOR, "img.absimg")
        for img in imgs:
            src = img.get_attribute('src')
            if src and src.startswith("http"):
                img_urls.append(src)

    # Cria a pasta de saída se não existir
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
    Gera um screenshot (PNG) de cada página renderizada do Scribd (quando o documento for 'text'),
    salva em output/page_XXX.png e retorna a lista de caminhos dessas imagens.
    """
    driver = setup_driver()
    driver.get(url)

    hardcore_block(driver)
    scroll_page_smooth(driver)

    # Garante que cada página esteja visível para lazy load
    driver.execute_script("""
        document.querySelectorAll('div.outer_page_container > div[id^="outer_page_"]').forEach(c => c.scrollIntoView());
    """)
    time.sleep(1)

    document_container = driver.find_element(By.ID, "document_container")
    pages = document_container.find_elements(By.CSS_SELECTOR, "div.outer_page_container > div[id^='outer_page_']")

    output_folder = "output"
    os.makedirs(output_folder, exist_ok=True)

    screenshots = []
    total = len(pages)
    print(f"📄 Documento de texto com {total} páginas. Salvando screenshots...")

    for i, page_div in enumerate(pages):
        file_path = os.path.join(output_folder, f"page_{i+1:03}.png")
        # Faz screenshot apenas da região da div específica
        page_div.screenshot(file_path)
        screenshots.append(file_path)
        print(f"📸 Screenshot página {i+1} de {total} salva.")

    driver.quit()
    return screenshots
