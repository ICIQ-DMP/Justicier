import locale
import logging
import os
import re
import shutil
from datetime import datetime
from typing import List, Tuple

import PyPDF2
from pypdf import PdfReader, PdfWriter

from data import unparse_month
from filesystem import list_dir
from logger import get_logger, get_logger_instance, get_process_logger
from custom_except import UndefinedRegularSalaryType
from defines import RegularSalaryType


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


def write_page(page: PyPDF2.PageObject, path):
    # Create a new PDF with only this page
    writer = PdfWriter()
    writer.add_page(page)

    with open(path, "wb+") as output_pdf:
        writer.write(output_pdf)
    pass


def get_matching_pages(pdf_path, query_string: str, pattern: str = r"\d{2}/\d{8}-\d{2}") -> List[Tuple[PyPDF2.PageObject, int]]:
    # Open PDF
    reader = PdfReader(pdf_path)

    # Define regex pattern to search for "NN/NNNNNNNN-NN" and extract SS number
    pattern = re.compile(pattern)
    pages = []

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
                break

        if match_selected is not None:
            pages.append((page, page_num))
    return pages


def get_matching_page(pdf_path, query_string: str, pattern: str = r"\d{2}/\d{8}-\d{2}") -> PyPDF2.PageObject:
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
    logger = get_process_logger(get_logger_instance(), "parse_dates_from_delayed_salary")
    # Define regex pattern to search for "NN/NNNNNNNN-NN" and extract SS number
    query_str = '\\d{1,2} (Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre) 20\\d{2} a \\d{1,2} (Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre) 20\\d{2}'  # Heuristic is to find "Atrasos" but appears two times on each page, so we are
    # restricting the search with the beginning of the year, which appears in the line that
    # we are interested in, which contains the date.
    pattern = re.compile(query_str)

    text = page.extract_text()
    if not text:
        pass  # TODO exceptions

    match = pattern.search(text)
    if not match:
        pass  # TODO exceptions

    logger.debug("Match is " + str(match))

    match = match.group(0)

    # Set locale to Spanish (you may need to install it depending on your OS)
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')

    # Split the string by ' a '
    start_str, end_str = match.split(' a ')

    # Parse both dates
    start_date = datetime.strptime(start_str.strip(), '%d %B %Y')
    end_date = datetime.strptime(end_str.strip(), '%d %B %Y')
    return start_date, end_date


def is_monthly_salary(salary_page):
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
    return False


def is_settlement_salary(salary_page):
    # Get text of the page
    text = salary_page.extract_text()
    if not text:
        return False

    pattern = r"Vacaciones Finiquito"
    pattern = re.compile(pattern)

    match = pattern.findall(text)
    if match:
        return True
    return False


def parse_regular_salary_type(salary_page):
    if is_monthly_salary(salary_page):  # For optimization first monthly because it is more common
        return RegularSalaryType.MONTHLY
    elif is_settlement_salary(salary_page):
        return RegularSalaryType.SETTLEMENT
    else:
        raise UndefinedRegularSalaryType("The type was not recognized")


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


def is_date_present_in_rlc_delay(delay_begin, delay_end, document_path):
    logger = get_process_logger(get_logger_instance(), "Salaries and RLCs L03 is_date_present_in_rlc_delay")
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

        logger.debug("Detected this matches: " + str(match))
        for match_i in match:
            if match_i.__eq__(query_string):
                return True

    return False


def compact_folder(path_folder):
    """
    Gets a path to a folder with only PDF files in it.
    Read all PDFs and merge them all into a single PDF.
    obtain parent of path_folder
    obtain filename of path_folder
    Remove folder path_folder
    create merged PDF path_folder + ".pdf"
    """
    logger = get_process_logger(get_logger_instance(), "Folder compactation")
    paths = list_dir(path_folder)
    if len(paths) == 0:
        logger.warning("Refusing to compact folder " + path_folder + " because it is empty. Aborting compression.")
        return

    paths.sort()
    for i in range(len(paths)):
        paths[i] = os.path.join(path_folder, paths[i])
    merge_pdfs(paths, path_folder + ".pdf")
    shutil.rmtree(path_folder)
