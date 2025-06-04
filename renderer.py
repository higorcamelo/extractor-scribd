import os
from PIL import Image
import pytesseract
import fitz  # PyMuPDF


tesseract_path = os.path.join(os.getcwd(), "tesseract", "tesseract.exe")
pytesseract.pytesseract.tesseract_cmd = tesseract_path


def save_text_to_pdf(image_paths, output_path):
    """
    Gera um PDF visual (com as imagens) e embute texto OCR invisível.
    """
    pdf = fitz.open()

    for img_path in image_paths:
        img = Image.open(img_path)
        width, height = img.size

        # Cria uma nova página no tamanho da imagem
        page = pdf.new_page(width=width, height=height)

        # Insere a imagem como fundo da página
        img_rect = fitz.Rect(0, 0, width, height)
        page.insert_image(img_rect, filename=img_path)

        # OCR na imagem
        print(f"🧠 Executando OCR na página {os.path.basename(img_path)}...")
        # Ajusta tamanho da imagem para garantir DPI adequado
        ocr_pdf_bytes = pytesseract.image_to_pdf_or_hocr(
            img.resize((img.width * 2, img.height * 2), Image.LANCZOS),
            extension='pdf',
            lang='por+eng'
        )
        ocr_pdf = fitz.open("pdf", ocr_pdf_bytes)

        # Copia a camada OCR para o PDF principal
        page.show_pdf_page(img_rect, ocr_pdf, 0)

        print(f"✅ OCR embutido na página {os.path.basename(img_path)}")

    pdf.save(output_path)
    pdf.close()
    print(f"📄 PDF com OCR salvo em {output_path}")


def save_images_to_pdf(image_paths, output_path):
    """
    Gera um PDF visual somente com imagens (sem OCR).
    """
    images = [Image.open(img).convert('RGB') for img in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])
    print(f"📄 PDF de imagens salvo em {output_path}")