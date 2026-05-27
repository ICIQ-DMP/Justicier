import argparse
import shutil
from datetime import datetime
from pathlib import Path
from typing import TypeVar

import pypdf

from DNI import DNI
from NAF import NAF
from Name import Name
from arguments import parse_date
from custom_except import UndefinedRegularSalaryType
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
            f"Monthly salary was found, but the expected L{rlc_type} RLC of type {rlc_subtype} was not found in the expected location {rlc_n_path}. Skipping merge of this salary file."
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
            f"Some of the RLC documents (N or P) has not been found. The salary file {salary_file_path} will be skipped."
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
    log.info(
        f"Salary file {salary_file_path} page {salary_page_number + 1} has been selected as delay salary for date {unparse_date(salary_date)}"
    )
    try:
        delay_initial_date, delay_end_date = parse_dates_from_delayed_salary(
            salary_page
        )
    except ValueError as exc:
        log.error(
            f"The delay date could not be parsed from the delay salary page. This document will be skipped from search. The internal error is {exc}"
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
    naf_to_dni: dict[NAF, DNI],
) -> None:
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
                        f"DNI {naf_to_dni[naf]} not detected in {proofs_folder_path / bankproof_folder / bankproof_file}. Error: {e}"
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
                    f"DNI {naf_to_dni[naf]} was detected in {proofs_folder_path / bankproof_folder / bankproof_file}. Writing page to {output_path}."
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
                        f"DNI {naf_to_dni[naf]} not detected in {proofs_folder_path / bankproof_folder / file_name}. Error: {e}"
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
                    f"DNI {naf_to_dni[naf]} was detected in {proofs_folder_path / bankproof_folder / file_name}. Writing page to {output_path}."
                )
                write_page(page, output_path)
        else:
            log.error(f"{bank} is a bad bank. Skipping to next bank proof.")
            continue


def process_contracts(
    contracts_folder_path: Path, naf_dir: Path, naf: NAF, begin: datetime, end: datetime
) -> bool:
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
                f"expected 3 fields in the name of the file {contracts_file} but {len(dates)} have been found. The file will be ignored until it has proper format."
            )
            continue

        if naf_dirty == naf:
            log.debug(
                f"NAF {naf_dirty} of file {contracts_file} coincides with queried NAF. Checking dates..."
            )
            if begin <= end_date and begin_date <= end:
                log.info(
                    f"{contracts_file} with date {unparse_date(begin_date, '-')}, {unparse_date(end_date, '-')} is in range of {unparse_date(begin, '-')}, {unparse_date(end, '-')}. Copying it to {naf_dir}"
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
                    f"NAF {naf} was detected in {rnt_path} in page {page_num + 1}. Writing page to {rnt_path_destination}."
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
                f"During date {unparse_year_month(current_date)} there were less than one RNTs or RLCs to merge (at least one is missing). Skipping"
            )
        log.trace(f"Merged PDFs: {paths_to_merge} -> {output_path}")


_K = TypeVar("_K")
_V = TypeVar("_V")


def reverse_dict(d: dict[_K, _V]) -> dict[_V, _K]:
    r = {}
    for key, value in d.items():
        r[value] = key
    return r


def complete_arguments(
    args: argparse.Namespace,
    NAME_TO_NAF: dict[Name, NAF],
    NAF_TO_DNI: dict[NAF, DNI],
    DNI_TO_NAF: dict[DNI, NAF],
    NAF_TO_NAME: dict[NAF, Name],
    EMAIL_TO_NAF: dict[str, NAF],
    NAF_TO_EMAIL: dict[NAF, str],
) -> None:
    if args.naf:
        if not args.dni:
            args.dni = NAF_TO_DNI[args.naf]
            if args.request:
                update_list_item_field(args.request, {"DNI": str(args.dni)})
        else:
            log.warning("DNI is defined but NAF is also defined. DNI will be ignored")
        if not args.name:
            args.name = NAF_TO_NAME[args.naf]
        else:
            log.warning("Name is defined but NAF is also defined. Name will be ignored")
        return
    if args.dni:
        if not args.naf:
            args.naf = DNI_TO_NAF[args.dni]
            if args.request:
                update_list_item_field(args.request, {"NAF": str(args.naf)})
        if not args.name:
            args.name = NAF_TO_NAME[args.naf]
            if args.request:
                update_list_item_field(args.request, {"Nomdelapersona": str(args.name)})
        else:
            log.warning("Name is defined but DNI is also defined. Name will be ignored")
        return
    if args.target_email:
        if not args.naf:
            if args.target_email in EMAIL_TO_NAF:
                args.naf = EMAIL_TO_NAF[args.target_email]
                if args.request:
                    update_list_item_field(args.request, {"NAF": str(args.naf)})
            else:
                raise ValueError(
                    f"Only name was supplied, but the name {str(args.name)} can not be found in the "
                    "database. The program "
                    "can not continue and will abort. Remember that "
                    "identifying employees using name is fragile and should be avoided. Using NAF for "
                    "employee "
                    "identification is the recommended configuration. Another option better than name but "
                    "worse than NAF is DNI."
                )
        if not args.dni:
            args.dni = NAF_TO_DNI[args.naf]
        if not args.name:
            args.name = NAF_TO_NAME[args.naf]
        return
    if args.name:
        if not args.naf:
            if args.name in NAME_TO_NAF:
                args.naf = NAME_TO_NAF[args.name]
                if args.request:
                    update_list_item_field(args.request, {"NAF": str(args.naf)})
            else:
                raise ValueError(
                    f"Only name was supplied, but the name {str(args.name)} can not be found in the "
                    "database. The program "
                    "can not continue and will abort. Remember that "
                    "identifying employees using name is fragile and should be avoided. Using NAF for "
                    "employee "
                    "identification is the recommended configuration. Another option better than name but "
                    "worse than NAF is DNI."
                )
        if not args.dni:
            args.dni = NAF_TO_DNI[args.naf]
        return

    raise ValueError(
        "An employee identifier was not supplied (NAF, DNI or name). Aborting."
    )
