from extractor import detect_document_type, extract_text
from renderer import save_images_to_pdf, save_text_to_pdf
import os

url = input("Insira o link do documento Scribd: ").strip()

output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

doc_type = detect_document_type(url)
print(f"Tipo de documento detectado: {doc_type}")

if doc_type == "text":
    print("Extraindo texto (screenshots)...")
    images = extract_text(url)

    opcao = input("Gerar (1) PDF simples de imagens ou (2) PDF com OCR embutido? [1/2]: ")

    if opcao.strip() == "2":
        print("Gerando PDF com OCR embutido...")
        save_text_to_pdf(images, os.path.join(output_folder, "documento_ocr.pdf"))
    else:
        print("Gerando PDF simples...")
        save_images_to_pdf(images, os.path.join(output_folder, "documento.pdf"))

else:
    print("❌ Este script está atualmente configurado só para livros com texto renderizado.")
    print("→ Para livros com imagens (scan), utilize o modo de extração de imagens que já funciona.")

print("✅ Processo concluído.")
