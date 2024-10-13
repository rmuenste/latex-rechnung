import os
import shutil
import json
import subprocess
import argparse


def generate_invoice(json_file):
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

def create_tex_file(data, invoice_folder):
    # Erstelle die .tex Datei für die Rechnungsdaten im Rechnungsordner
    tex_file_path = os.path.join(invoice_folder, "invoice_data.tex")
    
    with open(tex_file_path, 'w') as tex_file:
        tex_file.write(r"""
% ################## invoice DATA ##################
\newcommand{\invoiceDate}{""" + data['invoiceDate'] + r"""} % Datum der Rechnungsstellung
\newcommand{\payDate}{""" + data['payDate'] + r"""} % Datum der Zahlungsfrist
\newcommand{\invoiceReference}{""" + data['invoiceReference'] + r"""} % Rechnungsnummer
\newcommand{\invoiceSalutation}{""" + data['invoiceSalutation'] + r"""} % Anrede
\newcommand{\invoiceText}{""" + data['invoiceText'] + r"""} % Rechnungstext
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

def compile_latex(fileName, tex_file, folder):
    workingFolder = os.getcwd()

    os.chdir(folder)
    # Latex-Kompilation ausführen
    #subprocess.run(["pdflatex", "-output-directory", folder, tex_file], check=True)
    subprocess.run(["pdflatex", fileName], check=True)
    print(f"Die Datei {tex_file} wurde erfolgreich kompiliert.")
    os.chdir(workingFolder)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("data", help="The json file containing the data for the current invoice.")
    args = parser.parse_args()

    # Beispielaufruf
    json_file = ""

    json_file = args.data

    generate_invoice(json_file)
