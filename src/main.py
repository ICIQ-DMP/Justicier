import os.path
import time
import datetime

import pytz

from NAF import build_naf_to_dni, build_naf_to_name, build_naf_to_email
from TokenManager import get_token_manager
from arguments import process_parse_arguments
from chrono import elapsed_time
from defines import *
from filesystem import *
from logger import get_logger, setup_logging
from mail import mail_process
from pdf import merge_pdfs, compact_folder, merge_equal_files_from_two_folders
from report import get_end_user_report, get_initial_user_report
from secret import read_secret
from sharepoint import download_input_folder, upload_folder_recursive, upload_file, get_site_id, get_drive_id, \
    update_list_item_field, get_sharepoint_web_url
from tasks import reverse_dict, complete_arguments, process_salaries_with_rlc, process_proofs, process_contracts, \
    process_RNTs, merge_rnts_rlcs


def process(args, INPUT_FOLDER):
    if args.request:
        update_list_item_field(args.request, {"Estatworkflow": "En execució"})

    tz = pytz.timezone("Europe/Madrid")

    # Obtain absolute path to the valid user list
    USER_LIST_DATA_PATH = os.path.join(INPUT_FOLDER, "input")

    # Obtain absolute paths for each input directory
    SALARIES_FOLDER = os.path.join(INPUT_FOLDER, "_salaries")
    PROOFS_FOLDER = os.path.join(INPUT_FOLDER, "_proofs")
    CONTRACTS_FOLDER = os.path.join(INPUT_FOLDER, "_contracts")
    RNTS_FOLDER = os.path.join(INPUT_FOLDER, "_RNT")
    RLCS_FOLDER = os.path.join(INPUT_FOLDER, "_RLC")

    NAF_DATA_PATH = os.path.join(INPUT_FOLDER, "NAF_DNI.xlsx")

    token_manager = get_token_manager()

    sharepoint_domain = read_secret('SHAREPOINT_DOMAIN')
    site_name = read_secret('SITE_NAME')
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)
    drive_id = get_drive_id(token_manager, site_id, drive_name="Documents")
    carpeta_sharepoint = read_secret("SHAREPOINT_FOLDER_INPUT")

    start_time = time.time()
    # Ensure fresh input data
    if args.location == "sharepoint":
        remove_folder(INPUT_FOLDER)
        download_input_folder(token_manager, drive_id, carpeta_sharepoint, INPUT_FOLDER)
    elif args.location == "local":
        pass

    # Build dictionaries to translate between different identifier data
    NAF_TO_DNI = build_naf_to_dni(NAF_DATA_PATH)
    DNI_TO_NAF = reverse_dict(NAF_TO_DNI)
    NAF_TO_NAME = build_naf_to_name(NAF_DATA_PATH)
    NAME_TO_NAF = reverse_dict(NAF_TO_NAME)
    NAF_TO_EMAIL = build_naf_to_email(NAF_DATA_PATH)
    EMAIL_TO_NAF = reverse_dict(NAF_TO_EMAIL)

    complete_arguments(args, NAME_TO_NAF, NAF_TO_DNI, DNI_TO_NAF, NAF_TO_NAME, EMAIL_TO_NAF, NAF_TO_EMAIL)

    now = datetime.datetime.now().strftime("%Y-%m-%d_%H,%M,%S")

    id_str = compute_id(now, args, NAF_TO_NAME)
    impersonal_id_str = compute_impersonal_id(now, args, NAF_TO_NAME)

    current_user_folder, current_justification_folder, user_report_file, admin_log_path, supervisor_log_path = (
        compute_paths(args, id_str, impersonal_id_str))

    ensure_file_structure(current_user_folder, current_justification_folder)

    # Define logger
    setup_logging(level=logging.DEBUG, user_report_file=user_report_file, admin_log_file=admin_log_path, supervisor_log_file=supervisor_log_path)

    log = get_logger(__name__)

    # Log initial report
    log.info(get_initial_user_report(args))

    # Stop timer for download process
    end_time = elapsed_time(start_time)
    log.info("Time elapsed for obtaining and validating input data: " + str(end_time) + ".")
    start_time = time.time()

    # Begin processing
    reports = {}
    # Salaries & RLC
    salary_output_path = os.path.join(current_justification_folder, SALARIES_OUTPUT_NAME)
    reports[DocType.SALARY] = process_salaries_with_rlc(SALARIES_FOLDER, RLCS_FOLDER, current_justification_folder,
                                                        args.naf, args.begin, args.end)

    # Bank proofs
    proof_output_path = os.path.join(current_justification_folder, PROOFS_OUTPUT_NAME)
    reports[DocType.PROOFS] = process_proofs(PROOFS_FOLDER, proof_output_path, args.naf, args.begin,
                                             args.end, NAF_TO_DNI)

    rlc_output_path = os.path.join(current_justification_folder, RLCS_OUTPUT_NAME)
    if args.merge_salary:
        salaries_and_bankproofs_output_path = os.path.join(current_justification_folder,
                                                           SALARIES_AND_PROOFS_OUTPUT_NAME)
        merge_equal_files_from_two_folders(salary_output_path, proof_output_path, salaries_and_bankproofs_output_path)
        if args.merge_result[DocType.SALARIES_AND_PROOFS]:
            compact_folder(salaries_and_bankproofs_output_path)
    # Process general after processing merge salary + bank proof
    if args.merge_result[DocType.SALARY]:
        compact_folder(salary_output_path)
    if args.merge_result[DocType.RLC]:
        compact_folder(rlc_output_path)
    if args.merge_result[DocType.PROOFS]:
        compact_folder(proof_output_path)

    # Contracts
    try:
        reports[DocType.CONTRACT] = process_contracts(CONTRACTS_FOLDER, current_justification_folder, args.naf,
                                                      args.begin, args.end)
    except Exception as e:
        if args.request:
            update_list_item_field(args.request, {"Estatworkflow": "Error", "Missatge_x0020_error":
                str(e)})
        raise ValueError
    contract_output_path = os.path.join(current_justification_folder, CONTRACTS_OUTPUT_NAME)
    if args.merge_result[DocType.CONTRACT]:
        compact_folder(contract_output_path)

    # RNTs
    reports[DocType.RNT] = process_RNTs(RNTS_FOLDER, current_justification_folder, args.naf, args.begin, args.end)
    rnt_output_path = os.path.join(current_justification_folder, RNTS_OUTPUT_NAME)
    if args.merge_result[DocType.RNT]:
        compact_folder(rnt_output_path)

    # Process fusion of RLC & RNT
    if args.merge_rnt_rlc:
        log.info("Starting the merge of RNT and RLC")
        if args.merge_result[DocType.RNT] or args.merge_result[DocType.RLC]:
            rnts_merged_path = os.path.join(current_justification_folder, "RNTs.pdf")  # TODO: remove hard-coded filename
            rlcs_merged_path = os.path.join(current_justification_folder, "RLCs.pdf")  # TODO: remove hard-coded filename
            if os.path.exists(rnts_merged_path) and os.path.exists(rlcs_merged_path):
                rnt_rlc_merged_paths = []
                rnt_rlc_merged_paths.append(rnts_merged_path)
                rnt_rlc_merged_paths.append(rlcs_merged_path)
                rnt_rlc_merged_output_path = os.path.join(current_justification_folder, "RNTs i RLCs.pdf")
                merge_pdfs(rnt_rlc_merged_paths, rnt_rlc_merged_output_path, True)
            else:
                log.warning("The merge of RNT and RLC was not done because we were also instructed to merge each type"
                               " of "
                               "document"
                               "in a single file, but either RNTs.pdf or RLCs.pdf with the final results of the merge "
                               "do not exist, so the merge will not be "
                               "done. Try again without marking the option to merge the documents, only mark RLC and "
                               "RNT merging")
        else:
            os.makedirs(os.path.join(current_justification_folder, RNTS_AND_RLCS_OUTPUT_NAME), exist_ok=True)
            merge_rnts_rlcs(
                os.path.join(current_justification_folder, RNTS_OUTPUT_NAME),
                os.path.join(current_justification_folder, RLCS_OUTPUT_NAME),
                current_justification_folder,
                args.begin,
                args.end
            )

    report_text = get_end_user_report(reports, args)
    log.info(report_text)

    end_time = elapsed_time(start_time)
    log.info("Time elapsed for doing this justification: " + str(end_time) + ".")
    start_time = time.time()
    elapsed_time(start_time)

    upload_folder_recursive(
        token_manager=token_manager,
        drive_id=drive_id,
        local_folder_path=current_justification_folder,
        remote_folder_path=read_secret("SHAREPOINT_FOLDER_OUTPUT") + "/" + args.author + "/" + impersonal_id_str
    )

    link = get_sharepoint_web_url(token_manager, site_id, drive_id,
                                  read_secret("SHAREPOINT_FOLDER_OUTPUT") + "/" + args.author + "/" + impersonal_id_str)
    log.info(f"Clickable SharePoint URL: {link}  ")  # Space at the end for separating from color codes

    SHAREPOINT_FOLDER_OUTPUT = read_secret("SHAREPOINT_FOLDER_OUTPUT")
    upload_file(token_manager, drive_id,
                SHAREPOINT_FOLDER_OUTPUT + "/" + "_admin_logs/" + os.path.basename(admin_log_path), admin_log_path)
    log_link = get_sharepoint_web_url(token_manager, site_id, drive_id, SHAREPOINT_FOLDER_OUTPUT + "/" + "_admin_logs/" + os.path.basename(admin_log_path))

    # Upload supervisor log only in case of error
    #upload_file(token_manager, drive_id,
    #            SHAREPOINT_FOLDER_OUTPUT + "/" + "_supervisor_logs/" + os.path.basename(supervisor_log_path),
    #            supervisor_log_path)

    end_time = elapsed_time(start_time)
    log.info("Time elapsed for uploading data: " + str(end_time) + ".")
    start_time = time.time()
    elapsed_time(start_time)

    if args.request:
        log.debug("Updating list element state to Completed")
        update_list_item_field(args.request, {"Estatworkflow": "Completat"})
        log.debug("Updating list element error message to no error message")
        update_list_item_field(args.request, {"Missatge_x0020_error": "-"})
        log.debug("Updating list element link to result")
        #update_resultat_sharepoint_rest(args.request, link)  # TODO: When field Resultat is URL or image, I need more
                                                              # permissions to update it using sharepoint API, can't use
                                                              # graph api
        update_list_item_field(args.request, {"Resultat": link})

    return link, log_link


def main():
    setup_logging()
    args = process_parse_arguments()

    if args.input_location:
        INPUT_FOLDER = args.input_location
    else:
        INPUT_FOLDER = os.path.join(ROOT_FOLDER, "input")

    try:
        result_link, log_link = process(args, INPUT_FOLDER)
    except ValueError as e:  # "Too broad exception clause" but I know exactly what I'm doing
        err = f"A not controlled error happen during execution of Justicier. Error is: {str(e)}"
        update_list_item_field(args.request, {"Missatge_x0020_error": err})
        mail_process(result_link, log_link, args)
        print(err)
        exit(1)

    print("Justification process is finished.")
    print("Sending notification email")

    mail_process(result_link, log_link, args)



if __name__ == "__main__":
    main()
