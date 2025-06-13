import os.path
import os.path
import os.path
import time

from NAF import NAF, build_naf_to_dni, build_naf_to_name_and_surname
from TokenManager import TokenManager
from arguments import parse_date, process_parse_arguments
from chrono import elapsed_time
from custom_except import UndefinedRegularSalaryType
from data import get_rlc_monthly_result_structure, parse_date_from_salary_filename, \
    parse_salary_filename_from_salary_path, unparse_date, parse_salary_type, unparse_month
from defines import *
from filesystem import *
from logger import build_process_logger, get_logger
from logger import set_logger
from pdf import get_matching_page, write_page, parse_dates_from_delayed_salary, is_date_present_in_rlc_delay, \
    merge_pdfs, compact_folder, parse_regular_salary_type, get_matching_pages
from report import get_end_user_report, get_initial_user_report
from secret import read_secret
from sharepoint import download_input_folder, upload_folder_recursive, upload_file, get_site_id, get_drive_id

logger = None


def process_rlc_aux(salary_date, rlc_folder_path, months_found, rlc_subtype: str, rlc_type: str):
    proc_logger = build_process_logger(logger, "Salaries and RLCs L00 / L13 aux")
    month = unparse_month(salary_date)
    year = salary_date.year.__str__()
    n_name = month + "_L" + rlc_type + rlc_subtype + "01.pdf"
    rlc_n_path = os.path.join(rlc_folder_path, year, n_name)
    if os.path.exists(rlc_n_path):
        proc_logger.debug("The RLC " + rlc_n_path + " is present.")
        if rlc_subtype.__eq__("N"):
            months_found[salary_date][1] = True  # RLC L00 of type N is found
        elif rlc_subtype.__eq__("P"):
            months_found[salary_date][2] = True  # RLC L00 of type P is found
        return rlc_n_path
    else:
        proc_logger.error("Monthly salary was found, but the expected L" + rlc_type + " RLC of type " + rlc_subtype + " was "
                                                                                                                 "not found in the "
                                                                                                                 "expected location "
                                                                                                                 "" + str(
            rlc_n_path) + ". Skipping merge of this salary file.")
        raise ValueError("File was not detected")  # TODO custom except


def process_generic_rlc(rlc_type, salary_date, salary_file_path, rlc_folder_path, naf_dir, salary_output_path,
                        salaries_found):
    salaries_found[salary_date][0] = True  # Monthly salary is found
    proc_logger = build_process_logger(logger, "Salaries and RLCs L00 / L13")
    try:
        rlc_n_path = process_rlc_aux(salary_date, rlc_folder_path, salaries_found,
                                     "N", rlc_type)
        proc_logger.debug("Expected RLC N path is: " + rlc_n_path)
        rlc_p_path = process_rlc_aux(salary_date, rlc_folder_path, salaries_found,
                                     "P", rlc_type)
        proc_logger.debug("Expected RLC P path is: " + rlc_p_path)
    except ValueError:
        proc_logger.error("Some of the RLC documents (N or P) has not been found. The salary file " + salary_file_path
                     + " will be skipped.")
        return

    pdf_path_list = [rlc_n_path, rlc_p_path]
    pdf_merged_name = salary_date.year.__str__() + unparse_month(salary_date) + "_L" + rlc_type + "Merge.pdf"
    merge_pdfs(pdf_path_list, os.path.join(naf_dir, RLCS_OUTPUT_NAME, pdf_merged_name))


def process_rlc_l03(salary_file_path, salary_page_number, salary_page, salary_date, naf_dir, rlc_folder_path,
                    salary_output_path, months_found):
    proc_logger = build_process_logger(logger, "Salaries and RLCs L03")

    proc_logger.info("Salary file " + salary_file_path + " page " +
                str(salary_page_number + 1) + " has been selected as delay salary for date " +
                unparse_date(salary_date))
    try:
        delay_initial_date, delay_end_date = parse_dates_from_delayed_salary(salary_page)
    except ValueError as exc:
        proc_logger.error("The delay date could not be parsed from the delay salary page. This document will be "
                     "skipped from search. The internal error is " + exc.__str__())
        return
    proc_logger.debug("Initial date is " + unparse_date(delay_initial_date, "-") + " and end date is " +
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
            proc_logger.debug("Breaking out of the bucle because " + rlc_path_n +
                         "does not exist.")
            break
        if is_date_present_in_rlc_delay(delay_initial_date, delay_end_date, rlc_path_n):
            months_found[salary_date][1] = True  # Delay salary N found
            rlc_path_p = rlc_partial_path + "P" + str_suffix + ".pdf"
            pdf_path_list = []
            pdf_merged_name = salary_date.year.__str__() + unparse_month(
                salary_date) + "_L03Merge" + str_suffix + ".pdf"
            pdf_output_path = os.path.join(naf_dir, RLCS_OUTPUT_NAME, pdf_merged_name)
            if not os.path.exists(rlc_path_p):
                proc_logger.debug("Breaking out of the bucle because " + rlc_path_p +
                             "does not exist.")
            months_found[salary_date][2] = True  # Delay salary P is found
            # pdf_path_list.append(salary_output_path)  # Do not add salary to RLC merge
            pdf_path_list.append(rlc_path_n)
            pdf_path_list.append(rlc_path_p)
            merge_pdfs(pdf_path_list, pdf_output_path)
            break
        suffix += 1


def process_salaries_with_rlc(salaries_folder_path, rlc_folder_path, naf_dir, naf, begin, end):
    proc_logger = build_process_logger(logger, "Salaries and RLCs")
    regular_monthly_salaries_rlcs_found = get_rlc_monthly_result_structure(begin,
                                                                           end)  # regular monthly salary, RLC-N, RLC-P
    regular_settlement_salaries_rlcs_found = get_rlc_monthly_result_structure(begin,
                                                                              end)  # regular settlement salary, RLC-N, RLC-P
    delay_salaries_rlcs_found = get_rlc_monthly_result_structure(begin, end)  # delay salary, RLC-N, RLC-P
    # Salaries, RLC L00, RLC L03
    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    salary_files = flatten_dirs(salaries_folder_path)
    # Select all salary sheets that are in range with the date (begin and end date included)
    salary_files_selected = []
    for salary_file in salary_files:
        dir_date = parse_date_from_salary_filename(parse_salary_filename_from_salary_path(salary_file))
        if begin <= dir_date <= end:
            salary_files_selected.append(salary_file)
            proc_logger.debug(
                "Salary file " + str(salary_file) + " is selected, because its date is " + unparse_date(dir_date,
                                                                                                        "-") + ".")

    # Write sheets to NAF folder that match the supplied NAF
    salary_files_selected.sort()
    for salary_file in salary_files_selected:
        proc_logger.debug("Processing file " + salary_file)
        salary_file_path = os.path.join(salaries_folder_path, salary_file)
        salary_file_name = parse_salary_filename_from_salary_path(salary_file_path)
        salary_date = parse_date_from_salary_filename(salary_file_name)
        salary_pages = get_matching_pages(salary_file_path, naf.slash_dash_str())
        if len(salary_pages) == 0:
            proc_logger.debug("NAF " + naf.__str__() + " was not detected in PDF " + str(salary_file) +
                         ". Skipping document.")
            continue
        for salary_page, salary_page_number in salary_pages:
            salary_output_path = os.path.join(naf_dir, SALARIES_OUTPUT_NAME, salary_file_name)

            index = 2
            while os.path.exists(salary_output_path):
                salary_output_path = os.path.join(naf_dir, SALARIES_OUTPUT_NAME,
                                                  salary_file_name.split(".")[0] + "_" + str(index) + ".pdf")
                index += 1

            write_page(salary_page, salary_output_path)

            proc_logger.info("Detected NAF " + naf.__str__() + " in PDF salary " + str(salary_file_path) + ", page " +
                        str(salary_page_number + 1) + ". Saving page in " +
                        salary_output_path.__str__() + " and further processing it.")

            # Now check if salary_file is delay, so we need to proceed to L03 or regular (L00 or L13) procedure
            salary_type = parse_salary_type(salary_file_path)
            if salary_type == SalaryType.DELAY:  # process L03 RLCs
                delay_salaries_rlcs_found[salary_date][0] = True
                process_rlc_l03(salary_file_path, salary_page_number, salary_page, salary_date,
                                naf_dir, rlc_folder_path, salary_output_path, delay_salaries_rlcs_found)
            elif salary_type == SalaryType.REGULAR:  # process L00 and L13 RLCs
                proc_logger.info("Salary file " + salary_file_path + " page " +
                            str(salary_page_number + 1) + " has been selected as regular salary for date " +
                            unparse_date(salary_date))
                try:
                    regular_salary_type = parse_regular_salary_type(salary_page)
                except UndefinedRegularSalaryType as e:
                    proc_logger.error("Salary file " + salary_file_path + " page " +
                                 str(salary_page_number + 1) + " is a type not supported or can not be recognized. "
                                                               "Skipping to next page. Internal error is: " + e.__str__())
                    continue
                if regular_salary_type == RegularSalaryType.MONTHLY:
                    proc_logger.info("Salary file " + salary_file_path + " page " +
                                str(salary_page_number + 1) + " has been selected as regular monthly salary for date " +
                                unparse_date(salary_date))
                    process_generic_rlc("00", salary_date, salary_file_path, rlc_folder_path, naf_dir,
                                        salary_output_path, regular_monthly_salaries_rlcs_found)
                elif regular_salary_type == RegularSalaryType.SETTLEMENT:
                    proc_logger.info("Salary file " + salary_file_path + " page " +
                                str(salary_page_number + 1) + " has been selected as regular settlement salary for "
                                                              "date " +
                                unparse_date(salary_date))
                    process_generic_rlc("13", salary_date, salary_file_path, rlc_folder_path, naf_dir,
                                        salary_output_path, regular_settlement_salaries_rlcs_found)
                else:
                    proc_logger.error("The regular salary type is not recognized. This RLC will be skipped.")
                    continue

            elif salary_type.__eq__(SalaryType.EXTRA):
                proc_logger.info("Salary file " + salary_file_path + " page " +
                            str(salary_page_number + 1) + " has been selected as extra salary for date " +
                            unparse_date(salary_date))
                continue
            else:
                proc_logger.error(
                    "Detected type " + salary_type.__str__() + " that is not a recognized type. The current salary "
                                                               "file will be ignored")

    r = {RLCType.REGULAR: regular_monthly_salaries_rlcs_found,
         RLCType.SETTLEMENT: regular_settlement_salaries_rlcs_found, RLCType.DELAY: delay_salaries_rlcs_found}

    return r


def process_proofs(proofs_folder_path, naf_dir, naf, begin, end, naf_to_dni):
    proc_logger = build_process_logger(logger, "Bank proofs")
    # Flatten year directories (flat list of document for all years)
    all_bankproof_folders = flatten_dirs(proofs_folder_path)

    # Select all bankproof folder that are in range with the date (begin and end date included)
    bankproof_folders_selected = []
    for bankproof_folder in all_bankproof_folders:
        dir_date = parse_date(bankproof_folder.split("/")[1][:6], "%m%Y")
        if begin <= dir_date <= end:
            bankproof_folders_selected.append(bankproof_folder)
            proc_logger.debug(
                "Proof folder " + bankproof_folder + " is selected, because its date is " + unparse_date(dir_date,
                                                                                                         "-") + ".")

    # Write sheets to NAF folder that match the DNI
    proofs_dir = os.path.join(naf_dir, PROOFS_OUTPUT_NAME)
    for bankproof_folder in bankproof_folders_selected:
        bank = "_".join(bankproof_folder.split("_")[1:])
        proc_logger.debug("Working with folder " + bankproof_folder + ". Bank type is " + bank)
        if (bank.__eq__("BBVA") or bank.__eq__("BBVA_endarreriments") or bank.__eq__("BBVA_endarreriments") or
                bank.__eq__("BBVA_FINIQUITO")):
            for bankproof_file in list_dir(os.path.join(proofs_folder_path, bankproof_folder)):
                try:
                    page = get_matching_page(os.path.join(proofs_folder_path, bankproof_folder, bankproof_file),
                                             naf_to_dni[naf], "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]")
                except ValueError as e:
                    proc_logger.debug(
                        "NAF " + naf.__str__() + " not detected in " + bankproof_file + ". Error: " + e.__str__())
                    continue
                output_path = os.path.join(proofs_dir, bankproof_file)
                proc_logger.info(
                    "NAF " + naf.__str__() + " was detected in " + bankproof_file + ". Writing page to " + output_path.__str__()
                    + ".")
                write_page(page, output_path)

        elif bank.__eq__("LA_CAIXA") or bank.__eq__("LA_CAIXA_EXTRA") or bank.__eq__("LA_CAIXA_endarreriments"):
            file_names = list_dir(os.path.join(proofs_folder_path, bankproof_folder))
            for file_name in file_names:
                try:
                    page = get_matching_page(os.path.join(proofs_folder_path, bankproof_folder, file_name),
                                             naf_to_dni[naf], "[A-Z]\\d{7}[A-Z]|\\d{8}[A-Z]")
                except ValueError as e:
                    proc_logger.debug("NAF " + naf.__str__() + " not detected in " + file_name + ". Error: " + e.__str__())
                    continue
                output_path = os.path.join(proofs_dir, file_name)
                proc_logger.info(
                    "NAF " + naf.__str__() + " was detected in " + file_name + ". Writing page to " + output_path.__str__() + ".")
                write_page(page, output_path)
        else:
            proc_logger.error(bank.__str__() + " is a bad bank. Skipping to next bank proof.")
            continue


def process_contracts(contracts_folder_path, naf_dir, naf, begin, end):
    proc_logger = build_process_logger(logger, "Contracts")
    found = False
    # Salaries
    # List all file names in the _salaries folder, in the ./input folder and remove undesired files
    contracts_files = list_dir(contracts_folder_path)
    contracts_files.sort()
    for contracts_file in contracts_files:
        naf_dirty = NAF(contracts_file.split("_")[0])
        dates = contracts_file.split(".")[0].split("_")
        proc_logger.debug("contract file: " + contracts_file)
        begin_date = parse_date("20" + dates[1], "%Y%m")
        if len(dates) == 3:  # Contract is temporary; has end date
            end_date = parse_date("20" + dates[1], "%Y%m")
        elif len(dates) == 2:  # Contract is undefined; has no end date
            end_date = datetime.max
        else:
            proc_logger.error("expected 3 fields in the name of the file " + contracts_file + " but " +
                         str(len(dates)) + " have been found. The file will be ignored until it has proper format.")
            continue

        if naf_dirty.__eq__(naf):
            proc_logger.debug(
                "NAF " + naf_dirty.__str__() + " of file " + contracts_file + " coincides with queried NAF. Checking dates...")
            # Select which contracts are valid during the range in the arguments
            # This conditional means that we select the contract if there is any coincidence in the range defined by
            # (begin, end) and (end_date, begin_date).
            if begin <= end_date and begin_date <= end:
                proc_logger.info(
                    contracts_file + " with date " + unparse_date(begin_date, "-") + ", " + unparse_date(end_date,
                                                                                                         "-") + "is in range "
                                                                                                                "of " + unparse_date(
                        begin, "-") + ", " + unparse_date(end, "-") + ". Copying it to " + naf_dir)
                try:
                    shutil.copy(src=os.path.join(contracts_folder_path, contracts_file),
                                dst=os.path.join(naf_dir, CONTRACTS_OUTPUT_NAME))
                    found = True
                except Exception as e:
                    proc_logger.critical("An error happened program will abort" + e)
                    exit(2)
    if not found:
        proc_logger.warning("Contract not found with NAF " + str(naf))
    return found


def process_RNTs(rnts_folder_path, naf_dir, naf, begin, end):
    rnts_found = get_rlc_monthly_result_structure(begin, end, False)  # regular monthly salary, RLC-N, RLC-P

    proc_logger = build_process_logger(logger, "RNTs")
    rnt_files = flatten_dirs(rnts_folder_path)
    rnt_files.sort()
    for rnt_file in rnt_files:
        file_date = parse_date("20" + rnt_file.split("/")[1][:4], "%Y%m")
        if begin <= file_date <= end:
            rnt_file_name = rnt_file.split("/")[1]
            rnt_file_name_without_extension = rnt_file_name.split(".")[0]
            rnt_path = os.path.join(rnts_folder_path, file_date.year.__str__(), rnt_file_name)
            rnt_partial_path_destination = os.path.join(naf_dir, RNTS_OUTPUT_NAME, rnt_file_name)
            proc_logger.info("RNT file " + rnt_path.__str__() + " is selected, because its date is " +
                        unparse_date(file_date) + ".")
            try:
                pages = get_matching_pages(rnt_path, naf.__str__(), r"\d{12}")
            except ValueError as e:
                proc_logger.debug("NAF " + naf.__str__() + " not detected in " + rnt_path + ". Error: " + e.__str__())
                continue
            for page, page_num in pages:
                rnt_path_destination = os.path.join(naf_dir, RNTS_OUTPUT_NAME,
                                                    rnt_file_name_without_extension + "_" + str(page_num) + ".pdf")
                proc_logger.info(
                    "NAF " + naf.__str__() + " was detected in " + rnt_path + " in page " + str(page_num + 1) +
                    ". Writing page to " + rnt_path_destination.__str__() + ".")
                write_page(page, rnt_path_destination)
                rnts_found[file_date] = True
        else:
            proc_logger.debug("RNT file " + rnt_file.__str__() + " is not selected, because its date is " +
                         unparse_date(file_date) + ".")

    return rnts_found


def main():
    start_time = time.time()

    args = process_parse_arguments()

    tenant_id = read_secret('TENANT_ID')
    client_id = read_secret('CLIENT_ID')
    client_secret = read_secret('CLIENT_SECRET')
    token_manager = TokenManager(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)
    sharepoint_domain = read_secret('SHAREPOINT_DOMAIN')
    site_name = read_secret('SITE_NAME')
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)
    drive_id = get_drive_id(token_manager, site_id, drive_name="Documents")
    carpeta_sharepoint = read_secret("SHAREPOINT_FOLDER_INPUT")

    # Ensure fresh input data
    if args.input == "sharepoint":
        remove_folder(INPUT_FOLDER)
        download_input_folder(token_manager, drive_id, carpeta_sharepoint, INPUT_FOLDER)
    elif args.input == "local":
        pass

    start_time = time.time()

    NAF_TO_DNI = build_naf_to_dni(NAF_DATA_PATH)
    # Build dictionaries to translate NAF to different identifier data
    NAF_TO_NAME = build_naf_to_name_and_surname(NAF_DATA_PATH)

    now = datetime.now().strftime("%Y-%m-%d_%H,%M,%S")

    id_str = compute_id(now, args, NAF_TO_NAME)
    impersonal_id_str = compute_impersonal_id(now, args, NAF_TO_NAME)

    current_user_folder, current_justification_folder, user_report_file, admin_log_path, supervisor_log_path = (
        compute_paths(args, id_str, impersonal_id_str))

    ensure_file_structure(current_user_folder, current_justification_folder)

    # Define logger
    logger_instance = get_logger(user_report_file, admin_log_path, supervisor_log_path, debug_mode=True)
    set_logger(logger_instance)
    global logger
    logger = build_process_logger(logger_instance, "main process")

    # Log initial report
    logger.info(get_initial_user_report(args))

    # Stop timer for download process
    end_time = elapsed_time(start_time)
    logger.info("Time elapsed for downloading and validating input data: " + str(end_time) + ".")
    start_time = time.time()

    # Begin processing
    reports = {}
    # Salaries & RLC
    reports[DocType.SALARY] = process_salaries_with_rlc(SALARIES_FOLDER, RLCS_FOLDER, current_justification_folder,
                                                        args.naf, args.begin, args.end)
    salary_output_path = os.path.join(current_justification_folder, SALARIES_OUTPUT_NAME)
    rlc_output_path = os.path.join(current_justification_folder, RLCS_OUTPUT_NAME)
    if args.compact[DocType.SALARY]:
        compact_folder(salary_output_path)
    if args.compact[DocType.RLC]:
        compact_folder(rlc_output_path)

    # Bank proofs
    reports[DocType.PROOFS] = process_proofs(PROOFS_FOLDER, current_justification_folder, args.naf, args.begin,
                                             args.end, NAF_TO_DNI)
    proof_output_path = os.path.join(current_justification_folder, PROOFS_OUTPUT_NAME)
    if args.compact[DocType.PROOFS]:
        compact_folder(proof_output_path)

    # Contracts
    reports[DocType.CONTRACT] = process_contracts(CONTRACTS_FOLDER, current_justification_folder, args.naf,
                                                  args.begin, args.end)
    contract_output_path = os.path.join(current_justification_folder, CONTRACTS_OUTPUT_NAME)
    if args.compact[DocType.CONTRACT]:
        compact_folder(contract_output_path)

    # RNTs
    reports[DocType.RNT] = process_RNTs(RNTS_FOLDER, current_justification_folder, args.naf, args.begin, args.end)
    rnt_output_path = os.path.join(current_justification_folder, RNTS_OUTPUT_NAME)
    if args.compact[DocType.RNT]:
        compact_folder(rnt_output_path)

    final_logger = build_process_logger(logger_instance, "Final report")
    report_text = get_end_user_report(reports, args)
    final_logger.info(report_text)

    end_time = elapsed_time(start_time)
    logger.info("Time elapsed for doing this justification: " + str(end_time) + ".")
    start_time = time.time()
    elapsed_time(start_time)

    upload_folder_recursive(
        token_manager=token_manager,
        drive_id=drive_id,
        local_folder_path=current_justification_folder,
        remote_folder_path=read_secret("SHAREPOINT_FOLDER_OUTPUT") + "/" + args.author + "/" + impersonal_id_str
    )

    SHAREPOINT_FOLDER_OUTPUT = read_secret("SHAREPOINT_FOLDER_OUTPUT")
    upload_file(token_manager, drive_id, SHAREPOINT_FOLDER_OUTPUT + "/" + "_admin_logs/" + os.path.basename(admin_log_path), admin_log_path)
    upload_file(token_manager, drive_id, SHAREPOINT_FOLDER_OUTPUT + "/" + "_supervisor_logs/" + os.path.basename(supervisor_log_path), supervisor_log_path)

    end_time = elapsed_time(start_time)
    logger.info("Time elapsed for uploading data: " + str(end_time) + ".")
    start_time = time.time()
    elapsed_time(start_time)


if __name__ == "__main__":
    main()
