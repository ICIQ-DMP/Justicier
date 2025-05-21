import logging
import os.path
import os.path
import shutil

from pyfiglet import Figlet

from NAF import NAF, NAF_TO_DNI
from arguments import parse_date, process_arguments
from data import get_monthly_result_structure, parse_date_from_salary_filename, \
    parse_salary_filename_from_salary_path, unparse_date, parse_salary_type, unparse_month
from defines import *
from filesystem import *
from logger import get_process_logger, get_logger
from pdf import get_matching_page, write_page, parse_dates_from_delayed_salary, is_date_present_in_rlc_delay, \
    merge_pdfs, compact_folder, parse_regular_salary_type, get_matching_pages
from logger import set_logger
from custom_except import UndefinedRegularSalaryType


def process_rlc_aux(salary_date, rlc_folder_path, naf_dir, months_found, rlc_subtype: str, rlc_type: str):
    logger = get_process_logger(base_logger, "Salaries and RLCs")
    month = unparse_month(salary_date)
    year = salary_date.year.__str__()
    n_name = month + "_L" + rlc_type + rlc_subtype + "01.pdf"
    rlc_n_path = os.path.join(rlc_folder_path, year, n_name)
    if os.path.exists(rlc_n_path):
        logger.debug("The RLC " + rlc_n_path + " is present.")
        if rlc_subtype.__eq__("N"):
            months_found[salary_date][1] = True  # RLC L00 of type N is found
        elif rlc_subtype.__eq__("P"):
            months_found[salary_date][2] = True  # RLC L00 of type P is found
        return rlc_n_path
    else:
        logger.error("Monthly salary was found, but the expected L" + rlc_type + " RLC of type " + rlc_subtype + " was "
                                                                                                "not found in the "
                                                                                                "expected location "
                                                                                                "" + str(
            rlc_n_path) + ". Skipping merge of this salary file.")
        raise ValueError("File was not detected")  # TODO custom except


def process_generic_rlc(rlc_type, logger, salary_date, salary_file_path, rlc_folder_path, naf_dir, salary_output_path, salaries_found):
    salaries_found[salary_date][0] = True  # Monthly salary is found

    try:
        rlc_n_path = process_rlc_aux(salary_date, rlc_folder_path, naf_dir, salaries_found,
                                     "N", rlc_type)
        logger.debug("Expected RLC N path is: " + rlc_n_path)
        rlc_p_path = process_rlc_aux(salary_date, rlc_folder_path, naf_dir, salaries_found,
                                     "P", rlc_type)
        logger.debug("Expected RLC P path is: " + rlc_p_path)
    except ValueError:
        logger.error("Some of the RLC documents (N or P) has not been found. The salary file " + salary_file_path
                    + " will be skipped.")
        return

    pdf_path_list = [salary_output_path, rlc_n_path, rlc_p_path]
    pdf_merged_name = salary_date.year.__str__() + unparse_month(salary_date) + "_L" + rlc_type + "Merge.pdf"
    merge_pdfs(pdf_path_list, os.path.join(naf_dir, RLCS_OUTPUT_NAME, pdf_merged_name))


def process_rlc_l03(delay_salaries_found, salary_file_path, salary_page_number, salary_page, salary_date, naf_dir, rlc_folder_path, salary_output_path, months_found):
    logger = get_process_logger(base_logger, "Salaries and RLCs")

    delay_salaries_found += 1
    logger.info("Salary file " + salary_file_path + ", page " +
                str(salary_page_number) + " has been selected as delay salary for date " +
                unparse_date(salary_date))
    try:
        delay_initial_date, delay_end_date = parse_dates_from_delayed_salary(salary_page)
    except ValueError as exc:
        logger.error("The delay date could not be parsed from the delay salary page. This document will be "
                     "skipped from search. The internal error is " + exc.__str__())
        return
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
                salary_date) + "_L03Merge" + str_suffix + ".pdf"
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


def process_salaries_with_rlc(salaries_folder_path, rlc_folder_path, naf_dir, naf, begin, end):
    logger = get_process_logger(base_logger, "Salaries and RLCs")
    regular_monthly_salaries_rlcs_found = get_monthly_result_structure(begin, end)  # salary, RLC-N, RLC-P
    regular_settlement_salaries_rlcs_found = get_monthly_result_structure(begin, end)  # salary, RLC-N, RLC-P
    delay_salaries_rlcs_found = get_monthly_result_structure(begin, end)  # salary, RLC-N, RLC-P

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
        logger.debug("Processing file " + salary_file)
        salary_file_path = os.path.join(salaries_folder_path, salary_file)
        salary_file_name = parse_salary_filename_from_salary_path(salary_file_path)
        salary_date = parse_date_from_salary_filename(salary_file_name)
        salary_pages = get_matching_pages(salary_file_path, naf.slash_dash_str())
        if len(salary_pages) == 0:
            logger.debug("NAF " + naf.__str__() + " was not detected in PDF " + str(salary_file) +
                     ". Skipping document.")
            continue
        for salary_page, salary_page_number in salary_pages:
            salary_output_path = os.path.join(naf_dir, SALARIES_OUTPUT_NAME, salary_file_name)
            write_page(salary_page, salary_output_path)

            logger.info("Detected NAF " + naf.__str__() + " in PDF salary " + str(salary_file_path) + ", page " +
                        str(salary_page_number) + ". Saving page in " +
                        salary_output_path.__str__() + " and further processing it.")

            # Now check if salary_file is delay, so we need to proceed to L03 or regular (L00 or L13) procedure
            salary_type = parse_salary_type(salary_file_path)
            if salary_type == SalaryType.DELAY:  # process L03 RLCs
                process_rlc_l03(delay_salaries_found, salary_file_path, salary_page_number, salary_page, salary_date,
                                naf_dir, rlc_folder_path, salary_output_path, delay_salaries_rlcs_found)

            elif salary_type == SalaryType.REGULAR:  # process L00 and L13 RLCs
                logger.info("Salary file " + salary_file_path + " page " +
                        str(salary_page_number) + " has been selected as regular salary for date " +
                            unparse_date(salary_date))

                regular_salary_type = parse_regular_salary_type(salary_page)
                if regular_salary_type == RegularSalaryType.MONTHLY:
                    logger.info("Salary file " + salary_file_path + "page " +
                        str(salary_page_number) + " has been selected as regular monthly salary for date " +
                            unparse_date(salary_date))
                    process_generic_rlc("00", logger, salary_date, salary_file_path, rlc_folder_path, naf_dir, salary_output_path, regular_monthly_salaries_rlcs_found)
                elif regular_salary_type == RegularSalaryType.SETTLEMENT:
                    logger.info("Salary file " + salary_file_path + " page " +
                        str(salary_page_number) + "has been selected as regular settlement salary for date " +
                            unparse_date(salary_date))
                    process_generic_rlc("13", logger, salary_date, salary_file_path, rlc_folder_path, naf_dir, salary_output_path, regular_settlement_salaries_rlcs_found)
                else:
                    logger.error("The regular salary type is not recognized. This RLC will be skipped.")
                    continue

            elif salary_type.__eq__(SalaryType.EXTRA):
                logger.info("Salary file " + salary_file_path + " page " +
                            str(salary_page_number) + " has been selected as extra salary for date " +
                            unparse_date(salary_date))
                continue
            else:
                logger.error(
                    "Detected type " + salary_type.__str__() + " that is not a recognized type. The current salary file "
                                                               "will be ignored")

    # Report
    salaries_found = 0
    for key in regular_monthly_salaries_rlcs_found.keys():
        if regular_monthly_salaries_rlcs_found[key][0]:
            salaries_found += 1
        if not regular_monthly_salaries_rlcs_found[key][0]:
            logger.warning("Salary for NAF " + str(naf) + " was not found during period " + unparse_date(key, "-"))
        elif not regular_monthly_salaries_rlcs_found[key][1]:
            logger.warning("RLC L00 N for NAF " + str(naf) + " was not found during period " + unparse_date(key, "-"))
        elif not regular_monthly_salaries_rlcs_found[key][2]:
            logger.warning("RLC L00 P for NAF " + str(naf) + " was not found during period " + unparse_date(key, "-"))

    if salaries_found != len(regular_monthly_salaries_rlcs_found.keys()):
        logger.warning(
            "In the period from " + str(begin) + " to " + str(end) + " there are " + str(len(regular_monthly_salaries_rlcs_found.keys())) +
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
                    logger.debug("NAF " + naf.__str__() + " not detected in " + bankproof_file + ". Error: " + e.__str__())
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
                    logger.critical("An error happened program will abort" + e)
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
        else:
            logger.debug("RNT file " + rnt_file.__str__() + " is not selected, because its date is " +
                        unparse_date(file_date) + ".")


def main():
    args = process_arguments()

    CURRENT_USER_FOLDER, CURRENT_JUSTIFICATION_FOLDER, USER_REPORT_FILE, ADMIN_LOG_PATH, SUPERVISOR_LOG_PATH = (
        compute_paths(args))

    ensure_file_structure(CURRENT_USER_FOLDER, CURRENT_JUSTIFICATION_FOLDER)

    logger_instance = get_logger(USER_REPORT_FILE, ADMIN_LOG_PATH, SUPERVISOR_LOG_PATH, debug_mode=True)
    # assign it to logger.base_logger
    set_logger(logger_instance)
    from logger import base_logger
    global base_logger

    raw_logger = get_process_logger(logger_instance, "Initialization")

    figlet = Figlet(font='banner3-D')
    ascii_logo = "\n" + figlet.renderText('Justicier')
    raw_logger.info(ascii_logo)

    compact_something = False
    compact_text = ""
    for key in args.compact.keys():
        if args.compact[key]:
            compact_something = True
            compact_text += key.value.__str__()
    if not compact_something:
        compact_text += "No document categories to merge"


    raw_logger.info(
        "\n***********************************************************************************************************************"
        "\n*                                                USER REQUEST DETAILS                                                 *"
        "\n***********************************************************************************************************************"
        "\n* PARAMETERS:" +
        "\n* - Email of the user doing the request: " + args.author +
        "\n* - NAF requested: " + args.naf.__str__() +
        "\n* - Initial date: " + unparse_date(args.begin) +
        "\n* - End date: " + unparse_date(args.end) +
        "\n* OPTIONS:" +
        "\n* - Document categories of the document type to merge: " + compact_text +
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


if __name__ == "__main__":
    main()
