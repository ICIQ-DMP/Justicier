from datetime import datetime
import shutil
from typing import Union, Dict

import pandas as pd
from pypdf import PdfReader, PdfWriter
import pypdf
import re
import json

from arguments import parse_arguments, parse_date
from defines import *
from filesystem import *
from NAF import NAF
from logger import get_logger


def month_range_dict(begin: datetime, end: datetime) -> Dict[int, bool]:
    result = {}
    current = datetime(begin.year, begin.month, 1)

    while current <= end:
        key = str(current.year * 100 + current.month)
        result[key] = False
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return result


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

        match = pattern.findall(text)
        if not match:
            continue

        match_selected = None
        for match_i in match:
            if match_i.__eq__(query_string):
                match_selected = match_i

        if match_selected is not None:
            return page

    raise ValueError("The string " + query_string + " can't be found in the file " + pdf_path)


def get_dni(pdf_path: str) -> str:
    # Open PDF
    reader = PdfReader(pdf_path)

    # Define regex pattern to search for "Z1234567Z or 12345678Z" and extract dni number
    pattern = re.compile("[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]")

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


def write_page(page: pypdf.PageObject, path):
    # Create a new PDF with only this page
    writer = PdfWriter()
    writer.add_page(page)

    with open(path, "wb+") as output_pdf:
        writer.write(output_pdf)
    pass


def build_naf_to_dni(path):
    # Read the Excel file, skipping the first 3 rows
    df = pd.read_excel(path, skiprows=3, header=None)

    # Column C = index 2 (DNI), Column D = index 3 (NAF)
    dni_col = df[2]
    naf_col = df[3]

    # Replace the 11th character in each NAF
    def parse_naf(naf):
        return NAF(naf)

    naf_fixed = naf_col.apply(parse_naf)

    return dict(zip(naf_fixed, dni_col))


def build_naf_to_name_and_surname(path):
    # Read the Excel file, skipping the first 3 rows
    df = pd.read_excel(path, skiprows=3, header=None)

    # Column C = index 2 (DNI), Column D = index 3 (NAF)
    name_col = df[1]
    naf_col = df[3]

    # Replace the 11th character in each NAF
    def parse_naf(naf):
        return NAF(naf)

    naf_fixed = naf_col.apply(parse_naf)

    return dict(zip(naf_fixed, name_col))


def flatten_dirs(folder_to_flat):
    # List all file names in the _bank_proofs folder, in the ./input folder and remove undesired files
    folders_year = list_dir(folder_to_flat)
    if ".gitignore" in folders_year:
        folders_year.remove(".gitignore")
    # Flatten year directories (flat list of document for all years)
    flatted_folders = []
    for folder_year in folders_year:
        for folder in list_dir(os.path.join(folder_to_flat, folder_year)):
            flatted_folders.append(os.path.join(folder_year, folder))

    return flatted_folders


def process_salaries(salaries_folder_path, naf_dir, naf, begin, end):
    num_salaries_found = 0
    months_found = month_range_dict(begin, end)

    # Salaries
    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    salary_files = flatten_dirs(salaries_folder_path)

    # Select all salary sheets that are in range with the date (begin and end date included)
    salary_files_selected = []
    for salary_file in salary_files:
        dir_date = parse_date("20" + salary_file.split("/")[1][:4], "%Y%m")
        if begin <= dir_date <= end:
            salary_files_selected.append(salary_file)
            logger.debug("Salary file " + salary_file + " is selected, because its date is " + dir_date.__str__() + ".")

    # Write sheets to NAF folder that match the supplied NAF
    salary_files_selected.sort()
    for salary_file in salary_files_selected:
        try:
            page = get_matching_page(os.path.join(salaries_folder_path, salary_file), naf.slash_dash_str())
            current_output_path = os.path.join(naf_dir, SALARIES_OUTPUT_NAME,
                                               salary_file.split("/")[1])
            logger.info("Detected NAF " + naf.__str__() + " in PDF " + salary_file + ". Saving page in " +
                        current_output_path.__str__() + ".")
            write_page(page, current_output_path)
            months_found[salary_file.split("_")[0]] = True
        except ValueError as e:
            logger.debug("NAF " + naf.__str__() + " was not detected in PDF " + salary_file + ".")

    for key in months_found.keys():
        if not months_found[key]:
            logger.warning("Salary for NAF " + str(naf) + " was not found during period " + str(key))



def process_proofs(proofs_folder_path, naf_dir, naf, begin, end, naf_to_dni):
    # Flatten year directories (flat list of document for all years)
    all_bankproof_folders = flatten_dirs(proofs_folder_path)

    # Select all bankproof folder that are in range with the date (begin and end date included)
    bankproof_folders_selected = []
    for bankproof_folder in all_bankproof_folders:
        dir_date = parse_date(bankproof_folder.split("/")[1][:6], "%m%Y")
        if begin <= dir_date <= end:
            bankproof_folders_selected.append(bankproof_folder)
            logger.debug(
                "Proof folder " + bankproof_folder + " is selected, because its date is " + dir_date.__str__() + ".")

    # Write sheets to NAF folder that match the DNI
    proofs_dir = os.path.join(naf_dir, PROOFS_OUTPUT_NAME)
    for bankproof_folder in bankproof_folders_selected:
        bank = "_".join(bankproof_folder.split("_")[1:])
        logger.debug("Working with folder " + bankproof_folder + ". Bank type is " + bank)
        if (bank.__eq__("BBVA") or bank.__eq__("BBVA_endarreriments") or bank.__eq__("BBVA_endarreriments") or
                bank.__eq__("BBVA_FINIQUITO")):
            for bankproof_file in list_dir(os.path.join(proofs_folder_path, bankproof_folder)):
                try:
                    page = get_matching_page(os.path.join(proofs_folder_path, bankproof_folder, bankproof_file),
                                             naf_to_dni[naf], "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]")
                except ValueError as e:
                    # print("NAF " + args.naf + " not detected in " + bankproof_file + ". Error: " + e.__str__())
                    continue
                output_path = os.path.join(proofs_dir, bankproof_file)
                logger.info(
                    "NAF " + naf.__str__() + " was detected in " + bankproof_file + ". Writing page to " + output_path.__str__()
                    + ".")
                write_page(page, output_path)

        elif bank.__eq__("LA_CAIXA") or bank.__eq__("LA_CAIXA_EXTRA") or bank.__eq__("LA_CAIXA_endarreriments"):
            file_name = list_dir(os.path.join(proofs_folder_path, bankproof_folder))[0]
            try:
                page = get_matching_page(os.path.join(proofs_folder_path, bankproof_folder, file_name),
                                         naf_to_dni[naf], "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]")
            except ValueError as e:
                # print("NAF " + naf + " not detected in " + file_name + ". Error: " + e.__str__())
                continue
            output_path = os.path.join(proofs_dir, file_name)
            logger.info(
                "NAF " + naf.__str__() + " was detected in " + file_name + ". Writing page to " + output_path.__str__() + ".")
            write_page(page, output_path)
        else:
            logger.warning(bank.__str__() + " is a bad bank.")


def process_contracts(contracts_folder_path, naf_dir, naf, begin, end):
    found = 0
    # Salaries
    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    contracts_files = list_dir(contracts_folder_path)
    contracts_files.sort()
    for contracts_file in contracts_files:
        naf_dirty = NAF(contracts_file.split("_")[0])
        dates = contracts_file.split(".")[0].split("_")
        logger.debug("contract file: " + contracts_file)
        begin_date = parse_date("20" + dates[1], "%Y%m")
        if len(dates) == 3:  # Contract is temporary; has end date
            end_date = parse_date("20" + dates[1], "%Y%m")
        elif len(dates) == 2:  # Contract is undefined; has no end date
            end_date = datetime.max
        else:
            logger.warning("expected 3 fields in the name of the file " + contracts_file + " but " +
                           str(len(dates)) + " have been found. The file will be ignored until it has proper format.")
            continue

        if naf_dirty.__eq__(naf):
            logger.debug(
                "NAF " + naf_dirty.__str__() + " of file " + contracts_file + " coincides with queried NAF. Checking dates...")
            # Select which contracts are valid during the range in the arguments
            # This conditional means that we select the contract if there is any coincidence in the range defined by
            # (begin, end) and (end_date, begin_date).
            if begin <= end_date and begin_date <= end:
                logger.info(
                    contracts_file + " with date " + begin_date.__str__() + ", " + end_date.__str__() + "is in range "
                                                                                                        "of " + begin.__str__() + ", " + end.__str__() + ". Copying it to " + naf_dir)
                try:
                    shutil.copy(src=os.path.join(contracts_folder_path, contracts_file),
                                dst=os.path.join(naf_dir, CONTRACTS_OUTPUT_NAME))
                    found = 1
                except Exception as e:
                    logger.critical(e)
                    exit(2)
    if not found:
        logger.warning("Contract not found with NAF " + str(naf))


def process_RNTs(rnts_folder_path, naf_dir, naf, begin, end):
    rnt_files_selected = []
    rnt_files = flatten_dirs(rnts_folder_path)
    rnt_files.sort()
    for rnt_file in rnt_files:
        file_date = parse_date("20" + rnt_file.split("/")[1][:4], "%Y%m")
        if begin <= file_date <= end:
            rnt_files_selected.append(rnt_file)
            logger.debug("RNT file " + rnt_file + " is selected, because its date is " + file_date.__str__() + ".")

    rnt_files_selected.sort()
    for rnt_file in rnt_files_selected:
        try:
            page = get_matching_page(os.path.join(rnts_folder_path, rnt_file), naf.__str__(), "\\d{12}")
            current_output_path = os.path.join(naf_dir, RNTS_OUTPUT_NAME,
                                               rnt_file.split("/")[1])
            logger.debug("Detected NAF " + naf.__str__() + " in PDF " + rnt_file.__str__() + ". Saving page in " +
                         current_output_path.__str__() + ".")
            write_page(page, current_output_path)
        except ValueError as e:
            logger.warning(
                "NAF " + naf.__str__() + " was not detected in PDF " + rnt_file.__str__() + "or another error happened."
                                                                                            "The file " + rnt_file.__str__() + " will be ignored. The internal error trace is " + e.__str__())


def process_RLCs(rlcs_folder_path, naf_dir, naf, begin, end):
    rlc_files = flatten_dirs(rlcs_folder_path)
    rlc_files.sort()
    for rlc_file in rlc_files:
        full_date = rlc_file[:4] + "20" + rlc_file[4:6]
        file_date = parse_date(full_date, "%m%d%Y")
        if begin <= file_date <= end:
            logger.info("RNT file " + rlc_file + " will be copied, because its date is " + file_date.__str__() + ".")
            shutil.copy(src=os.path.join(rlcs_folder_path, rlc_file), dst=os.path.join(naf_dir, RLCS_OUTPUT_NAME))


if __name__ == "__main__":

    args = parse_arguments()

    # Build dictionaries to translate NAF to different identifier data
    NAF_TO_DNI = build_naf_to_dni(NAF_DATA_PATH)
    NAF_TO_NAME = build_naf_to_name_and_surname(NAF_DATA_PATH)

    NOW = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    # Ensure existence of output directory structure
    os.makedirs(GENERAL_OUTPUT_FOLDER, exist_ok=True)

    # Ensure existence of .gitignore
    gitignore_path = os.path.join(GENERAL_OUTPUT_FOLDER, '.gitignore')
    gitignore_content = "*\n!.gitignore\n"
    with open(gitignore_path, 'w+') as f:
        f.write(gitignore_content)

    os.makedirs(ADMIN_LOG_FOLDER, exist_ok=True)

    # Admin logs
    ADMIN_LOG_PATH = os.path.join(ADMIN_LOG_FOLDER, NOW + "_" +
                                  args.author + "_" +
                                  args.naf.__str__()
                                  + "_" + NAF_TO_NAME[args.naf] + "_" +
                                  args.begin.strftime("%Y-%m") + "-" + args.end.strftime("%Y-%m") + ".log.txt")

    CURRENT_USER_FOLDER: str = os.path.join(GENERAL_OUTPUT_FOLDER, args.author)
    os.makedirs(CURRENT_USER_FOLDER, exist_ok=True)

    justification_name = (NOW + " " + str(args.naf) + " " + NAF_TO_NAME[args.naf] + " " + str(args.begin) + "-" +
                          str(args.end))

    JUSTIFICATION_FOLDER = os.path.join(CURRENT_USER_FOLDER, justification_name)
    os.makedirs(JUSTIFICATION_FOLDER, exist_ok=True)

    USER_REPORT_FILE = os.path.join(JUSTIFICATION_FOLDER, NOW + "_" +
                                    args.naf.__str__()
                                    + "_" + NAF_TO_NAME[args.naf] + "_" +
                                    args.begin.strftime("%Y-%m") + "-" + args.end.strftime("%Y-%m") + ".log.txt")

    # Create logger with debugging enabled
    logger = get_logger(USER_REPORT_FILE, ADMIN_LOG_PATH, debug_mode=True)

    os.makedirs(os.path.join(JUSTIFICATION_FOLDER, SALARIES_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(JUSTIFICATION_FOLDER, PROOFS_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(JUSTIFICATION_FOLDER, CONTRACTS_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(JUSTIFICATION_FOLDER, RNTS_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(JUSTIFICATION_FOLDER, RLCS_OUTPUT_NAME), exist_ok=True)

    try:
        NAF_TO_DNI[args.naf]
    except KeyError as e:
        logger.critical("Error: NAF " + args.naf + " was not found in database. Update the file ./input/NAF_DNI.xlsx")
        exit(1)

    process_salaries(SALARIES_FOLDER, JUSTIFICATION_FOLDER, args.naf, args.begin, args.end)

    process_proofs(PROOFS_FOLDER, JUSTIFICATION_FOLDER, args.naf, args.begin, args.end, NAF_TO_DNI)

    process_contracts(CONTRACTS_FOLDER, JUSTIFICATION_FOLDER, args.naf, args.begin, args.end)

    process_RNTs(RNTS_FOLDER, JUSTIFICATION_FOLDER, args.naf, args.begin, args.end)

    #process_RLCs(RLCS_FOLDER, JUSTIFICATION_FOLDER, args.naf, args.begin, args.end)
