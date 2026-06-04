# justicier - Automated employee justifications
# Copyright (C) 2026  Aleix Mariné Tena (AleixMT), Carles de la Cuadra
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Document processing tasks: salary/RLC extraction, proofs, contracts, and RNTs."""

import shutil
from datetime import datetime
from pathlib import Path
from typing import TypeVar

import pypdf

from NIF import NIF
from NAF import NAF
from Name import Name
from arguments import parse_date
from custom_except import (
    UndefinedRegularSalaryType,
    BadSharepointListUpdateRequest,
    PersonDoesNotExistInSharepoint,
)
from data import (
    parse_date_from_salary_filename,
    parse_salary_filename_from_salary_path,
    unparse_date,
    parse_salary_type,
    unparse_month,
    unparse_year_month,
    unparse_year_month_short,
    parse_salary_type_from_salary_filename,
    get_rlc_monthly_result_structure,
    get_rnt_monthly_result_structure,
)
from defines import (
    RLCS_OUTPUT_NAME,
    SALARIES_OUTPUT_NAME,
    SalaryType,
    RegularSalaryType,
    RLCType,
    CONTRACTS_OUTPUT_NAME,
    RNTS_OUTPUT_NAME,
)

from filesystem import flatten_dirs, list_dir

from pdf import (
    get_matching_page,
    write_page,
    parse_dates_from_delayed_salary,
    is_date_present_in_rlc_delay,
    merge_pdfs,
    parse_regular_salary_type,
    get_matching_pages,
)
from sharepoint import update_list_item_field
from logger import get_logger

log = get_logger(__name__)


def process_rlc_aux(
    salary_date: datetime,
    rlc_folder_path: Path,
    months_found: dict[datetime, list[bool]],
    rlc_subtype: str,
    rlc_type: str,
) -> Path:
    """Locate one RLC sub-document (N or P) and mark it as found in *months_found*.

    Args:
        salary_date: Date of the corresponding salary.
        rlc_folder_path: Root folder containing RLC files.
        months_found: Per-month result structure to update in-place.
        rlc_subtype: Sub-document type, either ``"N"`` or ``"P"``.
        rlc_type: RLC type code, e.g. ``"00"``, ``"03"``, ``"13"``.

    Returns:
        Path to the found RLC file.

    Raises:
        ValueError: If the expected RLC file does not exist.
    """
    month = unparse_month(salary_date)
    year = str(salary_date.year)
    n_name = month + "_L" + rlc_type + rlc_subtype + "01.pdf"
    rlc_n_path = rlc_folder_path / year / n_name
    if rlc_n_path.exists():
        log.debug(f"The RLC {rlc_n_path} is present.")
        if rlc_subtype == "N":
            months_found[salary_date][1] = True
        elif rlc_subtype == "P":
            months_found[salary_date][2] = True
        return rlc_n_path
    else:
        log.error(
            f"Monthly salary was found, but the expected L{rlc_type} RLC of type "
            f"{rlc_subtype} was not found in the expected location {rlc_n_path}. "
            f"Skipping merge of this salary file."
        )
        raise ValueError("File was not detected")  # TODO custom except


def process_generic_rlc(
    rlc_type: str,
    salary_date: datetime,
    salary_file_path: Path,
    rlc_folder_path: Path,
    naf_dir: Path,
    salary_output_path: Path,
    salaries_found: dict[datetime, list[bool]],
) -> None:
    """Locate and merge both RLC sub-documents (N and P) for a regular or settlement salary.

    Args:
        rlc_type: RLC type code (``"00"`` for regular, ``"13"`` for settlement).
        salary_date: Date of the corresponding salary.
        salary_file_path: Path to the salary PDF (for logging only).
        rlc_folder_path: Root folder containing RLC files.
        naf_dir: Output directory for the employee.
        salary_output_path: Output path for the salary file (for logging only).
        salaries_found: Per-month result structure updated in-place.
    """
    salaries_found[salary_date][0] = True
    try:
        rlc_n_path = process_rlc_aux(
            salary_date, rlc_folder_path, salaries_found, "N", rlc_type
        )
        log.debug(f"Expected RLC N path is: {rlc_n_path}")
        rlc_p_path = process_rlc_aux(
            salary_date, rlc_folder_path, salaries_found, "P", rlc_type
        )
        log.debug(f"Expected RLC P path is: {rlc_p_path}")
    except ValueError:
        log.error(
            f"Some of the RLC documents (N or P) has not been found. "
            f"The salary file {salary_file_path} will be skipped."
        )
        return

    pdf_merged_name = (
        str(salary_date.year)
        + unparse_month(salary_date)
        + "_L"
        + rlc_type
        + "Merge.pdf"
    )
    merge_pdfs([rlc_n_path, rlc_p_path], naf_dir / RLCS_OUTPUT_NAME / pdf_merged_name)


def process_rlc_l03(
    salary_file_path: Path,
    salary_page_number: int,
    salary_page: pypdf.PageObject,
    salary_date: datetime,
    naf_dir: Path,
    rlc_folder_path: Path,
    salary_output_path: Path,
    months_found: dict[datetime, list[bool]],
) -> None:
    """Locate and merge the L03 RLC documents matching a delay (atrasos) salary page.

    Args:
        salary_file_path: Path to the salary PDF.
        salary_page_number: Zero-based page index of the delay salary.
        salary_page: The delay salary page object (used to extract its date range).
        salary_date: Date of the salary file.
        naf_dir: Output directory for the employee.
        rlc_folder_path: Root folder containing RLC files.
        salary_output_path: Output path for the salary file (unused, kept for API parity).
        months_found: Per-month result structure updated in-place.
    """
    log.info(
        f"Salary file {salary_file_path} page {salary_page_number + 1} has been "
        f"selected as delay salary for date {unparse_date(salary_date)}"
    )
    try:
        delay_initial_date, delay_end_date = parse_dates_from_delayed_salary(
            salary_page
        )
    except ValueError as exc:
        log.error(
            f"The delay date could not be parsed from the delay salary page. "
            f"This document will be skipped from search. The internal error is {exc}"
        )
        return
    log.debug(
        "Initial date is "
        + unparse_date(delay_initial_date, "-")
        + " and end date is "
        + unparse_date(delay_end_date, "-")
    )

    rlc_dir = naf_dir / rlc_folder_path / str(salary_date.year)
    rlc_stem = unparse_month(salary_date) + "_L03"

    suffix = 1
    while suffix < 100:
        str_suffix = str(suffix).zfill(2)
        rlc_path_n = rlc_dir / (rlc_stem + "N" + str_suffix + ".pdf")
        if not rlc_path_n.exists():
            log.debug(f"Breaking out of the bucle because {rlc_path_n} does not exist.")
            break
        if is_date_present_in_rlc_delay(delay_initial_date, delay_end_date, rlc_path_n):
            months_found[salary_date][1] = True
            rlc_path_p = rlc_dir / (rlc_stem + "P" + str_suffix + ".pdf")
            pdf_merged_name = f"{salary_date.year}{unparse_month(salary_date)}_L03Merge{str_suffix}.pdf"
            pdf_output_path = naf_dir / RLCS_OUTPUT_NAME / pdf_merged_name
            if not rlc_path_p.exists():
                log.debug(
                    f"Breaking out of the bucle because {rlc_path_p} does not exist."
                )
            months_found[salary_date][2] = True
            merge_pdfs([rlc_path_n, rlc_path_p], pdf_output_path)
            break
        suffix += 1


def process_salaries_with_rlc(
    salaries_folder_path: Path,
    rlc_folder_path: Path,
    naf_dir: Path,
    naf: NAF,
    begin: datetime,
    end: datetime,
) -> dict[RLCType, dict[datetime, list[bool]]]:
    """Extract salary pages for *naf* and locate their matching RLC documents.

    Args:
        salaries_folder_path: Root folder containing salary PDFs.
        rlc_folder_path: Root folder containing RLC PDFs.
        naf_dir: Output directory for the employee.
        naf: NAF identifier of the employee.
        begin: Start of the justification period.
        end: End of the justification period.

    Returns:
        Nested dict mapping each RLCType to a per-month found/not-found structure.
    """
    regular_monthly_salaries_rlcs_found = get_rlc_monthly_result_structure(begin, end)
    regular_settlement_salaries_rlcs_found = get_rlc_monthly_result_structure(
        begin, end
    )
    delay_salaries_rlcs_found = get_rlc_monthly_result_structure(begin, end)

    salary_files = flatten_dirs(salaries_folder_path)
    salary_files_selected = []
    for salary_file in salary_files:
        dir_date = parse_date_from_salary_filename(
            parse_salary_filename_from_salary_path(salary_file)
        )
        if begin <= dir_date <= end:
            salary_files_selected.append(salary_file)
            log.info(
                f"Salary file {salary_file} is selected, because its date is {unparse_date(dir_date, '-')}."
            )
        else:
            log.trace(
                f"Salary file {salary_file} is not selected, because its date is {unparse_date(dir_date, '-')}."
            )

    salary_files_selected.sort()
    for salary_file in salary_files_selected:
        log.debug(f"Processing file {salary_file}")
        salary_file_path = salaries_folder_path / salary_file
        salary_file_name = parse_salary_filename_from_salary_path(salary_file_path)
        salary_date = parse_date_from_salary_filename(salary_file_name)
        salary_type_str = parse_salary_type_from_salary_filename(salary_file_name)
        salary_output_filename = (
            f"{salary_date.year}{unparse_month(salary_date)}_{salary_type_str}"
        )
        # Liquidation files
        if salary_type_str == "LIQ":
            salary_file_name_no_extension = salary_file_name.split(".")[0]
            salary_file_liq_naf = salary_file_name_no_extension.split("_")[2]
            if salary_file_liq_naf != str(naf):
                log.debug(
                    f"NAF {str(naf)} was not detected in the name of liquidation PDF {salary_file}. Skipping document."
                )
                continue
            shutil.copy(
                src=salary_file_path,
                dst=naf_dir / SALARIES_OUTPUT_NAME / (salary_output_filename + ".pdf"),
            )

        salary_pages = get_matching_pages(salary_file_path, naf.slash_dash_str())
        if len(salary_pages) == 0:
            log.debug(
                f"NAF {str(naf)} was not detected in PDF {salary_file}. Skipping document."
            )
            continue
        for salary_page, salary_page_number in salary_pages:
            salary_output_path = naf_dir / SALARIES_OUTPUT_NAME / salary_output_filename

            index = 1
            while salary_output_path.exists():
                salary_output_path = (
                    naf_dir
                    / SALARIES_OUTPUT_NAME
                    / f"{salary_date.year}{unparse_month(salary_date)}_"
                    f"{salary_file_name.split('_')[1].split('.')[0]}_{index}.pdf"
                )
                index += 1

            write_page(salary_page, salary_output_path)

            log.info(
                f"Detected NAF {str(naf)} in PDF salary {salary_file_path}, page "
                f"{salary_page_number + 1}. Saving page in {salary_output_path} and "
                f"further processing it."
            )

            salary_type = parse_salary_type(salary_file_path)
            if salary_type == SalaryType.DELAY:
                delay_salaries_rlcs_found[salary_date][0] = True
                process_rlc_l03(
                    salary_file_path,
                    salary_page_number,
                    salary_page,
                    salary_date,
                    naf_dir,
                    rlc_folder_path,
                    salary_output_path,
                    delay_salaries_rlcs_found,
                )
            elif salary_type == SalaryType.REGULAR:
                log.info(
                    f"Salary file {salary_file_path} page {salary_page_number + 1} has been selected "
                    f"as regular salary for date {unparse_date(salary_date)}"
                )
                try:
                    regular_salary_type = parse_regular_salary_type(salary_page)
                except UndefinedRegularSalaryType as e:
                    log.error(
                        f"Salary file {salary_file_path} page {salary_page_number + 1} is a type "
                        f"not supported or can not be recognized. Skipping to next page. Internal error "
                        f"is: {str(e)}"
                    )
                    continue
                if regular_salary_type == RegularSalaryType.MONTHLY:
                    log.info(
                        f"Salary file {salary_file_path} page {salary_page_number + 1} has been "
                        f"selected as regular monthly salary for date {unparse_date(salary_date)}"
                    )
                    process_generic_rlc(
                        "00",
                        salary_date,
                        salary_file_path,
                        rlc_folder_path,
                        naf_dir,
                        salary_output_path,
                        regular_monthly_salaries_rlcs_found,
                    )
                elif regular_salary_type == RegularSalaryType.SETTLEMENT:
                    log.info(
                        f"Salary file {salary_file_path} page {salary_page_number + 1} has been "
                        f"selected as regular settlement salary for date {unparse_date(salary_date)}"
                    )
                    process_generic_rlc(
                        "13",
                        salary_date,
                        salary_file_path,
                        rlc_folder_path,
                        naf_dir,
                        salary_output_path,
                        regular_settlement_salaries_rlcs_found,
                    )
                else:
                    log.error(
                        "The regular salary type is not recognized. This RLC will be skipped."
                    )
                    continue

            elif salary_type == SalaryType.EXTRA:
                log.info(
                    f"Salary file {salary_file_path} page {salary_page_number + 1} has been selected "
                    f"as extra salary for date {unparse_date(salary_date)}"
                )
                continue
            else:
                log.error(
                    f"Detected type {str(salary_type)} that is not a recognized type. The current salary "
                    f"file will be ignored"
                )

    r = {
        RLCType.REGULAR: regular_monthly_salaries_rlcs_found,
        RLCType.SETTLEMENT: regular_settlement_salaries_rlcs_found,
        RLCType.DELAY: delay_salaries_rlcs_found,
    }

    return r


def compute_path(partial_path: Path, suffix: str, extension: str) -> Path:
    """Return a unique output path by appending *suffix* and a numeric disambiguator.

    Args:
        partial_path: Base path without suffix or extension.
        suffix: Label appended before the extension (e.g. ``"Nomines"``).
        extension: File extension including the dot (e.g. ``".pdf"``).

    Returns:
        A path that does not yet exist on disk.
    """
    num_suffix = 1
    output_path = partial_path.parent / (partial_path.name + "_" + suffix + extension)
    while output_path.exists():
        output_path = (
            partial_path.parent
            / f"{partial_path.name}_{suffix}_{num_suffix}{extension}"
        )
        num_suffix += 1
    return output_path


def process_proofs(
    proofs_folder_path: Path,
    proofs_output_path: Path,
    naf: NAF,
    begin: datetime,
    end: datetime,
    naf_to_dni: dict[NAF, NIF],
) -> None:
    """Extract bank-proof pages matching *naf*'s DNI from the proofs folder.

    Args:
        proofs_folder_path: Root folder containing bank-proof PDFs.
        proofs_output_path: Directory where extracted proof pages are written.
        naf: NAF identifier of the employee.
        begin: Start of the justification period.
        end: End of the justification period.
        naf_to_dni: Mapping from NAF to NIF for DNI lookup.
    """
    all_bankproof_folders = flatten_dirs(proofs_folder_path)

    bankproof_folders_selected = []
    for bankproof_folder in all_bankproof_folders:
        dir_date = parse_date(bankproof_folder.name[:6], "%m%Y")
        if begin <= dir_date <= end:
            bankproof_folders_selected.append(bankproof_folder)
            log.debug(
                f"Proof folder {bankproof_folder} is selected, because its date is {unparse_date(dir_date, '-')}."
            )

    for bankproof_folder in bankproof_folders_selected:
        bank = "_".join(bankproof_folder.name.split("_")[1:])
        proof_date = parse_date(bankproof_folder.name[:6], "%m%Y")
        log.trace(f"Working with folder {bankproof_folder}. Bank type is {bank}")
        if bank == "BBVA" or bank == "BBVA_endarreriments" or bank == "BBVA_FINIQUITO":
            for bankproof_file in list_dir(proofs_folder_path / bankproof_folder):
                try:
                    page = get_matching_page(
                        proofs_folder_path / bankproof_folder / bankproof_file,
                        naf_to_dni[naf].no_dash_str(),
                        "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]",
                    )
                except ValueError as e:
                    log.trace(
                        f"DNI {naf_to_dni[naf]} not detected in "
                        f"{proofs_folder_path / bankproof_folder / bankproof_file}. Error: {e}"
                    )
                    continue
                if bank == "BBVA_endarreriments":
                    suffix = "Atrasos"
                elif bank == "BBVA":
                    suffix = "Nomines"
                elif bank == "BBVA_FINIQUITO":
                    suffix = "Extra"
                else:
                    suffix = "BBVA-UnknownSalaryType"
                output_partial_path = proofs_output_path / proof_date.strftime("%Y%m")
                output_path = compute_path(output_partial_path, suffix, ".pdf")
                log.info(
                    f"DNI {naf_to_dni[naf]} was detected in "
                    f"{proofs_folder_path / bankproof_folder / bankproof_file}. "
                    f"Writing page to {output_path}."
                )
                write_page(page, output_path)

        elif (
            bank == "LA_CAIXA"
            or bank == "LA_CAIXA_EXTRA"
            or bank == "LA_CAIXA_endarreriments"
        ):
            file_names = list_dir(proofs_folder_path / bankproof_folder)
            for file_name in file_names:
                try:
                    page = get_matching_page(
                        proofs_folder_path / bankproof_folder / file_name,
                        naf_to_dni[naf].no_dash_str(),
                        "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]",
                    )
                except ValueError as e:
                    log.debug(
                        f"DNI {naf_to_dni[naf]} not detected in "
                        f"{proofs_folder_path / bankproof_folder / file_name}. Error: {e}"
                    )
                    continue
                if bank == "LA_CAIXA_endarreriments":
                    suffix = "Atrasos"
                elif bank == "LA_CAIXA":
                    suffix = "Nomines"
                elif bank == "LA_CAIXA_EXTRA":
                    suffix = "Extra"
                else:
                    suffix = "LACAIXA-UnknownSalaryType"
                output_partial_path = proofs_output_path / proof_date.strftime("%Y%m")
                output_path = compute_path(output_partial_path, suffix, ".pdf")
                log.info(
                    f"DNI {naf_to_dni[naf]} was detected in "
                    f"{proofs_folder_path / bankproof_folder / file_name}. "
                    f"Writing page to {output_path}."
                )
                write_page(page, output_path)
        else:
            log.error(f"{bank} is a bad bank. Skipping to next bank proof.")
            continue


def process_contracts(
    contracts_folder_path: Path, naf_dir: Path, naf: NAF, begin: datetime, end: datetime
) -> bool:
    """Copy contract files for *naf* that overlap the requested period.

    Args:
        contracts_folder_path: Folder containing contract PDFs.
        naf_dir: Output directory for the employee.
        naf: NAF identifier of the employee.
        begin: Start of the justification period.
        end: End of the justification period.

    Returns:
        True if at least one matching contract was found and copied.
    """
    found = False
    contracts_files = list_dir(contracts_folder_path)
    contracts_files.sort()
    for contracts_file in contracts_files:
        log.debug(f"contract file: {contracts_file}")
        naf_dirty = NAF(contracts_file.split("_")[0])
        dates = contracts_file.split(".")[0].split("_")
        begin_date = parse_date("20" + dates[1], "%Y%m")
        if len(dates) == 3:
            if dates[2] == "A":
                end_date = datetime.max
            else:
                end_date = parse_date("20" + dates[2], "%Y%m")
        elif len(dates) == 2:
            end_date = datetime.max
        else:
            log.error(
                f"expected 3 fields in the name of the file {contracts_file} but "
                f"{len(dates)} have been found. The file will be ignored until it has proper format."
            )
            continue

        if naf_dirty == naf:
            log.debug(
                f"NAF {naf_dirty} of file {contracts_file} coincides with queried NAF. Checking dates..."
            )
            if begin <= end_date and begin_date <= end:
                log.info(
                    f"{contracts_file} with date {unparse_date(begin_date, '-')}, "
                    f"{unparse_date(end_date, '-')} is in range of "
                    f"{unparse_date(begin, '-')}, {unparse_date(end, '-')}. Copying it to {naf_dir}"
                )
                try:
                    shutil.copy(
                        src=contracts_folder_path / contracts_file,
                        dst=naf_dir / CONTRACTS_OUTPUT_NAME,
                    )
                    found = True
                except Exception as e:
                    err_msg = (
                        f"An error happened while copying "
                        f"{contracts_folder_path / contracts_file} to "
                        f"{naf_dir / CONTRACTS_OUTPUT_NAME}. The program will abort. "
                        f"Error is: {str(e)}"
                    )
                    log.critical(err_msg)
                    raise Exception(err_msg)

    if not found:
        log.warning(f"Contract not found with NAF {naf}")
    return found


def process_RNTs(
    rnts_folder_path: Path, naf_dir: Path, naf: NAF, begin: datetime, end: datetime
) -> dict[datetime, bool]:
    """Extract RNT pages for *naf* and track which months have a matching RNT.

    Args:
        rnts_folder_path: Root folder containing RNT PDFs.
        naf_dir: Output directory for the employee.
        naf: NAF identifier of the employee.
        begin: Start of the justification period.
        end: End of the justification period.

    Returns:
        Per-month dict indicating whether an RNT was found for each month.
    """
    rnts_found = get_rnt_monthly_result_structure(begin, end)

    rnt_files = flatten_dirs(rnts_folder_path)
    rnt_files.sort()
    for rnt_file in rnt_files:
        file_date = parse_date("20" + rnt_file.name[:4], "%Y%m", return_naive=True)
        if begin <= file_date <= end:
            rnt_file_name = rnt_file.name
            rnt_file_name_without_extension = Path(rnt_file_name).stem
            rnt_path = rnts_folder_path / str(file_date.year) / rnt_file_name
            log.info(
                f"RNT file {rnt_path} is selected, because its date is {unparse_date(file_date)}."
            )
            try:
                pages = get_matching_pages(rnt_path, str(naf), r"\d{12}")
            except ValueError as e:
                log.debug(f"NAF {naf} not detected in {rnt_path}. Error: {e}")
                continue
            for page, page_num in pages:
                rnt_path_destination = (
                    naf_dir
                    / RNTS_OUTPUT_NAME
                    / f"{rnt_file_name_without_extension}_{page_num}.pdf"
                )
                log.info(
                    f"NAF {naf} was detected in {rnt_path} in page {page_num + 1}. "
                    f"Writing page to {rnt_path_destination}."
                )
                write_page(page, rnt_path_destination)
                log.debug(f"rnt found with date: {file_date}")
                rnts_found[file_date] = True
        else:
            log.debug(
                f"RNT file {rnt_file} is not selected, because its date is {unparse_date(file_date)}."
            )

    return rnts_found


def datetime_range(begin: datetime, end: datetime) -> list[datetime]:
    """Return a list of first-of-month datetimes covering the ``[begin, end]`` period.

    Args:
        begin: Start of the period.
        end: End of the period.

    Returns:
        Ordered list of ``datetime`` values, one per calendar month.
    """
    current = datetime(begin.year, begin.month, 1)

    result = []
    while current <= end:
        result.append(
            datetime.strptime(str(current.year * 100 + current.month), "%Y%m")
        )
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return result


def merge_rnts_rlcs(
    rnts_folder: Path,
    rlcs_folder: Path,
    rnts_folder_output: Path,
    rlcs_folder_output: Path,
    merged_rnts_rlcs_folder_output: Path,
    begin: datetime,
    end: datetime,
) -> None:
    """Merge per-month RNT and RLC output files into combined PDFs.

    Args:
        rnts_folder: Source folder listing available RNT filenames.
        rlcs_folder: Source folder listing available RLC filenames.
        rnts_folder_output: Folder containing the extracted RNT pages to merge.
        rlcs_folder_output: Folder containing the extracted RLC pages to merge.
        merged_rnts_rlcs_folder_output: Destination folder for the merged PDFs.
        begin: Start of the justification period.
        end: End of the justification period.
    """
    months_list = datetime_range(begin, end)
    log.info(f"Generated months list from {begin} to {end} is: {months_list}")
    rnts_filenames = list_dir(rnts_folder)
    rlcs_filenames = list_dir(rlcs_folder)
    log.trace(f"RNT available files are: {rnts_filenames}")
    log.trace(f"RLC available files are: {rlcs_filenames}")

    for current_date in months_list:
        full_year_date = unparse_year_month(current_date)
        partial_year_date = unparse_year_month_short(current_date)
        log.trace(f"Full year date is: {full_year_date}")
        log.trace(f"Partial year date is: {partial_year_date}")

        paths_to_merge = []
        for rnt_filename in rnts_filenames:
            date_str = rnt_filename.split("_")[0]
            log.trace(f"date str is: {date_str}")
            if date_str == partial_year_date:
                paths_to_merge.append(rnts_folder_output / rnt_filename)
        for rlc_filename in rlcs_filenames:
            date_str = rlc_filename.split("_")[0]
            log.trace(f"date str is: {date_str}")
            if date_str == full_year_date:
                paths_to_merge.append(rlcs_folder_output / rlc_filename)

        output_path = merged_rnts_rlcs_folder_output / (
            unparse_year_month(current_date) + "_Merged.pdf"
        )
        log.debug(f"PDFs to merge: {paths_to_merge}")
        log.debug(f"Output path: {output_path}")

        if len(paths_to_merge) >= 2:
            merge_pdfs(paths_to_merge, output_path, True)
        else:
            log.warning(
                f"During date {unparse_year_month(current_date)} there were less than "
                f"one RNTs or RLCs to merge (at least one is missing). Skipping"
            )
        log.trace(f"Merged PDFs: {paths_to_merge} -> {output_path}")


_K = TypeVar("_K")
_V = TypeVar("_V")


def reverse_dict(d: dict[_K, _V]) -> dict[_V, _K]:
    """Return a new dict with keys and values swapped.

    Args:
        d: Source dictionary to invert.

    Returns:
        Inverted dictionary mapping original values to original keys.
    """
    r = {}
    for key, value in d.items():
        r[value] = key
    return r


def complete_ids_with_naf(
    naf: NAF,
    naf_to_dni: dict[NAF, NIF],
    naf_to_name: dict[NAF, Name],
    naf_to_email: dict[NAF, str],
) -> tuple[NIF, Name, str]:
    """Resolve NIF, Name, and email for the given NAF using the lookup tables.

    Args:
        naf: NAF identifier of the employee.
        naf_to_dni: Mapping from NAF to NIF.
        naf_to_name: Mapping from NAF to Name.
        naf_to_email: Mapping from NAF to email address.

    Returns:
        Tuple of ``(nif, name, email)`` for the employee.
    """
    dni = naf_to_dni[naf]
    name = naf_to_name[naf]
    email = naf_to_email[naf]
    return dni, name, email


def update_list_with_person_ids(request: int, naf: NAF, dni: NIF, email: str) -> None:
    """Update the justification history list with NAF, DNI, and email identifiers.

    Name is intentionally skipped because the A3 name format does not match SharePoint.

    Args:
        request: Numeric list item identifier for the justification request.
        naf: Employee NAF to write.
        dni: Employee NIF/DNI to write.
        email: Employee email address to write.

    Raises:
        PersonDoesNotExistInSharepoint: If the employee no longer exists in SharePoint.
    """
    update_list_item_field(request, {"DNI": str(dni)})
    update_list_item_field(request, {"NAF": str(naf)})
    try:
        update_list_item_field(request, {"PersonaEmail": email})
    except BadSharepointListUpdateRequest as e:
        raise PersonDoesNotExistInSharepoint from e
    try:
        update_list_item_field(request, {"Nomdelapersona": str(email)})
    except BadSharepointListUpdateRequest as e:
        raise PersonDoesNotExistInSharepoint from e


def complete_ids(
    naf: NAF,
    nif: NIF,
    email: str,
    name: Name,
    name_to_naf: dict[Name, NAF],
    naf_to_nif: dict[NAF, NIF],
    nif_to_naf: dict[NIF, NAF],
    naf_to_name: dict[NAF, Name],
    email_to_naf: dict[str, NAF],
    naf_to_email: dict[NAF, str],
) -> tuple[NAF, NIF, Name, str]:
    """Resolve all employee identifiers from whichever primary key is provided.

    Precedence: NAF > email > NIF > name. Warns when a redundant identifier is
    supplied alongside the primary key.

    Args:
        naf: NAF identifier (highest priority).
        nif: NIF/DNI identifier.
        email: Email address.
        name: Employee name.
        name_to_naf: Lookup table from Name to NAF.
        naf_to_nif: Lookup table from NAF to NIF.
        nif_to_naf: Lookup table from NIF to NAF.
        naf_to_name: Lookup table from NAF to Name.
        email_to_naf: Lookup table from email to NAF.
        naf_to_email: Lookup table from NAF to email.

    Returns:
        Tuple of ``(naf, nif, name, email)`` with all fields resolved.

    Raises:
        ValueError: If none of the identifier arguments are provided.
    """
    if naf:
        if nif:
            log.warning(
                "DNI is defined but NAF is also defined. Provided NIF will be ignored."
            )
        if name:
            log.warning(
                "Name is defined but NAF is also defined. Provided name will be ignored."
            )
        if email:
            log.warning(
                "Email is defined but NAF is also defined. Provided email will be ignored."
            )

    elif email:
        if nif:
            log.warning(
                "DNI is defined but email is also defined. Provided NIF will be ignored."
            )
        if name:
            log.warning(
                "Name is defined but email is also defined. Provided name will be ignored."
            )
        naf = email_to_naf[email]

    elif nif:
        if name:
            log.warning(
                "Name is defined but NIF is also defined. Provided name will be ignored."
            )
        log.warning(
            "Remember that "
            "identifying employees using NIF is fragile and should be avoided. Using NAF or email for "
            "employee "
            "identification is the recommended configuration."
        )
        naf = nif_to_naf[nif]

    elif name:
        log.warning(
            "Remember that "
            "identifying employees using name is fragile and should be avoided. Using NAF or email for "
            "employee "
            "identification is the recommended configuration."
        )
        naf = name_to_naf[name]

    else:
        raise ValueError(
            "An employee identifier was not supplied (NAF, DNI or name). Aborting."
        )
    return (naf, *complete_ids_with_naf(naf, naf_to_nif, naf_to_name, naf_to_email))
