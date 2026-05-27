import argparse
import datetime
import logging
import time
from pathlib import Path

from NAF import build_naf_to_dni, build_naf_to_name, build_naf_to_email
from TokenManager import get_token_manager
from arguments import process_parse_arguments
from chrono import elapsed_time
from defines import (
    SALARIES_OUTPUT_NAME,
    PROOFS_OUTPUT_NAME,
    RLCS_OUTPUT_NAME,
    DocType,
    SALARIES_AND_PROOFS_OUTPUT_NAME,
    CONTRACTS_OUTPUT_NAME,
    RNTS_OUTPUT_NAME,
    RNTS_AND_RLCS_OUTPUT_NAME,
    ROOT_FOLDER,
)
from filesystem import (
    remove_folder,
    compute_id,
    compute_impersonal_id,
    compute_paths,
    ensure_file_structure,
)
from logger import get_logger, setup_logging
from mail import mail_process
from pdf import merge_pdfs, compact_folder, merge_equal_files_from_two_folders
from report import get_end_user_report, get_initial_user_report
from secret import read_secret
from sharepoint import (
    download_input_folder,
    upload_folder_recursive,
    upload_file,
    get_site_id,
    get_drive_id,
    update_list_item_field,
    get_sharepoint_web_url,
)
from TokenManager import TokenManager
from tasks import (
    reverse_dict,
    complete_arguments,
    process_salaries_with_rlc,
    process_proofs,
    process_contracts,
    process_RNTs,
    merge_rnts_rlcs,
)

log = get_logger(__name__)


def _connect_sharepoint() -> tuple[TokenManager, str, str]:
    token_manager = get_token_manager()
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)
    drive_id = get_drive_id(token_manager, site_id, drive_name="Documents")
    return token_manager, site_id, drive_id


def process(args: argparse.Namespace, input_folder: Path) -> tuple[str, str]:
    if args.request:
        update_list_item_field(args.request, {"Estatworkflow": "En execució"})

    SALARIES_FOLDER: Path = input_folder / "_salaries"
    PROOFS_FOLDER: Path = input_folder / "_proofs"
    CONTRACTS_FOLDER: Path = input_folder / "_contracts"
    RNTS_FOLDER: Path = input_folder / "_RNT"
    RLCS_FOLDER: Path = input_folder / "_RLC"

    NAF_DATA_PATH: Path = input_folder / "NAF_DNI.xlsx"

    start_time = time.time()

    if args.location == "sharepoint":
        token_manager, site_id, drive_id = _connect_sharepoint()
        carpeta_sharepoint = read_secret("SHAREPOINT_FOLDER_INPUT")
        remove_folder(input_folder)
        download_input_folder(token_manager, drive_id, carpeta_sharepoint, input_folder)

    NAF_TO_DNI = build_naf_to_dni(NAF_DATA_PATH)
    DNI_TO_NAF = reverse_dict(NAF_TO_DNI)
    NAF_TO_NAME = build_naf_to_name(NAF_DATA_PATH)
    NAME_TO_NAF = reverse_dict(NAF_TO_NAME)
    NAF_TO_EMAIL = build_naf_to_email(NAF_DATA_PATH)
    EMAIL_TO_NAF = reverse_dict(NAF_TO_EMAIL)

    complete_arguments(
        args,
        NAME_TO_NAF,
        NAF_TO_DNI,
        DNI_TO_NAF,
        NAF_TO_NAME,
        EMAIL_TO_NAF,
        NAF_TO_EMAIL,
    )

    now = datetime.datetime.now().strftime("%Y-%m-%d_%H,%M,%S")

    id_str = compute_id(now, args, NAF_TO_NAME)
    impersonal_id_str = compute_impersonal_id(now, args, NAF_TO_NAME)

    (
        current_user_folder,
        current_justification_folder,
        user_report_file,
        admin_log_path,
        supervisor_log_path,
    ) = compute_paths(args, id_str, impersonal_id_str)

    ensure_file_structure(current_user_folder, current_justification_folder)

    setup_logging(
        level=logging.DEBUG,
        user_report_file=user_report_file,
        admin_log_file=admin_log_path,
        supervisor_log_file=supervisor_log_path,
    )

    log = get_logger(__name__)

    log.info(get_initial_user_report(args))

    end_time = elapsed_time(start_time)
    log.info(f"Time elapsed for obtaining and validating input data: {end_time}.")
    start_time = time.time()

    # Salaries & RLC
    salary_output_path: Path = current_justification_folder / SALARIES_OUTPUT_NAME
    salaries_with_rlcs_result = process_salaries_with_rlc(
        SALARIES_FOLDER,
        RLCS_FOLDER,
        current_justification_folder,
        args.naf,
        args.begin,
        args.end,
    )

    # Bank proofs
    proof_output_path: Path = current_justification_folder / PROOFS_OUTPUT_NAME
    process_proofs(
        PROOFS_FOLDER, proof_output_path, args.naf, args.begin, args.end, NAF_TO_DNI
    )

    rlc_output_path: Path = current_justification_folder / RLCS_OUTPUT_NAME
    if args.merge_salary:
        salaries_and_bankproofs_output_path: Path = (
            current_justification_folder / SALARIES_AND_PROOFS_OUTPUT_NAME
        )
        merge_equal_files_from_two_folders(
            salary_output_path, proof_output_path, salaries_and_bankproofs_output_path
        )
        if args.merge_result[DocType.SALARIES_AND_PROOFS]:
            compact_folder(salaries_and_bankproofs_output_path)
    if args.merge_result[DocType.SALARY]:
        compact_folder(salary_output_path)
    if args.merge_result[DocType.RLC]:
        compact_folder(rlc_output_path)
    if args.merge_result[DocType.PROOFS]:
        compact_folder(proof_output_path)

    # Contracts
    contracts_result = process_contracts(
        CONTRACTS_FOLDER,
        current_justification_folder,
        args.naf,
        args.begin,
        args.end,
    )
    contract_output_path: Path = current_justification_folder / CONTRACTS_OUTPUT_NAME
    if args.merge_result[DocType.CONTRACT]:
        compact_folder(contract_output_path)

    # RNTs
    rnts_result = process_RNTs(
        RNTS_FOLDER, current_justification_folder, args.naf, args.begin, args.end
    )
    rnt_output_path: Path = current_justification_folder / RNTS_OUTPUT_NAME
    if args.merge_result[DocType.RNT]:
        compact_folder(rnt_output_path)

    # Merge RLC & RNT
    if args.merge_rnt_rlc:
        log.info("Starting the merge of RNT and RLC")
        if args.merge_result[DocType.RNT] or args.merge_result[DocType.RLC]:
            rnts_merged_path: Path = current_justification_folder / "RNTs.pdf"
            rlcs_merged_path: Path = current_justification_folder / "RLCs.pdf"
            if rnts_merged_path.exists() and rlcs_merged_path.exists():
                rnt_rlc_merged_output_path: Path = (
                    current_justification_folder / "RNTs i RLCs.pdf"
                )
                merge_pdfs(
                    [rnts_merged_path, rlcs_merged_path],
                    rnt_rlc_merged_output_path,
                    True,
                )
            else:
                log.warning(
                    "The merge of RNT and RLC was not done because we were also instructed to merge each type"
                    " of document in a single file, but either RNTs.pdf or RLCs.pdf with the final results"
                    " of the merge do not exist, so the merge will not be done. Try again without marking"
                    " the option to merge the documents, only mark RLC and RNT merging"
                )
        else:
            (current_justification_folder / RNTS_AND_RLCS_OUTPUT_NAME).mkdir(
                parents=True, exist_ok=True
            )
            merge_rnts_rlcs(
                current_justification_folder / RNTS_OUTPUT_NAME,
                current_justification_folder / RLCS_OUTPUT_NAME,
                current_justification_folder / RNTS_OUTPUT_NAME,
                current_justification_folder / RLCS_OUTPUT_NAME,
                current_justification_folder / RNTS_AND_RLCS_OUTPUT_NAME,
                args.begin,
                args.end,
            )

    report_text = get_end_user_report(
        salaries_with_rlcs_result=salaries_with_rlcs_result,
        contracts_result=contracts_result,
        rnts_result=rnts_result,
        args=args,
    )
    log.info(report_text)

    if args.request:
        end_time = elapsed_time(start_time)
        log.info(f"Time elapsed for doing this justification: {end_time}.")
        start_time = time.time()
        elapsed_time(start_time)

        token_manager, site_id, drive_id = _connect_sharepoint()
        SHAREPOINT_FOLDER_OUTPUT = read_secret("SHAREPOINT_FOLDER_OUTPUT")
        remote_output_path = (
            f"{SHAREPOINT_FOLDER_OUTPUT}/{args.author}/{impersonal_id_str}"
        )
        remote_log_path = (
            f"{SHAREPOINT_FOLDER_OUTPUT}/_admin_logs/{admin_log_path.name}"
        )

        upload_folder_recursive(
            token_manager=token_manager,
            drive_id=drive_id,
            local_folder_path=current_justification_folder,
            remote_folder_path=remote_output_path,
        )

        link = get_sharepoint_web_url(
            token_manager, site_id, drive_id, remote_output_path
        )
        log.info(f"Clickable SharePoint URL: {link}  ")

        upload_file(token_manager, drive_id, remote_log_path, admin_log_path)
        log_link = get_sharepoint_web_url(
            token_manager, site_id, drive_id, remote_log_path
        )

        end_time = elapsed_time(start_time)
        log.info(f"Time elapsed for uploading data: {end_time}.")
        start_time = time.time()
        elapsed_time(start_time)

    if args.request:
        log.debug("Updating list element state to Completed")
        update_list_item_field(args.request, {"Estatworkflow": "Completat"})
        log.debug("Updating list element error message to no error message")
        update_list_item_field(args.request, {"Missatge_x0020_error": "-"})
        log.debug("Updating list element link to result")
        update_list_item_field(args.request, {"Resultat": link})

    return link, log_link


def main() -> None:
    setup_logging()
    args = process_parse_arguments()

    INPUT_FOLDER: Path = ROOT_FOLDER / "input"
    if args.input_location:
        INPUT_FOLDER = args.input_location

    result_link = ""
    log_link = ""
    try:
        result_link, log_link = process(args, INPUT_FOLDER)
    except ValueError as e:
        err = f"A not controlled error happen during execution of Justicier. Error is: {str(e)}"
        if args.request:
            update_list_item_field(args.request, {"Missatge_x0020_error": err})
        log.error(err)
        exit(1)

    log.info("Justification process is finished.")
    log.info("Sending notification email")

    mail_process(result_link, log_link, args)


if __name__ == "__main__":
    main()
