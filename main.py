import sys
import os

from nicegui import ui
from extractor_text import detect_document_type as detect_type
from extractor_text import extract_text
from extractor_scan import extract_images
from renderer import save_images_to_pdf

output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

log_box = None  # Definido globalmente

class GuiLogger:
    def __init__(self, log_box):
        self.log_box = log_box
        self._stdout = sys.stdout

    def write(self, message):
        self._stdout.write(message)
        if message.strip() and self.log_box is not None:
            self.log_box.value += message

    def flush(self):
        self._stdout.flush()

async def baixar_documento():
    log_box.value = ""
    url = link.value.strip()
    nome = nome_pdf.value.strip()

    if not url:
        print("❌ Link não pode estar vazio.")
        ui.notify("❌ Link inválido.")
        return

    print('🔍 Detectando tipo de documento...')
    tipo = detect_type(url)

    if tipo == 'text':
        print("📘 Documento identificado como TEXTO.")
        print('📥 Baixando páginas (texto)...')
        imagens = extract_text(url)

    elif tipo == 'scan':
        print("📕 Documento identificado como SCAN.")
        print('📥 Baixando imagens...')
        imagens = extract_images(url, output_folder)

    else:
        print("❌ Documento não reconhecido ou não suportado.")
        ui.notify("❌ Documento não reconhecido ou não suportado.")
        return

    print('🗜️ Gerando PDF...')
    pdf_path = os.path.join(pasta.value, f'{nome}.pdf')
    save_images_to_pdf(imagens, pdf_path)

    if not manter_png.value:
        for img in imagens:
            os.remove(img)
        print('🗑️ PNGs temporários removidos.')

    print(f'✅ PDF salvo em {pdf_path}')
    ui.notify(f'✅ PDF salvo em {pdf_path}')

@ui.page('/')
def home():
    global log_box
    with ui.header().classes('bg-blue-700'):
        ui.label('📄 Scribd Downloader').classes('text-white text-2xl font-bold')
        ui.link('Biblioteca', '/biblioteca').classes('text-white')

    with ui.card().classes('max-w-xl mx-auto mt-10 p-4 shadow'):
        ui.label('🔗 Link do Scribd').classes('text-lg font-medium')
        global link
        link = ui.input('Cole aqui o link do documento').classes('w-full')

        ui.label('📄 Nome do PDF').classes('text-lg font-medium mt-4')
        global nome_pdf
        nome_pdf = ui.input('Nome do PDF (sem .pdf)').classes('w-full')
        nome_pdf.value = 'documento'

        ui.label('📂 Pasta de saída').classes('text-lg font-medium mt-4')
        with ui.row():
            global pasta
            pasta = ui.input('Pasta de saída').classes('w-full').props('readonly')
            pasta.value = output_folder

        global manter_png
        manter_png = ui.checkbox('🖼️ Manter PNGs após gerar o PDF')

        ui.button('📥 Baixar e gerar PDF', on_click=baixar_documento).classes('w-full mt-4')

        ui.separator().classes('my-4')
        ui.label('📝 Log de Execução').classes('text-md font-medium mt-2')

        log_box = ui.textarea('').props('readonly').classes('w-full h-64 bg-gray-100 rounded p-2')
        sys.stdout = GuiLogger(log_box)

@ui.page('/biblioteca')
def biblioteca():
    with ui.header().classes('bg-blue-700'):
        ui.label('📄 Scribd Downloader').classes('text-white text-2xl font-bold')
        ui.link('Início', '/').classes('text-white')

    ui.label('📚 Biblioteca de PDFs').classes('text-xl font-bold mt-6')

    lista = ui.column().classes('mt-4')

    def atualizar_lista():
        lista.clear()
        arquivos = [f for f in os.listdir(output_folder) if f.lower().endswith('.pdf')]
        if arquivos:
            for arquivo in arquivos:
                with lista:
                    with ui.row().classes('items-center'):
                        ui.label(arquivo)
                        ui.button('Abrir', on_click=lambda a=arquivo: os.startfile(os.path.join(output_folder, a))).classes('ml-4')
                        ui.button(
                            'Deletar',
                            on_click=lambda a=arquivo: (
                                os.remove(os.path.join(output_folder, a)),
                                ui.notify(f'{a} deletado!'),
                                atualizar_lista()
                            )
                        ).classes('ml-2')
        else:
            with lista:
                ui.label('Nenhum PDF encontrado na biblioteca.')

    atualizar_lista()
    ui.button('🔄 Atualizar', on_click=atualizar_lista).classes('mt-4')

ui.run(title="Scribd Downloader")
