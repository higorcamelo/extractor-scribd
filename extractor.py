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
    Cria e retorna uma instância do Edge WebDriver com perfil mínimo,
    sem carregar extensões e com paywalls/modais bloqueados em seguida.
    """
    options = Options()
    options.headless = True  # Mude para False se quiser rodar com interface
    service = EdgeService(EdgeChromiumDriverManager().install())
    driver = webdriver.Edge(service=service, options=options)
    driver.set_window_size(1920, 4000)
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
    driver = setup_driver()
    driver.get(url)

    hardcore_block(driver)
    scroll_page_smooth(driver, pause=0.2)

    time.sleep(1)  # Dá tempo para o conteúdo aparecer

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
    Captura screenshots das páginas de livros com texto renderizado no Scribd.
    Extrai somente o conteúdo visual da página, sem cabeçalho, rodapé ou interface do site.
    """
    driver = setup_driver()
    driver.get(url)

    hardcore_block(driver)
    scroll_page_smooth(driver, pause=0.2)

    # Remover banners de cookies e cabeçalhos de uma vez (tudo em uma única linha):
    driver.execute_script("""
        // Remove banners por classe ou id conhecidos
        document.querySelectorAll(
            'div[class*="cookie"], div[class*="Cookie"], div[id*="cookie"], '
            + 'div[class*="privacy"], div[id*="privacy"], '
            + 'header, nav, .navbar, .site-header'
        ).forEach(e => e.remove());

        // Remove absolutamente qualquer elemento com position fixed ou sticky que não seja parte das páginas
        Array.from(document.querySelectorAll('body *')).forEach(el => {
            const style = window.getComputedStyle(el);
            if ((style.position === 'fixed' || style.position === 'sticky') 
                && !el.closest('#document_container')) {
                el.remove();
            }
        });
    """)
    time.sleep(0.5)

    # Força cada página a ficar na viewport
    driver.execute_script(
        "document.querySelectorAll("
        "'div.outer_page_container > div[id^=\"outer_page_\"]'"
        ").forEach(c => c.scrollIntoView());"
    )
    time.sleep(0.5)

    document_container = driver.find_element(By.ID, "document_container")
    pages = document_container.find_elements(
        By.CSS_SELECTOR,
        "div.outer_page_container > div[id^='outer_page_']"
    )

    output_folder = "output"
    os.makedirs(output_folder, exist_ok=True)

    screenshots = []
    total = len(pages)
    print(f"📄 Documento de texto com {total} páginas. Salvando screenshots...")

    for i, page_div in enumerate(pages):
        try:
            newpage = page_div.find_element(By.CSS_SELECTOR, "div.newpage")
        except:
            newpage = page_div

        file_path = os.path.join(output_folder, f"page_{i+1:03}.png")
        newpage.screenshot(file_path)
        screenshots.append(file_path)
        print(f"📸 Screenshot página {i+1} de {total} salva.")

    driver.quit()
    return screenshots