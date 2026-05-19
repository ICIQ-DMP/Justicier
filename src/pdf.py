import locale
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import PyPDF2
from pypdf import PdfReader, PdfWriter

from custom_except import UndefinedRegularSalaryType
from data import unparse_month
from defines import RegularSalaryType
from filesystem import list_dir
from logger import get_logger

log = get_logger(__name__)


def get_dni(pdf_path: Path) -> str:
    reader = PdfReader(pdf_path)

    pattern = re.compile("[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]")

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()

        if not text:
            continue

        match = pattern.search(text)
        if not match:
            continue

        dni = match.group(0)
        return dni
    raise ValueError("DNI could not be detected in PDF " + str(pdf_path))


def write_page(page: PyPDF2.PageObject, path: Path) -> None:
    writer = PdfWriter()
    writer.add_page(page)

    with open(path, "wb+") as output_pdf:
        writer.write(output_pdf)


def get_matching_pages(
    pdf_path: Path, query_string: str, pattern: str = r"\d{2}/\d{8}-\d{2}"
) -> List[Tuple[PyPDF2.PageObject, int]]:
    reader = PdfReader(pdf_path)

    pattern = re.compile(pattern)
    pages = []

    for page_num, page in enumerate(reader.pages):
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


def get_matching_page(
    pdf_path: Path, query_string: str, pattern: str = r"\d{2}/\d{8}-\d{2}"
) -> PyPDF2.PageObject:
    reader = PdfReader(pdf_path)

    pattern = re.compile(pattern)

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        match = pattern.findall(text)
        if not match:
            continue

        match_selected = None
        for match_i in match:
            if str(match_i) == query_string:
                match_selected = match_i

        if match_selected is not None:
            return page

    raise ValueError(
        "The string " + query_string + " can't be found in the file " + str(pdf_path)
    )


def parse_dates_from_delayed_salary(page: PyPDF2.PageObject) -> tuple[datetime, datetime]:
    query_str = r"\d{1,2}\s+(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)\s+20\d{2}\s+a\s+\d{1,2}\s+(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)\s+20\d{2}"
    pattern = re.compile(query_str, re.MULTILINE)

    text = page.extract_text()
    if not text:
        pass  # TODO exceptions

    match = pattern.search(text)
    if not match:
        pass  # TODO exceptions

    match = match.group(0)
    match = match.replace("\n", "")

    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")

    start_str, end_str = match.split(" a ")

    start_date = datetime.strptime(start_str.strip(), "%d %B %Y")
    end_date = datetime.strptime(end_str.strip(), "%d %B %Y")
    return start_date, end_date


def is_monthly_salary(salary_page: PyPDF2.PageObject) -> bool:
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


def is_settlement_salary(salary_page: PyPDF2.PageObject) -> bool:
    text = salary_page.extract_text()
    if not text:
        return False

    pattern = r"Vacaciones Finiquito"
    pattern = re.compile(pattern)

    match = pattern.findall(text)
    if match:
        return True
    return False


def parse_regular_salary_type(salary_page: PyPDF2.PageObject) -> RegularSalaryType:
    if is_monthly_salary(salary_page):
        return RegularSalaryType.MONTHLY
    elif is_settlement_salary(salary_page):
        return RegularSalaryType.SETTLEMENT
    else:
        raise UndefinedRegularSalaryType("The type was not recognized")


def merge_pdfs(pdf_paths: List[Path], output_path: Path, all_pages: bool = False) -> None:
    """
    Merge multiple PDF files into a single PDF.

    :param pdf_paths: List of paths to PDF files to merge.
    :param output_path: Path to save the merged PDF.
    """
    pdfWriter = PyPDF2.PdfWriter()
    for filename in pdf_paths:
        pdf_file = open(filename, "rb")
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        if all_pages:
            for i in range(len(pdf_reader.pages)):
                pdfWriter.add_page(pdf_reader.pages[i])
        else:
            pdfWriter.add_page(pdf_reader.pages[0])
    f = open(output_path, "wb")
    pdfWriter.write(f)
    f.close()


def is_date_present_in_rlc_delay(delay_begin: datetime, delay_end: datetime, document_path: Path) -> bool:
    reader = PdfReader(document_path)
    query_string = (
        unparse_month(delay_begin)
        + "/"
        + str(delay_begin.year)
        + " - "
        + unparse_month(delay_end)
        + "/"
        + str(delay_end.year)
    )
    pattern = re.compile(query_string)

    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        match = pattern.findall(text)
        if not match:
            continue

        log.debug("Detected this matches: " + str(match))
        for match_i in match:
            if match_i.__eq__(query_string):
                return True

    return False


def compact_folder(path_folder: Path) -> None:
    """
    Gets a path to a folder with only PDF files in it.
    Merges all PDFs into a single file at path_folder.pdf, then removes the folder.
    """
    names = list_dir(path_folder)
    if len(names) == 0:
        log.warning(
            "Refusing to compact folder "
            + str(path_folder)
            + " because it is empty. Aborting compression."
        )
        return

    names.sort()
    paths = [path_folder / name for name in names]
    merge_pdfs(paths, path_folder.parent / (path_folder.name + ".pdf"), True)
    shutil.rmtree(path_folder)


def merge_equal_files_from_two_folders(folder1: Path, folder2: Path, folder_out: Path) -> None:
    log.info(
        f"Merging files with same name in folders {folder1} and {folder2} and outputting them in "
        f"{folder_out}."
    )
    files1 = list_dir(folder1)
    if len(files1) == 0:
        log.warning(
            f"Refusing to compact folders because {folder1} is empty. Aborting compression."
        )
        return
    files2 = list_dir(folder2)
    if len(files2) == 0:
        log.warning(
            f"Refusing to compact folders because {folder2} is empty. Aborting compression."
        )
        return

    for i in range(len(files1)):
        for j in range(len(files2)):
            if files1[i] == files2[j]:
                path1 = folder1 / files1[i]
                path2 = folder2 / files2[j]
                out_path = folder_out / files1[i]
                log.info(f"Matched {path1} with {path2} and merging into {out_path}.")
                merge_pdfs([path1, path2], out_path)
