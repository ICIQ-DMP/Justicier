import datetime
import re
import os
from pathlib import Path

from pypdf import PdfReader, PdfWriter
import pypdf
import re
import argparse


def get_matching_page(pdf_path: str, query_string: str, pattern: str = r"\d{2}/\d{8}-\d{2}") -> pypdf.PageObject:
    # Open PDF
    reader = PdfReader(pdf_path)

    # Define regex pattern to search for "NN/NNNNNNNN-NN" and extract SS number
    pattern = re.compile(pattern)

    for page_num, page in enumerate(reader.pages):
        # Get text of the page
        text = page.extract_text()

        if not text:
            continue

        match = pattern.search(text)
        if not match:
            continue

        match = match.group(0)  # TODO: ensure only one match per page, error otherwise
        if match.__eq__(query_string):
            return page

    raise ValueError("The string " + query_string + " can't be found in the file " + pdf_path)


def get_dni(pdf_path: str) -> str:
    # Open PDF
    reader = PdfReader(pdf_path)

    # Define regex pattern to search for "Z1234567Z or 12345678Z" and extract dni number
    pattern = re.compile("[A-Z]\d{7}[A-Z]|\d{8}[A-Z]")

    for page_num, page in enumerate(reader.pages):
        # Get text of the page
        text = page.extract_text()

        if not text:
            continue

        match = pattern.search(text)
        if not match:
            continue

        #if len(match.group) > 1:
        #    raise ValueError("More than one match for dni")
        dni = match.group(0)
        return dni
    raise ValueError("not found")


def clean_naf(naf):
    "Removes symbols that are not numbers in a SS number"
    return naf.replace("/", "").replace("-", "")


def write_page(page: pypdf.PageObject, naf, path):
    # Create a new PDF with only this page
    writer = PdfWriter()
    writer.add_page(page)

    with open(path, "wb+") as output_pdf:
        writer.write(output_pdf)
    pass


def validate_naf(value):
    """Validate that NAF has NAF format"""

    pattern = r"\d{2}/\d{8}-\d{2}"
    match = re.search(pattern, value)

    if not match:
        raise argparse.ArgumentTypeError("NAF must be in NAF format. Example: 43/12345678-20")
    return value


def parse_date(value, pattern=r"^\d{4}_[0-1][0-9]$", format="%Y_%m"):
    """Validate date format YYYY-MM"""

    if not re.match(pattern, value):
        raise argparse.ArgumentTypeError("Date must be in YYYY_MM format")

    return datetime.datetime.strptime(value, format)


def parse_arguments():
    """Parse and validate command-line arguments"""
    parser = argparse.ArgumentParser(description="Process NAF and date range.")

    parser.add_argument("-n", "--naf", type=validate_naf, required=True, help="NAF (SS security number)")
    parser.add_argument("-b", "--begin", type=parse_date, required=True, help="Begin date (YYYY-MM)")
    parser.add_argument("-e", "--end", type=parse_date, required=True, help="End date (YYYY-MM)")

    args = parser.parse_args()

    # Return data as a structured dictionary
    return args


def list_dir(input_folder):
    """Returns a list of all file names in the ./input/salaries directory."""
    # Ensure the input_folder is a valid directory
    if not os.path.isdir(input_folder):
        raise ValueError("input folder in list_files function is not a directory or can't be accessed" + input_folder)

    # List all files in the directory
    file_names = [os.path.basename(file) for file in os.listdir(input_folder)]

    return file_names


if __name__ == "__main__":
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Get the directory of main.py
    input_folder = os.path.join(root_dir, "input")  # Navigate to ./input/_salaries
    salaries_folder = os.path.join(input_folder, "_salaries")
    bankproofs_folder = os.path.join(input_folder, "_bank_proofs")

    # Parse args
    args = parse_arguments()

    # Ensure output directory exists
    os.makedirs(os.path.join(root_dir, "output"), exist_ok=True)
    output_dir = os.path.join(root_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    naf_dir = os.path.join(output_dir, clean_naf(args.naf))
    os.makedirs(naf_dir, exist_ok=True)

    naf_to_dni = {}

    # Salaries
    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    salary_files = list_dir(salaries_folder)
    if ".gitignore" in salary_files:
        salary_files.remove(".gitignore")

    # Select all salary sheets that are in range with the date (begin and end date included)
    salary_files_selected = []
    for salary_file in salary_files:
        dir_date = parse_date(salary_file[:7])
        if args.begin <= dir_date <= args.end:
            salary_files_selected.append(salary_file)

    # Write sheets to NAF folder that match the supplied NAF
    for salary_file in salary_files_selected:
        page = get_matching_page(os.path.join(salaries_folder, salary_file), args.naf)
        current_output_path = os.path.join(naf_dir, "salary_" + clean_naf(args.naf) + "_" + salary_file[:7] + ".pdf")
        write_page(page, args.naf, current_output_path)
        dni = get_dni(current_output_path)
        #print("dni from employee " + args.naf + "is " + dni)
        naf_to_dni[args.naf] = dni


    # Bank proofs
    # List all file names in the _bank_proofs folder, in the ./input folder and remove undesired files
    bankproofs_folders = list_dir(bankproofs_folder)
    if ".gitignore" in bankproofs_folders:
        bankproofs_folders.remove(".gitignore")

    # Select all bankproof folder that are in range with the date (begin and end date included)
    bankproof_folders_selected = []
    for bankproof_folder in bankproofs_folders:
        dir_date = parse_date(bankproof_folder[:6], r"^[0-1][0-9]\d{4}$", "%m%Y")
        if args.begin <= dir_date <= args.end:
            bankproof_folders_selected.append(bankproof_folder)

    # Write sheets to NAF folder that match the DNI
    for bankproof_folder in bankproof_folders_selected:
        bank = " ".join(bankproof_folder.split(" ")[1:])
        if bank.__eq__("BBVA"):
            for bankproof_file in list_dir(os.path.join(bankproofs_folder, bankproof_folder)):
                try:
                    page = get_matching_page(os.path.join(bankproofs_folder, bankproof_folder, bankproof_file), naf_to_dni[args.naf])
                except ValueError:
                    continue
                write_page(page, args.naf, os.path.join(naf_dir, bankproof_file))

        elif bank.__eq__("LA CAIXA"):
            file_name = list_dir(os.path.join(bankproofs_folder, bankproof_folder))[0]
            try:
                page = get_matching_page(os.path.join(bankproofs_folder, bankproof_folder, file_name),
                                         naf_to_dni[args.naf], "[A-Z]\d{7}[A-Z]|\d{8}[A-Z]")
            except ValueError as e:
                print(e)
                continue
            write_page(page, args.naf, os.path.join(naf_dir, file_name))
        else:
            print("bad bank")





