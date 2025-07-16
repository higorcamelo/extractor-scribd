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
    Cria e retorna uma instância do Edge WebDriver com múltiplos fallbacks
    para máxima compatibilidade em diferentes sistemas.
    """
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-web-security")
    options.add_argument("--allow-running-insecure-content")
    options.add_argument("--disable-features=VizDisplayCompositor")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    print("🔧 Inicializando EdgeDriver...")
    
    # Múltiplos métodos de fallback
    methods = [
        ("WebDriver Manager (fresh)", lambda: EdgeService(EdgeChromiumDriverManager().install())),
        ("Driver do sistema", lambda: EdgeService()),
        ("Chrome como fallback", lambda: setup_chrome_fallback()),
    ]
    
    for method_name, method_func in methods:
        try:
            print(f"🔄 Tentando: {method_name}")
            service = method_func()
            driver = webdriver.Edge(service=service, options=options)
            driver.set_window_size(1920, 2000)
            print(f"✅ EdgeDriver inicializado com sucesso via {method_name}")
            return driver
        except Exception as e:
            print(f"❌ Falhou {method_name}: {str(e)[:100]}...")
            continue
    
    raise RuntimeError("❌ Todos os métodos de inicialização falharam")

def setup_chrome_fallback():
    """
    Fallback para Chrome se Edge não funcionar.
    """
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from webdriver_manager.chrome import ChromeDriverManager
    
    print("🔄 Tentando Chrome como fallback...")
    chrome_options = ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
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
    try:
        print(f"🌐 Tentando acessar: {url}")
        driver.set_page_load_timeout(30)
        driver.get(url)
        print("✅ Página carregada com sucesso")

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

        return images
        
    except Exception as e:
        print(f"❌ Erro detalhado: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        driver.quit()
