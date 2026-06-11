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

"""File-system helpers: directory creation, path computation, and output structure."""

import argparse
import os
import shutil
from pathlib import Path

from .naf import NAF
from .name import Name

from .defines import (
    LOCAL_GENERAL_OUTPUT_FOLDER_PATH,
    LOCAL_ADMIN_LOG_FOLDER_PATH,
    LOCAL_SUPERVISOR_LOG_FOLDER_PATH,
    SHAREPOINT_SALARIES_OUTPUT_FOLDER_NAME,
    SHAREPOINT_PROOFS_OUTPUT_FOLDER_NAME,
    SHAREPOINT_CONTRACTS_OUTPUT_FOLDER_NAME,
    SHAREPOINT_RNTS_OUTPUT_FOLDER_NAME,
    SHAREPOINT_RLCS_OUTPUT_FOLDER_NAME,
    SHAREPOINT_SALARIES_AND_PROOFS_OUTPUT_FOLDER_NAME,
    DATE_DEFAULT_FORMAT,
)
from .logger import get_logger

log = get_logger(__name__)


def read_env_var(var_name: str) -> str:
    """Reads an environment variable.

    Args:
        var_name (str): Name of the environment variable.

    Returns:
        str: The value of the environment variable if valid.

    Raises:
        KeyError: If the environment variable does not exist.
        ValueError: If the environment variable is empty or contains only whitespace.
    """
    if var_name not in os.environ:
        raise KeyError(f"The environment variable '{var_name}' does not exist.")

    value = os.environ[var_name]

    if not value:
        raise ValueError(f"The environment variable '{var_name}' is empty.")

    return value


def read_file_content(file_path: Path) -> str:
    """Read a file and return its non-empty content.

    Args:
        file_path: Path to the file.

    Returns:
        The file content as a string.

    Raises:
        ValueError: If the file exists but is empty.
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read.
    """
    content = read_file(file_path)
    if not content:
        raise ValueError(f"The file '{file_path}' is empty.")
    return content


def read_file(file_path: Path) -> str:
    """Reads a file and returns its content.

    Args:
        file_path (Path): Path to the file.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read due to permission issues.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    if not os.access(file_path, os.R_OK):
        raise PermissionError(
            f"The file '{file_path}' cannot be read. Check permissions."
        )

    with open(file_path, "r") as file:
        content = file.read()

    return content


def ensure_output_gitignore() -> None:
    """Write a ``.gitignore`` to the output folder that excludes everything but itself."""
    gitignore_path = LOCAL_GENERAL_OUTPUT_FOLDER_PATH / ".gitignore"
    gitignore_content = "*\n!.gitignore\n"
    with open(gitignore_path, "w+") as f:
        f.write(gitignore_content)


def list_dir(input_folder: Path) -> list[str]:
    """Returns a list of all file names in the given directory."""
    if not input_folder.is_dir():
        raise ValueError(
            f"input folder {input_folder} in list_files function is not a directory or can't be accessed"
        )
    return [f.name for f in input_folder.iterdir()]


def flatten_dirs(folder_to_flat: Path) -> list[Path]:
    """Returns a flat list of relative paths (year/filename) from a two-level directory."""
    subfolder_year = list_dir(folder_to_flat)
    if ".gitignore" in subfolder_year:
        subfolder_year.remove(".gitignore")
    flatted_folders = []
    for folder_year in subfolder_year:
        for name in list_dir(folder_to_flat / folder_year):
            flatted_folders.append(Path(folder_year) / name)
    return flatted_folders


def compute_id(now: str, args: argparse.Namespace, naf_to_name: dict[NAF, Name]) -> str:
    """Compute the full run identifier, including the requesting author.

    Args:
        now: Timestamp string for the current run.
        args: Parsed CLI arguments.
        naf_to_name: Mapping from NAF to employee Name.

    Returns:
        Unique identifier string for this run including the author email.
    """
    id_str = compute_impersonal_id(now, args, naf_to_name)
    return f"{id_str}_{args.author}"


def compute_impersonal_id(
    now: str, args: argparse.Namespace, naf_to_name: dict[NAF, Name]
) -> str:
    """Compute the run identifier without the requesting author.

    Args:
        now: Timestamp string for the current run.
        args: Parsed CLI arguments.
        naf_to_name: Mapping from NAF to employee Name.

    Returns:
        Unique identifier string for this run excluding the author email.

    Raises:
        KeyError: If the NAF is not found in *naf_to_name*.
    """
    id_str = ""
    if args.request:
        id_str = f"_{args.request}"
    try:
        name = str(naf_to_name[args.naf])
    except KeyError:
        log.debug(
            f"NAF provided was not possible to be translated into name, NAF is: {args.naf}"
        )
        raise KeyError
    r = (
        f"{now}_{args.naf}_{name.replace(' ', '_')}"
        f"_{args.begin.strftime(DATE_DEFAULT_FORMAT)}_{args.end.strftime(DATE_DEFAULT_FORMAT)}{id_str}"
    )
    return r


def compute_paths(
    args: argparse.Namespace, id_str: str, impersonal_id_str: str
) -> tuple[Path, Path, Path, Path, Path]:
    """Compute all output and log paths for a justification run.

    Args:
        args: Parsed CLI arguments (uses ``args.author``).
        id_str: Full run identifier (including author).
        impersonal_id_str: Run identifier without author.

    Returns:
        Tuple of ``(user_folder, justification_folder, user_report_file,
        admin_log_path, supervisor_log_path)``.
    """
    log_filename = id_str + ".log.txt"
    log_filename_impersonal = impersonal_id_str + ".log.txt"

    admin_log_path: Path = LOCAL_ADMIN_LOG_FOLDER_PATH / log_filename
    supervisor_log_path: Path = LOCAL_SUPERVISOR_LOG_FOLDER_PATH / log_filename

    current_user_folder: Path = LOCAL_GENERAL_OUTPUT_FOLDER_PATH / args.author
    justification_name = impersonal_id_str
    current_justification_folder: Path = current_user_folder / justification_name
    user_report_file: Path = current_justification_folder / log_filename_impersonal

    return (
        current_user_folder,
        current_justification_folder,
        user_report_file,
        admin_log_path,
        supervisor_log_path,
    )


def remove_folder(folder_path: Path) -> None:
    """Remove the folder at the given path if it exists. Do nothing if it doesn't."""
    try:
        shutil.rmtree(folder_path)
    except FileNotFoundError:
        pass
    except Exception as e:
        log.error(f"Error removing folder {folder_path}: {e}")


def ensure_file_structure(
    current_user_folder: Path, current_justification_folder: Path
) -> None:
    """Create the full output directory tree for a justification run.

    Args:
        current_user_folder: Root folder for the requesting user's output.
        current_justification_folder: Sub-folder for this specific justification run.
    """
    LOCAL_GENERAL_OUTPUT_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    ensure_output_gitignore()

    LOCAL_ADMIN_LOG_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    LOCAL_SUPERVISOR_LOG_FOLDER_PATH.mkdir(parents=True, exist_ok=True)
    current_user_folder.mkdir(parents=True, exist_ok=True)
    current_justification_folder.mkdir(parents=True, exist_ok=True)

    (current_justification_folder / SHAREPOINT_SALARIES_OUTPUT_FOLDER_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (current_justification_folder / SHAREPOINT_PROOFS_OUTPUT_FOLDER_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (current_justification_folder / SHAREPOINT_CONTRACTS_OUTPUT_FOLDER_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (current_justification_folder / SHAREPOINT_RNTS_OUTPUT_FOLDER_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (current_justification_folder / SHAREPOINT_RLCS_OUTPUT_FOLDER_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (
        current_justification_folder / SHAREPOINT_SALARIES_AND_PROOFS_OUTPUT_FOLDER_NAME
    ).mkdir(parents=True, exist_ok=True)


def get_first_file_path_in_folder(log_dir: Path) -> Path:
    """Return the path to the first regular file inside the directory."""
    if not log_dir.is_dir():
        raise ValueError(f"'{log_dir}' is not a valid directory")

    for entry in log_dir.iterdir():
        if entry.is_file():
            return entry

    raise FileNotFoundError(f"No files found in directory: {log_dir}")
