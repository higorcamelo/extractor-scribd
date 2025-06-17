import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.microsoft import EdgeChromiumDriverManager

def setup_driver():
    """
    Cria uma instância do Edge WebDriver headless, otimizado para extrair imagens
    de documentos escaneados do Scribd.
    """
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    service = EdgeService(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.set_window_size(1920, 2000)
    return driver

def scroll_page_smooth(driver, pause=0.2):
    """
    Faz scroll gradual até o fim da página para ativar lazy loading.
    """
    scroll_height = driver.execute_script("return document.body.scrollHeight")
    current = 0
    while current < scroll_height:
        driver.execute_script(f"window.scrollTo(0, {current});")
        current += 500
        time.sleep(pause)
        scroll_height = driver.execute_script("return document.body.scrollHeight")
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(1)

def hardcore_block(driver):
    """
    Remove scripts, modais e elementos que possam obstruir a renderização.
    """
    driver.execute_script("window.stop();")
    driver.execute_script("""
        document.querySelectorAll('script').forEach(e => e.remove());
        document.querySelectorAll('.overlay, .modal, .paywall, .popup, .login-prompt, .container-overlay').forEach(e => e.remove());
    """)
    time.sleep(0.5)

def extract_images(url, output_folder):
    """
    Extrai todas as imagens <img.absimg> de um documento de scan no Scribd.
    Salva em JPG na pasta especificada e retorna os caminhos.
    """
    driver = setup_driver()
    driver.get(url)

    print("🔒 Limpando bloqueios e modais...")
    hardcore_block(driver)

    print("📜 Fazendo scroll para carregar todas as páginas...")
    scroll_page_smooth(driver)

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
    total = len(img_urls)
    print(f"🖼️ Encontradas {total} imagens. Baixando...")
    for i, img_url in enumerate(img_urls):
        try:
            resp = requests.get(img_url, timeout=15)
            resp.raise_for_status()
            file_path = os.path.join(output_folder, f"page_{i+1:03}.jpg")
            with open(file_path, "wb") as f:
                f.write(resp.content)
            images.append(file_path)
            print(f"✅ Baixada página {i+1} de {total}")
        except Exception as e:
            print(f"❌ Erro ao baixar página {i+1}: {e}")

    driver.quit()
    return images
