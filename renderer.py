from PIL import Image
from fpdf import FPDF

def save_images_to_pdf(image_paths, output_path):
    images = [Image.open(img).convert('RGB') for img in image_paths]
    images[0].save(output_path, save_all=True, append_images=images[1:])

def save_text_to_pdf(pages, output_path):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for page in pages:
        pdf.add_page()
        pdf.multi_cell(0, 10, page)

    pdf.output(output_path)
