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
def compile_latex2(main_tex_file, target_folder, latex_command=DEFAULT_LATEX_COMMAND):
    """Compiles the main LaTeX file within the target folder."""
    current_dir = os.getcwd()
    try:
        os.chdir(target_folder)
        logging.info(f"Changed directory to: {target_folder}")

        # Check if LaTeX command exists (basic check)
        if not shutil.which(latex_command):
            logging.error(f"LaTeX command '{latex_command}' not found in PATH.")
            raise FileExistsError(f"LaTeX command '{latex_command}' not found.")

        # Run LaTeX compilation (consider running twice for references/TOC)
        # Suppress LaTeX output unless errors occur for cleaner logs
        logging.info(f"Running '{latex_command} {main_tex_file}'...")
        process = subprocess.run(
            [latex_command, "-interaction=nonstopmode", main_tex_file],
            check=False, # Check manually for better error reporting
            capture_output=True, # Capture stdout/stderr
            text=True, # Decode output as text
            encoding='utf-8', # Assume utf-8 output from latex
            errors='replace' # Add this!
        )

        if process.returncode != 0:
            logging.error(f"LaTeX compilation failed (exit code {process.returncode}).")
            logging.error("--- LaTeX Output ---")
            logging.error(process.stdout) # Log captured output
            logging.error("--- End LaTeX Output ---")
            # Consider also logging stderr if relevant: logging.error(process.stderr)
            raise subprocess.CalledProcessError(process.returncode, process.args, process.stdout, process.stderr)
        else:
            # Optionally run again if needed (e.g., for cross-references, TOC)
            logging.info("First LaTeX pass successful. Running again for references...")
            process = subprocess.run(
                [latex_command, "-interaction=nonstopmode", main_tex_file],
                check=True, capture_output=True, text=True, encoding='utf-8',errors='replace'
            )
            logging.info(f"Successfully compiled {main_tex_file} in {target_folder}") 

    except FileNotFoundError:
        # Reraise specific error if command not found
        raise
    except subprocess.CalledProcessError as e:
        logging.error(f"LaTeX compilation failed during second pass: {e}")
        # Optionally log e.stdout again here if needed
        raise # Reraise the exception
    except Exception as e:
        logging.error(f"An unexpected error occurred during LaTeX compilation: {e}")
        raise
    finally:
        # CRITICAL: Always change back to the original directory
        os.chdir(current_dir)
        logging.info(f"Returned to directory: {current_dir}")

    
#==========================================================================    
def generate_invoice(json_file_path, force_overwrite=False, latex_cmd=DEFAULT_LATEX_COMMAND):
    """Generates an invoice PDF from a JSON data file."""
    # 1. Validate input JSON path
    if not os.path.isfile(json_file_path):
        logging.error(f"Input JSON file not found: {json_file_path}")
        sys.exit(1) # Exit script if input file is invalid

    # 2. Load JSON data with error handling
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f: # Specify encoding
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON file {json_file_path}: {e}")
        sys.exit(1)
    except IOError as e:
         logging.error(f"Could not read JSON file {json_file_path}: {e}")
         sys.exit(1)

    # 3. Validate essential data early
    if 'invoiceReference' not in data or not data['invoiceReference']:
        logging.error("JSON data must contain a non-empty 'invoiceReference' key.")
        sys.exit(1)
    invoice_ref = data['invoiceReference']
    invoice_folder = f"invoice-{invoice_ref}"
    output_pdf_name = f"invoice-{invoice_ref}.pdf" # Define desired output name

    # 4. Handle existing output directory
    if os.path.exists(invoice_folder):
        if force_overwrite:
            logging.warning(f"Folder '{invoice_folder}' exists. Overwriting due to --force flag.")
            try:
                shutil.rmtree(invoice_folder)
            except OSError as e:
                logging.error(f"Failed to remove existing folder '{invoice_folder}': {e}")
                sys.exit(1)
        else:
            logging.error(f"Output folder '{invoice_folder}' already exists. Use --force to overwrite.")
            sys.exit(1)

    # 5. Check for template directory
    if not os.path.isdir(TEMPLATE_DIR):
        logging.error(f"Template directory '{TEMPLATE_DIR}' not found.")
        sys.exit(1)

    # 6. Copy template directory
    try:
        shutil.copytree(TEMPLATE_DIR, invoice_folder)
        logging.info(f"Copied template '{TEMPLATE_DIR}' to '{invoice_folder}'")
    except OSError as e:
        logging.error(f"Failed to copy template directory: {e}")
        sys.exit(1) # Exit if template copy fails

    # 7. Create the data file and compile
    try:
        create_tex_data_file(data, invoice_folder)
        compile_latex2(MAIN_TEX_FILE, invoice_folder, latex_cmd)

        # 8. Rename the output PDF
        generated_pdf = os.path.join(invoice_folder, MAIN_TEX_FILE.replace('.tex', '.pdf'))
        final_pdf_path = os.path.join(invoice_folder, output_pdf_name)
        if os.path.exists(generated_pdf):
            shutil.move(generated_pdf, final_pdf_path)
            logging.info(f"Successfully generated invoice: {final_pdf_path}")
        else:
            logging.warning(f"Expected PDF '{generated_pdf}' not found after compilation.")
            # Decide if this is an error or just a warning

    except (ValueError, IOError, FileNotFoundError, subprocess.CalledProcessError) as e:
        # Catch specific errors from previous steps
        logging.error(f"Invoice generation failed: {e}")
        # Optional: Clean up the partially created folder?
        # if os.path.exists(invoice_folder):
        #     logging.info(f"Cleaning up folder {invoice_folder} due to error.")
        #     shutil.rmtree(invoice_folder)
        sys.exit(1) # Exit with error status
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred during invoice generation: {e}")
        sys.exit(1)
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
def generate_invoice2(json_file_path, force_overwrite=False, latex_cmd=DEFAULT_LATEX_COMMAND):
    """Generates an invoice PDF from a JSON data file."""
    # 1. Validate input JSON path
    if not os.path.isfile(json_file_path):
        logging.error(f"Input JSON file not found: {json_file_path}")
        sys.exit(1) # Exit script if input file is invalid

    # 2. Load JSON data with error handling
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f: # Specify encoding
            data = json.load(f)
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON file {json_file_path}: {e}")
        sys.exit(1)
    except IOError as e:
         logging.error(f"Could not read JSON file {json_file_path}: {e}")
         sys.exit(1)

    # 3. Validate essential data early
    if 'invoiceReference' not in data or not data['invoiceReference']:
        logging.error("JSON data must contain a non-empty 'invoiceReference' key.")
        sys.exit(1)
    invoice_ref = data['invoiceReference']
    invoice_folder = f"invoice-{invoice_ref}"
    output_pdf_name = f"invoice-{invoice_ref}.pdf" # Define desired output name

    # 4. Handle existing output directory
    if os.path.exists(invoice_folder):
        if force_overwrite:
            logging.warning(f"Folder '{invoice_folder}' exists. Overwriting due to --force flag.")
            try:
                shutil.rmtree(invoice_folder)
            except OSError as e:
                logging.error(f"Failed to remove existing folder '{invoice_folder}': {e}")
                sys.exit(1)
        else:
            logging.error(f"Output folder '{invoice_folder}' already exists. Use --force to overwrite.")
            sys.exit(1)

    # 5. Check for template directory
    if not os.path.isdir(TEMPLATE_DIR):
        logging.error(f"Template directory '{TEMPLATE_DIR}' not found.")
        sys.exit(1)

    # 6. Copy template directory
    try:
        shutil.copytree(TEMPLATE_DIR, invoice_folder)
        logging.info(f"Copied template '{TEMPLATE_DIR}' to '{invoice_folder}'")
    except OSError as e:
        logging.error(f"Failed to copy template directory: {e}")
        sys.exit(1) # Exit if template copy fails

    # 7. Create the data file and compile
    try:
        create_tex_data_file(data, invoice_folder)
        compile_latex2(MAIN_TEX_FILE, invoice_folder, latex_cmd)

        # 8. Rename the output PDF
        generated_pdf = os.path.join(invoice_folder, MAIN_TEX_FILE.replace('.tex', '.pdf'))
        final_pdf_path = os.path.join(invoice_folder, output_pdf_name)
        if os.path.exists(generated_pdf):
            shutil.move(generated_pdf, final_pdf_path)
            logging.info(f"Successfully generated invoice: {final_pdf_path}")
        else:
            logging.warning(f"Expected PDF '{generated_pdf}' not found after compilation.")
            # Decide if this is an error or just a warning

    except (ValueError, IOError, FileNotFoundError, subprocess.CalledProcessError) as e:
        # Catch specific errors from previous steps
        logging.error(f"Invoice generation failed: {e}")
        # Optional: Clean up the partially created folder?
        # if os.path.exists(invoice_folder):
        #     logging.info(f"Cleaning up folder {invoice_folder} due to error.")
        #     shutil.rmtree(invoice_folder)
        sys.exit(1) # Exit with error status
    except Exception as e:
        # Catch any other unexpected errors
        logging.error(f"An unexpected error occurred during invoice generation: {e}")
        sys.exit(1)
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

    generate_invoice2(json_file, args.force, args.latex_cmd)
