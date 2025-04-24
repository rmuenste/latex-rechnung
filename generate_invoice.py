import os
import shutil
import json
import subprocess
import logging
import sys
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Constants ---
TEMPLATE_DIR = "invoice_template"
MAIN_TEX_FILE = "main_invoice.tex"
DATA_TEX_FILE = "invoice_data.tex"
DEFAULT_LATEX_COMMAND = "pdflatex"

# --- LaTeX Sanitization ---
# Basic LaTeX character escaping
#==========================================================================    
def sanitize_latex(text):
    """Escape special LaTeX characters in a string."""
    if not isinstance(text, str):
        text = str(text) # Make sure this is a string
    chars = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
        '\\': r'\textbackslash{}'
    }

    # Simple replace - adjust if more escaping is needed
    for char, escaped in chars.items():
        text.replace(char, escaped)

    # Handle potential newlines - replace with LaTex newline or space
    text = text.replace('\n', r'\\')
    return text
#==========================================================================    


#==========================================================================    
def create_tex_data_file(data, invoice_folder):
    """Creates the invoice_data.tex file with sanitized data."""
    tex_file_path = os.path.join(invoice_folder, DATA_TEX_FILE)
    required_keys = [ # Define keys expected in the JSON
        'invoiceDate', 'invoiceTimeSpan', 'payDate', 'invoiceReference',
        'invoiceSalutation', 'invoiceText', 'invoiceServices', 'invoiceEnclosures',
        'invoiceClosing', 'customerCompany', 'customerName', 'customerStreet',
        'customerZIP', 'customerCity', 'taxID', 'senderName', 'senderStreet',
        'senderZIP', 'senderCity', 'senderTelephone', 'senderMobilephone',
        'senderEmail', 'senderWeb', 'accountRCPT', 'accountNumber',
        'accountBLZ', 'accountBankName', 'accountIBAN', 'accountBIC'
    ]    

    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        logging.error(f"Missing required keys in JSON data: {', '.join(missing_keys)}")
        raise ValueError("JSON data is missing required keys")

    # Generate LaTeX commands using f-strings and sanitization
    tex_content = r"% --- Generated Invoice Data ---" + "\n"
    for key in required_keys:
        value = data.get(key, '')
        sanitized_value = sanitize_latex(value)
        tex_content += f"\\newcommand{{\\{key}}}{{{sanitized_value}}}\n"
    tex_content += r"% --- End Generated Invoice Data ---" + "\n"

    try:
        with open(tex_file_path, 'w', encoding='utf-8') as tex_file:
            tex_file.write(tex_content)
        logging.info(f"Created LaTeX data file: {tex_file_path}")
    except IOError as e:
        logging.error(f"Failed to write LaTex data file {tex_file_path}: {e}")
        raise
    
#==========================================================================    


#==========================================================================    
def generate_invoice(json_file, force_overwrite=False,
                     latex_cmd=DEFAULT_LATEX_COMMAND):
    # Lade die JSON-Daten
    with open(json_file, 'r') as f:
        data = json.load(f)

    

    # Erstelle den Rechnungsordner
    invoice_folder = f"invoice-{data['invoiceReference']}"

    # Kopiere die main_invoice.tex Datei in den Rechnungsordner
    template_path = "invoice_template/main_invoice.tex"
    target_template_path = os.path.join(invoice_folder, "main_invoice.tex")

    if os.path.exists(invoice_folder):
        shutil.rmtree(invoice_folder)

    shutil.copytree("invoice_template", invoice_folder)
    #============================================================================================
    # if not os.path.exists(invoice_folder):
    #     os.makedirs(invoice_folder)
    # print(f"Ordner {invoice_folder} erstellt.")
    
    # shutil.copy(template_path, target_template_path)
    # print(f"Kopie von {template_path} nach {target_template_path} erstellt.")
    #============================================================================================
    
    # Erstelle das invoice_template.tex mit den JSON-Daten (führt das zuvor erstellte Skript aus)
    create_tex_file(data, invoice_folder)
    
    mainFileName = "main_invoice.tex"
    # Führe die Latex-Kompilation der main_invoice.tex im Rechnungsordner durch
    compile_latex(mainFileName, target_template_path, invoice_folder)
#==========================================================================    


#==========================================================================    
def create_tex_file(data, invoice_folder):
    # Erstelle die .tex Datei für die Rechnungsdaten im Rechnungsordner
    tex_file_path = os.path.join(invoice_folder, "invoice_data.tex")
    
    with open(tex_file_path, 'w') as tex_file:
        tex_file.write(r"""
% ################## invoice DATA ##################
\newcommand{\invoiceDate}{""" + data['invoiceDate'] + r"""} % Datum der Rechnungsstellung
\newcommand{\invoiceTimeSpan}{""" + data['invoiceTimeSpan'] + r"""} % Datum der Rechnungsstellung
\newcommand{\payDate}{""" + data['payDate'] + r"""} % Datum der Zahlungsfrist
\newcommand{\invoiceReference}{""" + data['invoiceReference'] + r"""} % Rechnungsnummer
\newcommand{\invoiceSalutation}{""" + data['invoiceSalutation'] + r"""} % Anrede
\newcommand{\invoiceText}{""" + data['invoiceText'] + r"""} % Rechnungstext
\newcommand{\invoiceServices}{""" + data['invoiceServices'] + r"""} % RechnungsLeistung
\newcommand{\invoiceEnclosures}{""" + data['invoiceEnclosures'] + r"""} % Anlagen
\newcommand{\invoiceClosing}{""" + data['invoiceClosing'] + r"""} % Schlusssatz
% ################## invoice DATA ##################

% ################## Customer DATA ##################
\newcommand{\customerCompany}{""" + data['customerCompany'] + r"""} % Firma
\newcommand{\customerName}{""" + data['customerName'] + r"""} % Name
\newcommand{\customerStreet}{""" + data['customerStreet'] + r"""} % Straße
\newcommand{\customerZIP}{""" + data['customerZIP'] + r"""} % Postleitzahl
\newcommand{\customerCity}{""" + data['customerCity'] + r"""} % Ort
% ################## Customer DATA ##################

% ################## Personal DATA ##################
\newcommand{\taxID}{""" + data['taxID'] + r"""} % Steuernummer

% START SENDERS DATA
\newcommand{\senderName}{""" + data['senderName'] + r"""} % Absender Name
\newcommand{\senderStreet}{""" + data['senderStreet'] + r"""} % Absender Straße
\newcommand{\senderZIP}{""" + data['senderZIP'] + r"""} % Absender Postleitzahl
\newcommand{\senderCity}{""" + data['senderCity'] + r"""} % Absender Stadt
\newcommand{\senderTelephone}{""" + data['senderTelephone'] + r"""} % Telefon
\newcommand{\senderMobilephone}{""" + data['senderMobilephone'] + r"""} % Mobiltelefon
\newcommand{\senderEmail}{""" + data['senderEmail'] + r"""} % Email
\newcommand{\senderWeb}{""" + data['senderWeb'] + r"""} % Webseite
% END SENDER DATA

% START ACCOUNT DATA
\newcommand{\accountRCPT}{""" + data['accountRCPT'] + r"""} % Kontoinhaber
\newcommand{\accountNumber}{""" + data['accountNumber'] + r"""} % Kontonummer
\newcommand{\accountBLZ}{""" + data['accountBLZ'] + r"""} % Bankleitzahl
\newcommand{\accountBankName}{""" + data['accountBankName'] + r"""} % Bankname
\newcommand{\accountIBAN}{""" + data['accountIBAN'] + r"""} % IBAN
\newcommand{\accountBIC}{""" + data['accountBIC'] + r"""} % BIC
% END ACCOUNT DATA
% ################## Personal DATA ##################
""")
    print(f"Die Datei invoice_template.tex wurde im Ordner {invoice_folder} erstellt.")
#==========================================================================    


#==========================================================================    
def compile_latex(fileName, tex_file, folder):
    workingFolder = os.getcwd()

    os.chdir(folder)
    # Latex-Kompilation ausführen
    #subprocess.run(["pdflatex", "-output-directory", folder, tex_file], check=True)
    subprocess.run(["pdflatex", fileName], check=True)
    print(f"Die Datei {tex_file} wurde erfolgreich kompiliert.")
    os.chdir(workingFolder)
#==========================================================================    


#==========================================================================    
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Generate a PDF invoice from a JSON file using a LaTeX template.")
    parser.add_argument("data", help="The json file containing the data for the current invoice.")

    parser.add_argument("-l", "--latex-cmd", default=DEFAULT_LATEX_COMMAND, 
                        help="The LaTeX command to use for compilation (default: pdflatex). Alternative: xelatex, lualatex")

    parser.add_argument("-f", "--force", action="store_true",
                        help="Force overwrite of existing invoice folder.")
    args = parser.parse_args()

    # Beispielaufruf
    json_file = ""

    json_file = args.data

    generate_invoice(json_file, args.force, args.latex_cmd)
