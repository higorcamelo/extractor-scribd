import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from nicegui import ui
import os
from extractor import detect_document_type, extract_text
from renderer import save_images_to_pdf

output_folder = "output"
os.makedirs(output_folder, exist_ok=True)


def baixar_documento():
    progresso.set_value(0)
    status.set_text("🔍 Detectando tipo de documento...")

    doc_type = detect_document_type(link.value)
    if doc_type != "text":
        ui.notify("❌ Documento não é de texto renderizado ou não foi detectado corretamente.")
        status.set_text("❌ Documento não suportado.")
        progresso.set_value(0)
        return

    status.set_text("📥 Baixando páginas...")
    progresso.set_value(0.3)

    imagens = extract_text(link.value)

    status.set_text("🗜️ Gerando PDF...")
    progresso.set_value(0.7)

    pdf_path = os.path.join(pasta.value, f"{nome_pdf.value}.pdf")
    save_images_to_pdf(imagens, pdf_path)

    if not manter_png.value:
        for img in imagens:
            os.remove(img)

    status.set_text(f"✅ PDF salvo em {pdf_path}")
    progresso.set_value(1.0)
    ui.notify(f"✅ PDF salvo em {pdf_path}")


@ui.page('/')
def home():
    with ui.header().classes('bg-blue-700'):
        ui.label('📄 Scribd Downloader').classes('text-white text-2xl font-bold')
        ui.link('Biblioteca', '/biblioteca').classes('text-white')

    with ui.card().classes('max-w-xl mx-auto mt-10'):
        ui.label('🔗 Link do Scribd').classes('text-lg font-medium')
        global link
        link = ui.input('Cole aqui o link do documento').classes('w-full')

        ui.label('📄 Nome do PDF').classes('text-lg font-medium mt-4')
        global nome_pdf
        nome_pdf = ui.input('Nome do PDF (sem .pdf)').classes('w-full')
        nome_pdf.value = 'documento'

        ui.label('📂 Pasta de saída').classes('text-lg font-medium mt-4')
        global pasta
        pasta = ui.input('Pasta de saída').classes('w-full')
        pasta.value = output_folder

        global manter_png
        manter_png = ui.checkbox('🖼️ Manter PNGs após gerar o PDF')

        ui.button('📥 Baixar e gerar PDF', on_click=baixar_documento).classes('w-full mt-4')

        global status, progresso
        status = ui.label('').classes('text-sm text-gray-600')
        progresso = ui.linear_progress().classes('w-full')


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
                        ui.button('Abrir', on_click=lambda a=arquivo: os.startfile(os.path.join(output_folder, a)))
                        ui.button('Deletar', on_click=lambda a=arquivo: (
                            os.remove(os.path.join(output_folder, a)),
                            ui.notify(f'{a} deletado!'),
                            atualizar_lista()
                        ))
        else:
            with lista:
                ui.label('Nenhum PDF encontrado na biblioteca.')

    atualizar_lista()

    ui.button('🔄 Atualizar', on_click=atualizar_lista).classes('mt-4')


ui.run(title="Scribd Downloader")
