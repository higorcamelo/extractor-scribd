from extractor import detect_document_type, extract_images, extract_text
from renderer import save_images_to_pdf, save_text_to_pdf
import os

# ✅ Link de exemplo
url = input("Insira o link do documento Scribd: ").strip()

# 📂 Pasta de saída
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# 🔍 Detecta tipo
doc_type = detect_document_type(url)
print(f"Tipo de documento detectado: {doc_type}")

if doc_type == "scan":
    print("Extraindo imagens...")
    images = extract_images(url, output_folder)
    print("Gerando PDF...")
    save_images_to_pdf(images, os.path.join(output_folder, "documento.pdf"))

elif doc_type == "text":
    print("Extraindo texto (screenshots)...")
    images = extract_text(url)
    print("Gerando PDF...")
    save_text_to_pdf(images, os.path.join(output_folder, "documento.pdf"))

print("✅ Processo concluído.")