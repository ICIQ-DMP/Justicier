import argparse
import os
import shutil
from pathlib import Path

from NAF import NAF
from Name import Name

from defines import (
    GENERAL_OUTPUT_FOLDER,
    ADMIN_LOG_FOLDER,
    SUPERVISOR_LOG_FOLDER,
    SALARIES_OUTPUT_NAME,
    PROOFS_OUTPUT_NAME,
    CONTRACTS_OUTPUT_NAME,
    RNTS_OUTPUT_NAME,
    RLCS_OUTPUT_NAME,
    SALARIES_AND_PROOFS_OUTPUT_NAME,
)
from logger import get_logger

log = get_logger(__name__)


def read_env_var(var_name: str) -> str:
    """
    Reads an environment variable.

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
    content = read_file(file_path)
    if not content:
        raise ValueError(f"The file '{file_path}' is empty.")
    return content


def read_file(file_path: Path) -> str:
    """
    Reads a file and returns its content.

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
    gitignore_path = GENERAL_OUTPUT_FOLDER / ".gitignore"
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
    id_str = compute_impersonal_id(now, args, naf_to_name)
    return f"{id_str}_{args.author}"


def compute_impersonal_id(
    now: str, args: argparse.Namespace, naf_to_name: dict[NAF, Name]
) -> str:
    id_str = ""
    if args.request:
        id_str = f"_{args.request}"
    try:
        name = str(naf_to_name[args.naf])
    except KeyError:
        log.debug(f"NAF provided was not possible to be translated into name, NAF is: {args.naf}")
        raise KeyError
    r = f"{now}_{args.naf}_{name.replace(' ', '_')}_{args.begin.strftime('%Y-%m-%d')}_{args.end.strftime('%Y-%m-%d')}{id_str}"
    return r


def compute_paths(
    args: argparse.Namespace, id_str: str, impersonal_id_str: str
) -> tuple[Path, Path, Path, Path, Path]:
    log_filename = id_str + ".log.txt"
    log_filename_impersonal = impersonal_id_str + ".log.txt"

    ADMIN_LOG_PATH: Path = ADMIN_LOG_FOLDER / log_filename
    SUPERVISOR_LOG_PATH: Path = SUPERVISOR_LOG_FOLDER / log_filename

    CURRENT_USER_FOLDER: Path = GENERAL_OUTPUT_FOLDER / args.author
    justification_name = impersonal_id_str
    CURRENT_JUSTIFICATION_FOLDER: Path = CURRENT_USER_FOLDER / justification_name
    USER_REPORT_FILE: Path = CURRENT_JUSTIFICATION_FOLDER / log_filename_impersonal

    return (
        CURRENT_USER_FOLDER,
        CURRENT_JUSTIFICATION_FOLDER,
        USER_REPORT_FILE,
        ADMIN_LOG_PATH,
        SUPERVISOR_LOG_PATH,
    )


def remove_folder(folder_path: Path) -> None:
    """Remove the folder at the given path if it exists. Do nothing if it doesn't."""
    try:
        shutil.rmtree(folder_path)
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"Error removing folder {folder_path}: {e}")


def ensure_file_structure(
    current_user_folder: Path, current_justification_folder: Path
) -> None:
    GENERAL_OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    ensure_output_gitignore()

    ADMIN_LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    SUPERVISOR_LOG_FOLDER.mkdir(parents=True, exist_ok=True)
    current_user_folder.mkdir(parents=True, exist_ok=True)
    current_justification_folder.mkdir(parents=True, exist_ok=True)

    (current_justification_folder / SALARIES_OUTPUT_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (current_justification_folder / PROOFS_OUTPUT_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (current_justification_folder / CONTRACTS_OUTPUT_NAME).mkdir(
        parents=True, exist_ok=True
    )
    (current_justification_folder / RNTS_OUTPUT_NAME).mkdir(parents=True, exist_ok=True)
    (current_justification_folder / RLCS_OUTPUT_NAME).mkdir(parents=True, exist_ok=True)
    (current_justification_folder / SALARIES_AND_PROOFS_OUTPUT_NAME).mkdir(
        parents=True, exist_ok=True
    )
