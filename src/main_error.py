import argparse
import os

from arguments import parse_id
from sharepoint import update_list_item_field, upload_folder_recursive, get_drive_id, get_site_id, upload_file
from TokenManager import get_token_manager
from secret import read_secret
from defines import ADMIN_LOG_FOLDER


def get_first_log_path(log_dir: str) -> str:
    """Return the full path to the first regular file inside the directory."""
    if not os.path.isdir(log_dir):
        raise ValueError(f"'{log_dir}' is not a valid directory")

    for entry in os.listdir(log_dir):
        full_path = os.path.join(log_dir, entry)
        if os.path.isfile(full_path):
            return full_path

    raise FileNotFoundError(f"No files found in directory: {log_dir}")


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-r", "--request", "--id", type=parse_id, required=True,
                        help='ID of the justification request in Microsoft List of Peticions Justificacions.')
    args = parser.parse_args()
    update_list_item_field(args.request, {"Estatworkflow": "Error"})

    SUPERVISOR_LOG_PATH = get_first_log_path(ADMIN_LOG_FOLDER)

    token_manager = get_token_manager()
    sharepoint_domain = read_secret('SHAREPOINT_DOMAIN')
    site_name = read_secret('SITE_NAME')
    site_id = get_site_id(token_manager, sharepoint_domain, site_name)
    drive_id = get_drive_id(token_manager, site_id, drive_name="Documents")

    upload_file(token_manager,
                drive_id,
                os.path.join(read_secret("SHAREPOINT_FOLDER_OUTPUT"), "_admin_logs", os.path.basename(SUPERVISOR_LOG_PATH)),
                SUPERVISOR_LOG_PATH)


if __name__ == "__main__":
    main()
