import os
import sys
import threading
import FreeSimpleGUI as sg
from extractor_text import detect_document_type as detect_type
from extractor_text import extract_text
from extractor_scan import extract_images
from renderer import save_images_to_pdf

output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# Tema customizado DarkBlueSmooth, usando a função correta para adicionar tema antes de setar
custom_theme = {
    'BACKGROUND': '#121A2B',
    'TEXT': '#E0E6F0',
    'INPUT': '#1E2747',
    'TEXT_INPUT': '#D0D8FF',
    'SCROLL': '#2A3558',
    'BUTTON': ('#E0E6F0', '#3B5A99'),
    'BUTTON_HOVER': ('#FFFFFF', '#5A7BCF'),
    'FRAME_BACKGROUND': '#1A2340',
    'BORDER': 0,
}

# Registrar tema antes de usar
if 'DarkBlueSmooth' not in sg.theme_list():
    sg.theme_add_new('DarkBlueSmooth', custom_theme)

sg.theme('DarkBlueSmooth')

FONT_TITLE = ('Segoe UI', 16, 'bold')
FONT_LABEL = ('Segoe UI', 11)
FONT_INPUT = ('Segoe UI', 11)
FONT_LOG = ('Consolas', 11)

class GuiLogger:
    def __init__(self, window):
        self.window = window
        self._stdout = sys.stdout

    def write(self, message):
        self._stdout.write(message)
        if message.strip():
            self.window.write_event_value('-LOG-', message)

    def flush(self):
        self._stdout.flush()

def baixar_documento(window, values):
    try:
        window['-LOG-'].update('')
        url = values['-LINK-'].strip()
        nome = values['-NOME-'].strip()
        pasta = values['-PASTA-'].strip()
        manter_png = values['-MANTERPNG-']

        if not url:
            print("❌ Link não pode estar vazio.")
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
            imagens = extract_images(url, pasta)

        else:
            print("❌ Documento não reconhecido ou não suportado.")
            return

        print('🗜️ Gerando PDF...')
        pdf_path = os.path.join(pasta, f'{nome}.pdf')
        save_images_to_pdf(imagens, pdf_path)

        if not manter_png:
            for img in imagens:
                os.remove(img)
            print('🗑️ PNGs temporários removidos.')

        print(f'✅ PDF salvo em {pdf_path}')
    except Exception as e:
        print(f'❌ Erro: {e}')

def main():
    layout = [
        [sg.Text('📄 Scribd Downloader', font=FONT_TITLE, justification='center', expand_x=True, pad=(0,20))],

        [sg.Frame('Configurações', font=FONT_LABEL, title_color="#F8F8F8", relief=sg.RELIEF_SUNKEN, 
                  layout=[
                    [sg.Text('🔗 Link do Scribd:', font=FONT_LABEL, pad=((0,5), (5,2)))],
                    [sg.Input(key='-LINK-', size=(60, 1), font=FONT_INPUT, focus=True)],
                    
                    [sg.Text('📄 Nome do PDF:', font=FONT_LABEL, pad=((0,5), (15,2)))],
                    [sg.Input('documento', key='-NOME-', size=(60, 1), font=FONT_INPUT)],

                    [sg.Text('📂 Pasta de saída:', font=FONT_LABEL, pad=((0,5), (15,2)))],
                    [sg.Input(output_folder, key='-PASTA-', size=(48,1), font=FONT_INPUT, readonly=True), 
                     sg.FolderBrowse(button_text='📁', font=FONT_LABEL, tooltip='Selecionar pasta')],
                    
                    [sg.Checkbox('🖼️ Manter PNGs após gerar o PDF', key='-MANTERPNG-', font=FONT_LABEL, pad=((0,0),(20,10)))]
                  ], element_justification='left', expand_x=True)],

        [sg.Button('📥 Baixar e gerar PDF', size=(40,1), font=FONT_LABEL, button_color=custom_theme['BUTTON'])],

        [sg.Text('📝 Log de Execução:', font=FONT_LABEL, pad=((0,0),(15,5)))],
        [sg.Multiline('', key='-LOG-', size=(80, 20), autoscroll=True, disabled=True, 
                      background_color=custom_theme['INPUT'], text_color=custom_theme['TEXT_INPUT'], font=FONT_LOG)],
    ]

    window = sg.Window('Scribd Downloader', layout, finalize=True, resizable=False, element_justification='center')

    sys.stdout = GuiLogger(window)

    while True:
        event, values = window.read()

        if event == sg.WINDOW_CLOSED:
            break

        if event == '📥 Baixar e gerar PDF':
            threading.Thread(target=baixar_documento, args=(window, values), daemon=True).start()

        if event == '-LOG-':
            current_log = window['-LOG-'].get()
            window['-LOG-'].update(current_log + values[event])

    window.close()

if __name__ == '__main__':
    main()
