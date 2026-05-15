import os.path
from datetime import datetime

from NAF import NAF
from arguments import parse_date
from custom_except import UndefinedRegularSalaryType
from data import (
    get_rlc_monthly_result_structure,
    parse_date_from_salary_filename,
    parse_salary_filename_from_salary_path,
    unparse_date,
    parse_salary_type,
    unparse_month,
    unparse_year_month,
    unparse_year_month_short,
    parse_salary_type_from_salary_filename,
)
from defines import *
from filesystem import *
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
    salary_date, rlc_folder_path, months_found, rlc_subtype: str, rlc_type: str
):
    month = unparse_month(salary_date)
    year = salary_date.year.__str__()
    n_name = month + "_L" + rlc_type + rlc_subtype + "01.pdf"
    rlc_n_path = os.path.join(rlc_folder_path, year, n_name)
    if os.path.exists(rlc_n_path):
        log.debug("The RLC " + rlc_n_path + " is present.")
        if rlc_subtype.__eq__("N"):
            months_found[salary_date][1] = True  # RLC L00 of type N is found
        elif rlc_subtype.__eq__("P"):
            months_found[salary_date][2] = True  # RLC L00 of type P is found
        return rlc_n_path
    else:
        log.error(
            "Monthly salary was found, but the expected L"
            + rlc_type
            + " RLC of type "
            + rlc_subtype
            + " was "
            "not found in the "
            "expected location "
            "" + str(rlc_n_path) + ". Skipping merge of this salary file."
        )
        raise ValueError("File was not detected")  # TODO custom except


def process_generic_rlc(
    rlc_type,
    salary_date,
    salary_file_path,
    rlc_folder_path,
    naf_dir,
    salary_output_path,
    salaries_found,
):
    salaries_found[salary_date][0] = True  # Monthly salary is found
    try:
        rlc_n_path = process_rlc_aux(
            salary_date, rlc_folder_path, salaries_found, "N", rlc_type
        )
        log.debug("Expected RLC N path is: " + rlc_n_path)
        rlc_p_path = process_rlc_aux(
            salary_date, rlc_folder_path, salaries_found, "P", rlc_type
        )
        log.debug("Expected RLC P path is: " + rlc_p_path)
    except ValueError:
        log.error(
            "Some of the RLC documents (N or P) has not been found. The salary file "
            + salary_file_path
            + " will be skipped."
        )
        return

    pdf_path_list = [rlc_n_path, rlc_p_path]
    pdf_merged_name = (
        salary_date.year.__str__()
        + unparse_month(salary_date)
        + "_L"
        + rlc_type
        + "Merge.pdf"
    )
    merge_pdfs(pdf_path_list, os.path.join(naf_dir, RLCS_OUTPUT_NAME, pdf_merged_name))


def process_rlc_l03(
    salary_file_path,
    salary_page_number,
    salary_page,
    salary_date,
    naf_dir,
    rlc_folder_path,
    salary_output_path,
    months_found,
):

    log.info(
        "Salary file "
        + salary_file_path
        + " page "
        + str(salary_page_number + 1)
        + " has been selected as delay salary for date "
        + unparse_date(salary_date)
    )
    try:
        delay_initial_date, delay_end_date = parse_dates_from_delayed_salary(
            salary_page
        )
    except ValueError as exc:
        log.error(
            "The delay date could not be parsed from the delay salary page. This document will be "
            "skipped from search. The internal error is " + exc.__str__()
        )
        return
    log.debug(
        "Initial date is "
        + unparse_date(delay_initial_date, "-")
        + " and end date is "
        + unparse_date(delay_end_date, "-")
    )

    rlc_partial_path = os.path.join(
        naf_dir,
        rlc_folder_path,
        salary_date.year.__str__(),
        unparse_month(salary_date) + "_L03",
    )
    suffix = 1
    while suffix < 100:  # Accepting only suffix under 100
        if suffix < 10:
            str_suffix = "0" + str(suffix)
        else:
            str_suffix = str(suffix)
        rlc_path_n = rlc_partial_path + "N" + str_suffix + ".pdf"
        if not os.path.exists(rlc_path_n):
            log.debug(f"Breaking out of the bucle because {rlc_path_n} does not exist.")
            break
        if is_date_present_in_rlc_delay(delay_initial_date, delay_end_date, rlc_path_n):
            months_found[salary_date][1] = True  # Delay salary N found
            rlc_path_p = f"{rlc_partial_path}P{str_suffix}.pdf"
            pdf_path_list = []
            pdf_merged_name = f"{salary_date.year}{unparse_month(salary_date)}_L03Merge{str_suffix}.pdf"
            pdf_output_path = os.path.join(naf_dir, RLCS_OUTPUT_NAME, pdf_merged_name)
            if not os.path.exists(rlc_path_p):
                log.debug(
                    f"Breaking out of the bucle because {rlc_path_p} does not exist."
                )
            months_found[salary_date][2] = True  # Delay salary P is found
            # pdf_path_list.append(salary_output_path)  # Do not add salary to RLC merge
            pdf_path_list.append(rlc_path_n)
            pdf_path_list.append(rlc_path_p)
            merge_pdfs(pdf_path_list, pdf_output_path)
            break
        suffix += 1


def process_salaries_with_rlc(
    salaries_folder_path, rlc_folder_path, naf_dir, naf, begin, end
):
    # regular monthly salary, RLC-N, RLC-P
    regular_monthly_salaries_rlcs_found = get_rlc_monthly_result_structure(begin, end)
    # regular settlement salary, RLC-N, RLC-P
    regular_settlement_salaries_rlcs_found = get_rlc_monthly_result_structure(
        begin, end
    )
    # delay salary, RLC-N, RLC-P
    delay_salaries_rlcs_found = get_rlc_monthly_result_structure(begin, end)

    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    salary_files = flatten_dirs(salaries_folder_path)
    # Select all salary sheets that are in range with the date (begin and end date included)
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
            log.debug(
                f"Salary file {salary_file} is not selected, because its date is {unparse_date(dir_date, '-')}."
            )

    # Salaries, RLC L00, RLC L03
    # Write sheets to NAF folder that match the supplied NAF
    salary_files_selected.sort()
    for salary_file in salary_files_selected:
        log.debug(f"Processing file {salary_file}")
        salary_file_path = os.path.join(salaries_folder_path, salary_file)
        salary_file_name = parse_salary_filename_from_salary_path(salary_file_path)
        salary_date = parse_date_from_salary_filename(salary_file_name)
        salary_type_str = parse_salary_type_from_salary_filename(salary_file_name)
        salary_output_filename = (
            f"{str(salary_date.year)}{unparse_month(salary_date)}_{salary_type_str}"
        )
        # Liquidation files
        if salary_type_str == "LIQ":
            salary_file_name_no_extension = salary_file_name.split(".")[0]
            salary_file_liq_naf = salary_file_name_no_extension.split("_")[2]
            if salary_file_liq_naf != str(naf):
                log.debug(
                    f"NAF {str(naf)} was not detected in the name of liquidation PDF {str(salary_file)}. Skipping document."
                )
                continue
            shutil.copy(
                src=salary_file_path,
                dst=os.path.join(
                    naf_dir, SALARIES_OUTPUT_NAME, salary_output_filename + ".pdf"
                ),
            )

        salary_pages = get_matching_pages(salary_file_path, naf.slash_dash_str())
        if len(salary_pages) == 0:
            log.debug(
                f"NAF {str(naf)} was not detected in PDF {str(salary_file)}. Skipping document."
            )
            continue
        for salary_page, salary_page_number in salary_pages:
            salary_output_path = os.path.join(
                naf_dir, SALARIES_OUTPUT_NAME, salary_output_filename
            )

            index = 1
            while os.path.exists(salary_output_path):
                salary_output_path = os.path.join(
                    naf_dir,
                    SALARIES_OUTPUT_NAME,
                    f"{str(salary_date.year)}{unparse_month(salary_date)}_"
                    f"{salary_file_name.split('_')[1].split('.')[0]}_{str(index)}.pdf",
                )
                index += 1

            write_page(salary_page, salary_output_path)

            log.info(
                f"Detected NAF {str(naf)} in PDF salary {str(salary_file_path)}, page "
                f"{str(salary_page_number + 1)} . Saving page in {str(salary_output_path)} and "
                f"further processing it."
            )

            # Now check if salary_file is delay, so we need to proceed to L03 or regular (L00 or L13) procedure
            salary_type = parse_salary_type(salary_file_path)
            if salary_type == SalaryType.DELAY:  # process L03 RLCs
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
            elif salary_type == SalaryType.REGULAR:  # process L00 and L13 RLCs
                log.info(
                    f"Salary file {salary_file_path} page {str(salary_page_number + 1)} has been selected "
                    f"as regular salary for date {unparse_date(salary_date)}"
                )
                try:
                    regular_salary_type = parse_regular_salary_type(salary_page)
                except UndefinedRegularSalaryType as e:
                    log.error(
                        f"Salary file {salary_file_path} page {str(salary_page_number + 1)} is a type "
                        f"not supported or can not be recognized. Skipping to next page. Internal error "
                        f"is: {str(e)}"
                    )
                    continue
                if regular_salary_type == RegularSalaryType.MONTHLY:
                    log.info(
                        f"Salary file {salary_file_path} page {str(salary_page_number + 1)} has been "
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
                        f"Salary file {salary_file_path} page {str(salary_page_number + 1)} has been "
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

            elif salary_type.__eq__(SalaryType.EXTRA):
                log.info(
                    f"Salary file {salary_file_path} page {str(salary_page_number + 1)} has been selected "
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


def compute_path(partial_path, suffix, extension):
    num_suffix = 1
    output_path = partial_path + "_" + suffix + extension
    while os.path.exists(output_path):
        str_suffix = str(num_suffix)
        output_path = partial_path + "_" + suffix + "_" + str_suffix + extension
        num_suffix += 1

    return output_path


def process_proofs(proofs_folder_path, proofs_output_path, naf, begin, end, naf_to_dni):
    # Flatten year directories (flat list of document for all years)
    all_bankproof_folders = flatten_dirs(proofs_folder_path)

    # Select all bankproof folder that are in range with the date (begin and end date included)
    bankproof_folders_selected = []
    for bankproof_folder in all_bankproof_folders:
        dir_date = parse_date(bankproof_folder.split("/")[1][:6], "%m%Y")
        if begin <= dir_date <= end:
            bankproof_folders_selected.append(bankproof_folder)
            log.info(
                "Proof folder "
                + bankproof_folder
                + " is selected, because its date is "
                + unparse_date(dir_date, "-")
                + "."
            )

    # Write sheets to NAF folder that match the DNI
    for bankproof_folder in bankproof_folders_selected:
        bank = "_".join(bankproof_folder.split("_")[1:])
        proof_date = parse_date(bankproof_folder.split("/")[1][:6], "%m%Y")
        log.debug("Working with folder " + bankproof_folder + ". Bank type is " + bank)
        if (
            bank.__eq__("BBVA")
            or bank.__eq__("BBVA_endarreriments")
            or bank.__eq__("BBVA_endarreriments")
            or bank.__eq__("BBVA_FINIQUITO")
        ):
            for bankproof_file in list_dir(
                os.path.join(proofs_folder_path, bankproof_folder)
            ):
                try:
                    page = get_matching_page(
                        os.path.join(
                            proofs_folder_path, bankproof_folder, bankproof_file
                        ),
                        naf_to_dni[naf].no_dash_str(),
                        "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]",
                    )
                except ValueError as e:
                    log.debug(
                        "DNI "
                        + str(naf_to_dni[naf])
                        + " not detected in "
                        + os.path.join(
                            proofs_folder_path, bankproof_folder, bankproof_file
                        )
                        + ". Error: "
                        + e.__str__()
                    )
                    continue
                if bank.__eq__("BBVA_endarreriments") or bank.__eq__(
                    "BBVA_endarreriments"
                ):
                    suffix = "Atrasos"
                elif bank.__eq__("BBVA"):
                    suffix = "Nomines"
                elif bank.__eq__("BBVA_FINIQUITO"):
                    suffix = "Extra"
                else:
                    suffix = "BBVA-UnknownSalaryType"
                output_partial_path = os.path.join(
                    proofs_output_path, proof_date.strftime("%Y%m")
                )
                output_path = compute_path(output_partial_path, suffix, ".pdf")
                log.info(
                    "DNI "
                    + str(naf_to_dni[naf])
                    + " was detected in "
                    + os.path.join(proofs_folder_path, bankproof_folder, bankproof_file)
                    + ". Writing page to "
                    + output_path.__str__()
                    + "."
                )
                write_page(page, output_path)

        elif (
            bank.__eq__("LA_CAIXA")
            or bank.__eq__("LA_CAIXA_EXTRA")
            or bank.__eq__("LA_CAIXA_endarreriments")
        ):
            file_names = list_dir(os.path.join(proofs_folder_path, bankproof_folder))
            for file_name in file_names:
                try:
                    page = get_matching_page(
                        os.path.join(proofs_folder_path, bankproof_folder, file_name),
                        naf_to_dni[naf].no_dash_str(),
                        "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]",
                    )
                except ValueError as e:
                    log.debug(
                        "DNI "
                        + str(naf_to_dni[naf])
                        + " not detected in "
                        + os.path.join(proofs_folder_path, bankproof_folder, file_name)
                        + ". Error: "
                        + e.__str__()
                    )
                    continue
                if bank.__eq__("LA_CAIXA_endarreriments"):
                    suffix = "Atrasos"
                elif bank.__eq__("LA_CAIXA"):
                    suffix = "Nomines"
                elif bank.__eq__("LA_CAIXA_EXTRA"):
                    suffix = "Extra"
                else:
                    suffix = "LACAIXA-UnknownSalaryType"
                output_partial_path = os.path.join(
                    proofs_output_path, proof_date.strftime("%Y%m")
                )
                output_path = compute_path(output_partial_path, suffix, ".pdf")
                log.info(
                    "DNI "
                    + str(naf_to_dni[naf])
                    + " was detected in "
                    + os.path.join(proofs_folder_path, bankproof_folder, file_name)
                    + ". Writing page to "
                    + output_path.__str__()
                    + "."
                )
                write_page(page, output_path)
        else:
            log.error(bank.__str__() + " is a bad bank. Skipping to next bank proof.")
            continue


def process_contracts(contracts_folder_path, naf_dir, naf, begin, end):
    found = False
    # Salaries
    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    contracts_files = list_dir(contracts_folder_path)
    contracts_files.sort()
    for contracts_file in contracts_files:
        log.debug("contract file: " + contracts_file)
        naf_dirty = NAF(contracts_file.split("_")[0])
        dates = contracts_file.split(".")[0].split("_")
        begin_date = parse_date("20" + dates[1], "%Y%m")
        if len(dates) == 3:  # Contract is temporary; has end date
            if dates[2] == "A":
                # Addenda
                end_date = datetime.datetime.max
            else:
                end_date = parse_date("20" + dates[2], "%Y%m")
        elif len(dates) == 2:  # Contract is undefined; has no end date
            end_date = datetime.datetime.max
        else:
            log.error(
                "expected 3 fields in the name of the file "
                + contracts_file
                + " but "
                + str(len(dates))
                + " have been found. The file will be ignored until it has proper format."
            )
            continue

        if naf_dirty.__eq__(naf):
            log.debug(
                "NAF "
                + naf_dirty.__str__()
                + " of file "
                + contracts_file
                + " coincides with queried NAF. Checking dates..."
            )
            # Select which contracts are valid during the range in the arguments
            # This conditional means that we select the contract if there is any coincidence in the range defined by
            # (begin, end) and (end_date, begin_date).
            if begin <= end_date and begin_date <= end:
                log.info(
                    contracts_file
                    + " with date "
                    + unparse_date(begin_date, "-")
                    + ", "
                    + unparse_date(end_date, "-")
                    + "is in range "
                    "of "
                    + unparse_date(begin, "-")
                    + ", "
                    + unparse_date(end, "-")
                    + ". Copying it to "
                    + naf_dir
                )
                try:
                    shutil.copy(
                        src=os.path.join(contracts_folder_path, contracts_file),
                        dst=os.path.join(naf_dir, CONTRACTS_OUTPUT_NAME),
                    )
                    found = True
                except Exception as e:
                    err_msg = (
                        f"An error happened while copying "
                        f"{os.path.join(contracts_folder_path, contracts_file)} to "
                        f"{os.path.join(naf_dir, CONTRACTS_OUTPUT_NAME)}. The program will abort. "
                        f"Error is: {str(e)}"
                    )
                    log.critical(err_msg)
                    raise Exception(err_msg)

    if not found:
        log.warning("Contract not found with NAF " + str(naf))
    return found


def process_RNTs(rnts_folder_path, naf_dir, naf, begin, end):
    rnts_found = get_rlc_monthly_result_structure(
        begin, end, False
    )  # regular monthly salary, RLC-N, RLC-P

    rnt_files = flatten_dirs(rnts_folder_path)
    rnt_files.sort()
    for rnt_file in rnt_files:
        file_date = parse_date(
            "20" + rnt_file.split("/")[1][:4], "%Y%m", return_naive=True
        )
        # file_date.hour = 0  # Sometimes due to timezone correction the hour get set to a different than 0, causing problems in reporting
        if begin <= file_date <= end:
            rnt_file_name = rnt_file.split("/")[1]
            rnt_file_name_without_extension = rnt_file_name.split(".")[0]
            rnt_path = os.path.join(
                rnts_folder_path, file_date.year.__str__(), rnt_file_name
            )
            rnt_partial_path_destination = os.path.join(
                naf_dir, RNTS_OUTPUT_NAME, rnt_file_name
            )
            log.info(
                "RNT file "
                + rnt_path.__str__()
                + " is selected, because its date is "
                + unparse_date(file_date)
                + "."
            )
            try:
                pages = get_matching_pages(rnt_path, naf.__str__(), r"\d{12}")
            except ValueError as e:
                log.debug(
                    "NAF "
                    + naf.__str__()
                    + " not detected in "
                    + rnt_path
                    + ". Error: "
                    + e.__str__()
                )
                continue
            for page, page_num in pages:
                rnt_path_destination = os.path.join(
                    naf_dir,
                    RNTS_OUTPUT_NAME,
                    rnt_file_name_without_extension + "_" + str(page_num) + ".pdf",
                )
                log.info(
                    "NAF "
                    + naf.__str__()
                    + " was detected in "
                    + rnt_path
                    + " in page "
                    + str(page_num + 1)
                    + ". Writing page to "
                    + rnt_path_destination.__str__()
                    + "."
                )
                write_page(page, rnt_path_destination)
                print("rnt found with date: " + str(file_date))
                rnts_found[file_date] = True
        else:
            log.debug(
                "RNT file "
                + rnt_file.__str__()
                + " is not selected, because its date is "
                + unparse_date(file_date)
                + "."
            )

    return rnts_found


def datetime_range(begin, end):
    current = datetime.datetime(begin.year, begin.month, 1)

    result = []
    while current <= end:
        result.append(
            datetime.datetime.strptime(str(current.year * 100 + current.month), "%Y%m")
        )
        if current.month == 12:
            current = datetime.datetime(current.year + 1, 1, 1)
        else:
            current = datetime.datetime(current.year, current.month + 1, 1)

    return result


def merge_rnts_rlcs(rnts_folder_path, rlcs_folder_path, naf_dir, begin, end):
    months_list = datetime_range(begin, end)
    log.info(
        "Generated months list from "
        + str(begin)
        + " to "
        + str(end)
        + " is: "
        + str(months_list)
    )
    rnts_filenames = list_dir(rnts_folder_path)
    rlcs_filenames = list_dir(rlcs_folder_path)
    log.debug("RNT available files are: " + str(rnts_filenames))
    log.debug("RLC available files are: " + str(rlcs_filenames))

    for current_date in months_list:
        full_year_date = unparse_year_month(current_date)
        partial_year_date = unparse_year_month_short(current_date)
        log.debug("Full year date is: " + str(full_year_date))
        log.debug("Partial year date is: " + str(partial_year_date))

        paths_to_merge = []
        for rnt_filename in rnts_filenames:
            date_str = rnt_filename.split("_")[0]
            log.debug("date str is: " + str(date_str))
            if date_str.__eq__(partial_year_date):
                paths_to_merge.append(
                    os.path.join(naf_dir, RNTS_OUTPUT_NAME, rnt_filename)
                )
        for rlc_filename in rlcs_filenames:
            date_str = rlc_filename.split("_")[0]
            log.debug("date str is: " + str(date_str))
            if date_str.__eq__(full_year_date):
                paths_to_merge.append(
                    os.path.join(naf_dir, RLCS_OUTPUT_NAME, rlc_filename)
                )
        log.debug("PDFs to merge: " + str(paths_to_merge))
        log.debug(
            "Output path: "
            + str(
                os.path.join(
                    naf_dir,
                    RNTS_AND_RLCS_OUTPUT_NAME,
                    unparse_year_month(current_date) + "_Merged.pdf",
                )
            )
        )
        log.debug("Naf dir is: " + str(naf_dir))
        if len(paths_to_merge) >= 2:
            merge_pdfs(
                paths_to_merge,
                os.path.join(
                    naf_dir,
                    RNTS_AND_RLCS_OUTPUT_NAME,
                    unparse_year_month(current_date) + "_Merged.pdf",
                ),
                True,
            )
        else:
            log.warning(
                "During date "
                + unparse_year_month(current_date)
                + " there were less than one RNTs "
                "or RLCs to "
                "merge (at least one is missing). Skipping"
            )
        print(
            paths_to_merge,
            os.path.join(
                naf_dir,
                RNTS_AND_RLCS_OUTPUT_NAME,
                unparse_year_month(current_date) + "_Merged.pdf",
            ),
        )


def reverse_dict(d: dict):
    r = {}
    for key in d.keys():
        r[d[key]] = key
    return r


def complete_arguments(
    args, NAME_TO_NAF, NAF_TO_DNI, DNI_TO_NAF, NAF_TO_NAME, EMAIL_TO_NAF, NAF_TO_EMAIL
):
    if args.naf:
        if not args.dni:
            args.dni = NAF_TO_DNI[args.naf]
            if args.request:
                update_list_item_field(args.request, {"DNI": str(args.dni)})
        else:
            print(
                "WARNING: DNI is defined but NAF is also defined. DNI will be ignored"
            )
        if not args.name:
            args.name = NAF_TO_NAME[args.naf]
        else:
            print(
                "WARNING: Name is defined but NAF is also defined. Name will be ignored"
            )
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
            print(
                "WARNING: Name is defined but DNI is also defined. Name will be ignored"
            )
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
