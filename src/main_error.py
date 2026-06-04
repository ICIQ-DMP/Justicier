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

"""Error handler entry point: marks the request as failed and uploads the admin log."""

import argparse
from pathlib import Path

from arguments import parse_id
from sharepoint import (
    update_list_item_field,
    get_drive_id,
    get_site_id,
    upload_file,
)
from TokenManager import get_token_manager
from secret import read_secret
from defines import ADMIN_LOG_FOLDER


def get_first_log_path(log_dir: Path) -> Path:
    """Return the path to the first regular file inside the directory."""
    if not log_dir.is_dir():
        raise ValueError(f"'{log_dir}' is not a valid directory")

    for entry in log_dir.iterdir():
        if entry.is_file():
            return entry

    raise FileNotFoundError(f"No files found in directory: {log_dir}")


def main() -> None:
    """Mark a request as failed in SharePoint and upload the admin log."""
    parser = argparse.ArgumentParser(description="")
    parser.add_argument(
        "-r",
        "--request",
        "--id",
        type=parse_id,
        required=True,
        help="ID of the justification request in Microsoft List of Peticions Justificacions.",
    )
    args = parser.parse_args()
    update_list_item_field(args.request, {"Estatworkflow": "Error"})

    if ADMIN_LOG_FOLDER.is_dir():  # Only upload when the folder is detected
        supervisor_log_path = get_first_log_path(ADMIN_LOG_FOLDER)
        token_manager = get_token_manager()
        sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
        site_name = read_secret("SITE_NAME")
        site_id = get_site_id(token_manager, sharepoint_domain, site_name)
        drive_id = get_drive_id(token_manager, site_id, drive_name="Documents")

        upload_file(
            token_manager,
            drive_id,
            read_secret("SHAREPOINT_FOLDER_OUTPUT")
            + "/_admin_logs/"
            + supervisor_log_path.name,
            supervisor_log_path,
        )


if __name__ == "__main__":
    main()
