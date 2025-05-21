import argparse
import locale
import os.path
import sys
from datetime import datetime
import shutil
from logging import LoggerAdapter
from typing import Union, Dict, Tuple

import PyPDF2
import pandas as pd
from pyfiglet import Figlet
from pypdf import PdfReader, PdfWriter
import pypdf
import re
import json
from pypdf import PdfMerger

from arguments import parse_arguments, parse_date, process_arguments
from defines import *
from filesystem import *
from NAF import NAF, build_naf_to_dni, build_naf_to_name_and_surname, NAF_TO_DNI, NAF_TO_NAME
from logger import get_raw_logger, get_process_logger, unformatted_logger, get_logger
from custom_except import ArgumentAuthorError, ArgumentDateError, ArgumentNafNotPresent, ArgumentNafInvalid


def get_monthly_result_structure(begin: datetime, end: datetime) -> Dict[str, Tuple[bool, bool, bool]]:
    result = {}
    current = datetime(begin.year, begin.month, 1)

    while current <= end:
        key = datetime.strptime(str(current.year * 100 + current.month), "%Y%m")
        result[key] = [False, False, False]  # Monthly salary found, RLC L00N found, RLC L00P found
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return result


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

        dni = match.group(0)
        return dni
    raise ValueError("DNI could not be detected in PDF " + pdf_path)


def write_page(page: pypdf.PageObject, path):
    # Create a new PDF with only this page
    writer = PdfWriter()
    writer.add_page(page)

    with open(path, "wb+") as output_pdf:
        writer.write(output_pdf)
    pass


def flatten_dirs(folder_to_flat):
    # List all file names in the _bank_proofs folder, in the ./input folder and remove undesired files
    subfolder_year = list_dir(folder_to_flat)
    if ".gitignore" in subfolder_year:
        subfolder_year.remove(".gitignore")
    # Flatten year directories (flat list of document for all years)
    flatted_folders = []
    for folder_year in subfolder_year:
        for folder in list_dir(os.path.join(folder_to_flat, folder_year)):
            flatted_folders.append(os.path.join(folder_year, folder))

    return flatted_folders


def get_matching_page(pdf_path, query_string: str, pattern: str = r"\d{2}/\d{8}-\d{2}") -> pypdf.PageObject:
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


def parse_dates_from_delayed_salary(page):
    # Define regex pattern to search for "NN/NNNNNNNN-NN" and extract SS number
    query_str = "Atrasos 20.*"  # Heuristic is to find "Atrasos" but appears two times on each page, so we are
    # restricting the search with the beginning of the year, which appears in the line that
    # we are interested in, which contains the date.
    pattern = re.compile(query_str)

    text = page.extract_text()
    if not text:
        pass  # TODO exceptions

    match = pattern.findall(text)
    if not match:
        pass  # TODO exceptions

    if len(match) > 1:
        base_logger.error("More than one match was detected in page, defaulting to the first match detected")
    match = match[0]

    # Set locale to Spanish (you may need to install it depending on your OS)
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    date_text = " ".join(match.__str__().split("-")[1].strip(" ").split(" ")[0:-1])

    # Split the string by ' a '
    start_str, end_str = date_text.split(' a ')

    # Parse both dates
    start_date = datetime.strptime(start_str.strip(), '%d %B %Y')
    end_date = datetime.strptime(end_str.strip(), '%d %B %Y')
    return start_date, end_date


def is_monthly_salary(salary_page):
    # TODO DEPRECATED: we use the file name of the salary to know if it is monthly
    # Get text of the page
    text = salary_page.extract_text()
    if not text:
        return False

    pattern = r".*Mensual -.*"
    pattern = re.compile(pattern)

    match = pattern.findall(text)
    if not match:
        return False

    match_selected = None
    for match_i in match:
        if match_i.__eq__(pattern):
            match_selected = match_i

    if match_selected is not None:
        return True


def parse_salary_type(salary_file_path):
    logger = get_process_logger(base_logger, "Salaries and RLCs")
    parsed = salary_file_path[::-1].split("/")[0][::-1].split(".")[0].split("_")[1]
    logger.debug("Data parsed from filename is: " + parsed)
    t = SalaryType(parsed)
    logger.debug("Type detected is: " + t.__str__())
    return t


def parse_year_salary_path(salary_file):
    return datetime.strptime("20" + salary_file.split("/")[1].split("_")[0][:2], "%Y")


def parse_month_salary_path(salary_file):
    return datetime.strptime(salary_file[::-1].split("/")[0][::-1].split("_")[0][2:], "%m")


def parse_date_from_key(key: str):
    return datetime.strptime(key, "%Y%m")


def unparse_month(date_obj):
    if date_obj.month >= 10:
        return date_obj.month.__str__()
    else:
        return "0" + date_obj.month.__str__()


def unparse_date(d, separator="-"):
    return unparse_month(d) + separator + d.year.__str__()


def parse_date_from_salary_filename(salary_path):
    return datetime.strptime("20" + salary_path[::-1].split("/")[0][::-1].split(".")[0].split("_")[0], "%Y%m")


def parse_salary_filename_from_salary_path(salary_path):
    return os.path.basename(salary_path)


def process_rlc_l00(salary_date, rlc_folder_path, naf_dir, months_found, rlc_type: str):
    logger = get_process_logger(base_logger, "Salaries and RLCs")
    month = unparse_month(salary_date)
    year = salary_date.year.__str__()
    n_name = month + "_L00" + rlc_type + "01.pdf"
    rlc_n_path = os.path.join(rlc_folder_path, year, n_name)
    if os.path.exists(rlc_n_path):
        logger.debug("The RLC " + rlc_n_path + " is present.")
        if rlc_type.__eq__("N"):
            months_found[salary_date][1] = True  # RLC L00 of type N is found
        elif rlc_type.__eq__("P"):
            months_found[salary_date][2] = True  # RLC L00 of type P is found
        return rlc_n_path
    else:
        logger.error("Monthly salary was found, but the expected L00 RLC of type " + rlc_type + " was "
                                                                                                "not found in the "
                                                                                                "expected location "
                                                                                                "" + str(
            rlc_n_path) + ". Skipping merge of this salary file.")
        raise ValueError("File was not detected")  # TODO custom except


def merge_pdfs(pdf_paths, output_path):
    """
    Merge multiple PDF files into a single PDF.

    :param pdf_paths: List of paths to PDF files to merge.
    :param output_path: Path to save the merged PDF.
    """
    # Assigning the pdfWriter() function to pdfWriter.
    pdfWriter = PyPDF2.PdfWriter()
    for filename in pdf_paths:  # Starting a for loop.
        pdf_file = open(filename, 'rb')  # Opens each of the file paths in filename variable.
        # Reads each of the files in the new variable you've created above and stores into memory.
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        page = pdf_reader.pages[0]  # Documents of only one page, so we are interested in the first
        pdfWriter.add_page(page)  # Adds each of the PDFs it's read to a new page.
    f = open(output_path, 'wb')
    # Writing the output file using the pdfWriter function.
    pdfWriter.write(f)
    f.close()


def compact_folder(path_folder):
    """
    Gets a path to a folder with only PDF files in it.
    Read all PDFs and merge them all into a single PDF.
    obtain parent of path_folder
    obtain filename of path_folder
    Remove folder path_folder
    create merged PDF path_folder + ".pdf"
    """
    paths = list_dir(path_folder)
    paths.sort()
    for i in range(len(paths)):
        paths[i] = os.path.join(path_folder, paths[i])
    merge_pdfs(paths, path_folder + ".pdf")
    shutil.rmtree(path_folder)


def is_date_present_in_rlc_delay(delay_begin, delay_end, document_path):
    reader = PdfReader(document_path)
    query_string = (unparse_month(delay_begin) + "/" + delay_begin.year.__str__() + " - " + unparse_month(delay_end)
                    + "/" + delay_end.year.__str__())
    pattern = re.compile(query_string)

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        match = pattern.findall(text)
        if not match:
            continue

        for match_i in match:
            if match_i.__eq__(query_string):
                return True

    raise ValueError("The string " + query_string + " can't be found in the file " + document_path)


def process_salaries_with_rlc(salaries_folder_path, rlc_folder_path, naf_dir, naf, begin, end):
    logger = get_process_logger(base_logger, "Salaries and RLCs")
    months_found = get_monthly_result_structure(begin, end)  # salary, RLC-N, RLC-P
    delay_salaries_found = 0

    # Salaries, RLC L00, RLC L03
    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    salary_files = flatten_dirs(salaries_folder_path)
    # Select all salary sheets that are in range with the date (begin and end date included)
    salary_files_selected = []
    for salary_file in salary_files:
        dir_date = parse_date_from_salary_filename(parse_salary_filename_from_salary_path(salary_file))
        if begin <= dir_date <= end:
            salary_files_selected.append(salary_file)
            logger.debug(
                "Salary file " + str(salary_file) + " is selected, because its date is " + unparse_date(dir_date,
                                                                                                        "-") + ".")

    # Write sheets to NAF folder that match the supplied NAF
    salary_files_selected.sort()
    for salary_file in salary_files_selected:
        salary_file_path = os.path.join(salaries_folder_path, salary_file)
        salary_file_name = parse_salary_filename_from_salary_path(salary_file_path)
        salary_date = parse_date_from_salary_filename(salary_file_name)
        logger
        try:
            salary_page = get_matching_page(salary_file_path, naf.slash_dash_str())
        except ValueError as exc:
            logger.debug("NAF " + naf.__str__() + " was not detected in PDF " + str(salary_file) +
                         ". Skipping document. Internal exception is: " + exc.__str__())
            continue

        salary_output_path = os.path.join(naf_dir, SALARIES_OUTPUT_NAME, salary_file_name)
        write_page(salary_page, salary_output_path)

        # Mark it as found
        months_found[salary_date][0] = True  # Monthly salary is found
        logger.info("Detected NAF " + naf.__str__() + " in PDF salary " + str(salary_file_path) + ". Saving page in " +
                    salary_output_path.__str__() + " and further processing it.")

        # Now check if salary_file is delay, so we need to proceed to L03 procedure
        salary_type = parse_salary_type(salary_file_path)
        if salary_type == SalaryType.DELAY:  # process L03 RLCs
            delay_salaries_found += 1
            logger.info("Salary file " + salary_file_path + " has been selected as delay salary for date " +
                        unparse_date(salary_date))
            try:
                delay_initial_date, delay_end_date = parse_dates_from_delayed_salary(salary_page)
            except ValueError as exc:
                logger.error("The delay date could not be parsed from the delay salary page. This document will be "
                             "skipped from search. The internal error is " + exc.__str__())
                continue
            logger.debug("Initial date is " + unparse_date(delay_initial_date, "-") + " and end date is " +
                         unparse_date(delay_end_date, "-"))

            rlc_partial_path = os.path.join(naf_dir, rlc_folder_path, salary_date.year.__str__(),
                                            unparse_month(salary_date) + "_L03")
            suffix = 1
            while suffix < 100:  # Accepting only suffix under 100
                if suffix < 10:
                    str_suffix = "0" + str(suffix)
                else:
                    str_suffix = str(suffix)
                rlc_path_n = rlc_partial_path + "N" + str_suffix + ".pdf"
                if not os.path.exists(rlc_path_n):
                    logger.debug("Breaking out of the bucle because " + rlc_path_n +
                                 "does not exist.")
                    break
                if is_date_present_in_rlc_delay(delay_initial_date, delay_end_date, rlc_path_n):
                    months_found[salary_date][1] = True  # Monthly salary is found
                    rlc_path_p = rlc_partial_path + "P" + str_suffix + ".pdf"
                    pdf_path_list = []
                    pdf_merged_name = salary_date.year.__str__() + unparse_month(
                        salary_date) + "_L03F" + str_suffix + ".pdf"
                    pdf_output_path = os.path.join(naf_dir, RLCS_OUTPUT_NAME, pdf_merged_name)
                    if not os.path.exists(rlc_path_p):
                        logger.debug("Breaking out of the bucle because " + rlc_path_p +
                                     "does not exist.")
                    months_found[salary_date][2] = True  # Monthly salary is found
                    pdf_path_list.append(salary_output_path)
                    pdf_path_list.append(rlc_path_n)
                    pdf_path_list.append(rlc_path_p)
                    merge_pdfs(pdf_path_list, pdf_output_path)
                    break
                if not os.path.exists(rlc_path_n):
                    logger.debug("Breaking out of the bucle because " + rlc_path_n +
                                 "does not exist.")
                suffix += 1
        elif salary_type == SalaryType.REGULAR:
            # Monthly salary, look for L00 RLC N & P
            logger.info("Salary file " + salary_file_path + " has been selected as regular salary for date " +
                        unparse_date(salary_date))
            try:
                rlc_n_path = process_rlc_l00(salary_date, rlc_folder_path, naf_dir, months_found, "N")
                logger.debug("Expected RLC N path is: " + rlc_n_path)
                rlc_p_path = process_rlc_l00(salary_date, rlc_folder_path, naf_dir, months_found, "P")
                logger.debug("Expected RLC P path is: " + rlc_p_path)
            except ValueError:
                logger.info("Any of the RLC documents (N or P) has not been found. The salary file " + salary_file_path
                            + " will be skipped.")
                continue

            pdf_path_list = [salary_output_path, rlc_n_path, rlc_p_path]
            pdf_merged_name = salary_date.year.__str__() + unparse_month(salary_date) + "_L00Merge.pdf"
            merge_pdfs(pdf_path_list, os.path.join(naf_dir, RLCS_OUTPUT_NAME, pdf_merged_name))

        elif salary_type.__eq__(SalaryType.EXTRA):  # Atrasos
            pass
        else:
            logger.error(
                "Detected type " + salary_type.__str__() + " that is not a recognized type. The current salary file "
                                                           "will be ignored")

    # Report
    salaries_found = 0
    for key in months_found.keys():
        if months_found[key][0]:
            salaries_found += 1
        if not months_found[key][0]:
            logger.warning("Salary for NAF " + str(naf) + " was not found during period " + unparse_date(key, "-"))
        elif not months_found[key][1]:
            logger.warning("RLC L00 N for NAF " + str(naf) + " was not found during period " + unparse_date(key, "-"))
        elif not months_found[key][2]:
            logger.warning("RLC L00 P for NAF " + str(naf) + " was not found during period " + unparse_date(key, "-"))

    if salaries_found != len(months_found.keys()):
        logger.info(
            "In the period from " + str(begin) + " to " + str(end) + " there are " + str(len(months_found.keys())) +
            " months, but only " + str(salaries_found) + " regular salaries were found.")

    logger.info(str(delay_salaries_found) + " delay salaries have been found.")


def process_proofs(proofs_folder_path, naf_dir, naf, begin, end, naf_to_dni):
    logger = get_process_logger(base_logger, "Bank proofs")
    # Flatten year directories (flat list of document for all years)
    all_bankproof_folders = flatten_dirs(proofs_folder_path)

    # Select all bankproof folder that are in range with the date (begin and end date included)
    bankproof_folders_selected = []
    for bankproof_folder in all_bankproof_folders:
        dir_date = parse_date(bankproof_folder.split("/")[1][:6], "%m%Y")
        if begin <= dir_date <= end:
            bankproof_folders_selected.append(bankproof_folder)
            logger.debug(
                "Proof folder " + bankproof_folder + " is selected, because its date is " + unparse_date(dir_date,
                                                                                                         "-") + ".")

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
    logger = get_process_logger(base_logger, "Contracts")
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
            logger.error("expected 3 fields in the name of the file " + contracts_file + " but " +
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
                    contracts_file + " with date " + unparse_date(begin_date, "-") + ", " + unparse_date(end_date,
                                                                                                         "-") + "is in range "
                                                                                                                "of " + unparse_date(
                        begin, "-") + ", " + unparse_date(end, "-") + ". Copying it to " + naf_dir)
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
    logger = get_process_logger(base_logger, "RNTs")
    rnt_files = flatten_dirs(rnts_folder_path)
    rnt_files.sort()
    for rnt_file in rnt_files:
        file_date = parse_date("20" + rnt_file.split("/")[1][:4], "%Y%m")
        if begin <= file_date <= end:
            rnt_file_name = rnt_file.split("/")[1]
            rnt_path = os.path.join(rnts_folder_path, file_date.year.__str__(), rnt_file_name)
            rnt_path_destination = os.path.join(naf_dir, RNTS_OUTPUT_NAME, rnt_file_name)
            logger.info("RNT file " + rnt_path.__str__() + " is selected, because its date is " +
                        unparse_date(file_date) + "."
                                                  " It will be copied into " + rnt_path_destination)
            shutil.copy(src=rnt_path,
                        dst=rnt_path_destination)


if __name__ == "__main__":
    args = process_arguments()

    CURRENT_USER_FOLDER, CURRENT_JUSTIFICATION_FOLDER, USER_REPORT_FILE, ADMIN_LOG_PATH, SUPERVISOR_LOG_PATH = (
        compute_paths(args))

    ensure_file_structure(CURRENT_USER_FOLDER, CURRENT_JUSTIFICATION_FOLDER)

    base_logger = get_logger(USER_REPORT_FILE, ADMIN_LOG_PATH, SUPERVISOR_LOG_PATH, debug_mode=True)
    raw_logger = get_process_logger(base_logger, "Initialization")

    figlet = Figlet(font='banner3-D')
    ascii_logo = "\n" + figlet.renderText('Justifly')
    raw_logger.info(ascii_logo)

    raw_logger.info(
        "\n***********************************************************************************************************************"
        "\n*                                                USER REQUEST DETAILS                                                 *"
        "\n***********************************************************************************************************************"
        "\n* Email of the user doing the request: " + args.author +
        "\n* NAF requested: " + args.naf.__str__() +
        "\n* Initial date: " + unparse_date(args.begin) +
        "\n* End date: " + unparse_date(args.end) +
        "\n***********************************************************************************************************************"
        "\n\n")



    process_salaries_with_rlc(SALARIES_FOLDER, RLCS_FOLDER, CURRENT_JUSTIFICATION_FOLDER, args.naf, args.begin,
                              args.end)
    salary_output_path = os.path.join(CURRENT_JUSTIFICATION_FOLDER, SALARIES_OUTPUT_NAME)
    if args.compact[DocType.SALARY]:
        compact_folder(salary_output_path)

    process_proofs(PROOFS_FOLDER, CURRENT_JUSTIFICATION_FOLDER, args.naf, args.begin, args.end, NAF_TO_DNI)
    proof_output_path = os.path.join(CURRENT_JUSTIFICATION_FOLDER, PROOFS_OUTPUT_NAME)
    if args.compact[DocType.PROOFS]:
        compact_folder(proof_output_path)

    process_contracts(CONTRACTS_FOLDER, CURRENT_JUSTIFICATION_FOLDER, args.naf, args.begin, args.end)
    contract_output_path = os.path.join(CURRENT_JUSTIFICATION_FOLDER, CONTRACTS_OUTPUT_NAME)
    if args.compact[DocType.CONTRACT]:
        compact_folder(contract_output_path)

    process_RNTs(RNTS_FOLDER, CURRENT_JUSTIFICATION_FOLDER, args.naf, args.begin, args.end)
    rnt_output_path = os.path.join(CURRENT_JUSTIFICATION_FOLDER, RNTS_OUTPUT_NAME)
    if args.compact[DocType.RNT]:
        compact_folder(rnt_output_path)