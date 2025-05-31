import time
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
import base64
import os
import requests

options = Options()
options.binary_location = r"D:\Program Files\Mozilla Firefox\firefox.exe"
options.headless = False

driver = webdriver.Firefox(options=options)
url = 'https://pt.scribd.com/document/434649239/The-Concise-Meditations-of-Marcus-Aurelius-by-Robin-Homer'
driver.get(url)

# Remove overlays que atrapalham
driver.execute_script("""
document.querySelectorAll('.overlay, .modal, .paywall, .login-prompt, .popup, #nux-modal, .container-overlay').forEach(el => el.remove());
""")

def scroll_slow_steps(driver, step=800, pause=0.15, max_steps=1000):
    current_pos = 0
    for _ in range(max_steps):
        driver.execute_script(f"window.scrollTo(0, {current_pos});")
        current_pos += step
        time.sleep(pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if current_pos >= new_height:
            break

# Scroll lento várias vezes para garantir renderização das páginas
scroll_slow_steps(driver, step=800, pause=0.15, max_steps=1000)

# Força scroll em cada página para ativar lazy loading (se houver)
driver.execute_script("""
  const containers = document.querySelectorAll('div.outer_page_container > div[id^="outer_page_"]');
  containers.forEach(c => c.scrollIntoView());
""")

time.sleep(3)  # espera estabilizar

document_container = driver.find_element(By.ID, "document_container")

# Seleciona as páginas que foram carregadas
pages = document_container.find_elements(By.CSS_SELECTOR, "div.outer_page_container > div[id^='outer_page_']")
print(f"Encontradas {len(pages)} páginas após scroll")

img_urls = []

for page_div in pages:
    imgs = page_div.find_elements(By.CSS_SELECTOR, "img.absimg")
    if imgs:
        for img in imgs:
            src = img.get_attribute('src')
            if src and src.startswith('http'):
                img_urls.append(src)
    else:
        data_url = driver.execute_script("""
            const canvas = arguments[0].querySelector('canvas');
            if(canvas) return canvas.toDataURL('image/jpeg');
            return null;
        """, page_div)
        if data_url:
            img_urls.append(data_url)

print(f"Total de imagens/canvas capturados: {len(img_urls)}")

os.makedirs('paginas', exist_ok=True)

for i, img_url in enumerate(img_urls):
    try:
        if img_url.startswith('data:image'):
            header, encoded = img_url.split(',', 1)
            img_data = base64.b64decode(encoded)
            with open(f'paginas/page_{i+1:03}.jpg', 'wb') as f:
                f.write(img_data)
        else:
            img_data = requests.get(img_url).content
            with open(f'paginas/page_{i+1:03}.jpg', 'wb') as f:
                f.write(img_data)
    except Exception as e:
        print(f"Erro ao baixar/imagem {i+1}: {e}")

print("✅ Imagens salvas!")

driver.quit()
