import os
import shutil
from datetime import datetime

from defines import GENERAL_OUTPUT_FOLDER, ADMIN_LOG_FOLDER, SUPERVISOR_LOG_FOLDER, SALARIES_OUTPUT_NAME, \
    PROOFS_OUTPUT_NAME, CONTRACTS_OUTPUT_NAME, RNTS_OUTPUT_NAME, RLCS_OUTPUT_NAME, SALARIES_AND_PROOFS_OUTPUT_NAME


def read_env_var(var_name):
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
    # Check if the environment variable exists
    if var_name not in os.environ:
        raise KeyError(f"The environment variable '{var_name}' does not exist.")

    # Read the value
    value = os.environ[var_name]

    # Check if the value is empty
    if not value:
        raise ValueError(f"The environment variable '{var_name}' is empty.")

    return value


def read_file_content(file_path):
    content = read_file(file_path)
    # Check if the file is empty or contains only whitespace
    if not content:
        raise ValueError(f"The file '{file_path}' is empty.")

    return content


def read_file(file_path):
    """
    Reads a file and returns its content.
    Handles edge cases such as the file not existing or being unreadable.

    Args:
        file_path (str): Path to the token file.

    Returns:
        str: The content of the file.

    Raises:
        FileNotFoundError: If the file does not exist.
        PermissionError: If the file cannot be read due to permission issues.
    """
    # Check if the file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file '{file_path}' does not exist.")

    # Check if the file is readable
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"The file '{file_path}' cannot be read. Check permissions.")

    # Read the file
    with open(file_path, "r") as file:
        content = file.read()

    return content


def ensure_output_gitignore():
    # Ensure existence of .gitignore
    gitignore_path = os.path.join(GENERAL_OUTPUT_FOLDER, '.gitignore')
    gitignore_content = "*\n!.gitignore\n"
    with open(gitignore_path, 'w+') as f:
        f.write(gitignore_content)


def list_dir(input_folder):
    """Returns a list of all file names in the ./input/salaries directory."""
    # Ensure the input_folder is a valid directory
    if not os.path.isdir(input_folder):
        raise ValueError("input folder " + input_folder + " in list_files function is not a directory or can't be accessed")

    # List all files in the directory
    file_names = [os.path.basename(file) for file in os.listdir(input_folder)]

    return file_names


def flatten_dirs(folder_to_flat):
    # List all file names in the _bank_proofs folder, in the ./input folder and remove undesired files
    subfolder_year = list_dir(folder_to_flat)
    if ".gitignore" in subfolder_year:
        subfolder_year.remove(".gitignore")
    # Flatten year directories (flat list of document for all years)
    flatted_folders = []
    for folder_year in subfolder_year:
        for folder in list_dir(os.path.join(folder_to_flat, folder_year)):
            flatted_folders.append(os.path.join(folder_year, folder))

    return flatted_folders


def compute_id(now, args, naf_to_name):
    return (now + "_" + args.author + "_" + args.naf.__str__() + "_" + str(naf_to_name[args.naf]) + "_" +
            args.begin.strftime("%Y-%m") + "-" + args.end.strftime("%Y-%m"))


def compute_impersonal_id(now, args, naf_to_name):
    return (now + "_" + args.naf.__str__() + "_" + str(naf_to_name[args.naf]) + "_" +
            args.begin.strftime("%Y-%m") + "-" + args.end.strftime("%Y-%m"))


def compute_paths(args, id_str, impersonal_id_str):
    log_filename = id_str + ".log.txt"
    log_filename_impersonal = impersonal_id_str + ".log.txt"

    # Admin logs
    ADMIN_LOG_PATH = os.path.join(ADMIN_LOG_FOLDER, log_filename)
    SUPERVISOR_LOG_PATH = os.path.join(SUPERVISOR_LOG_FOLDER, log_filename)

    # Home folder of the user
    CURRENT_USER_FOLDER: str = os.path.join(GENERAL_OUTPUT_FOLDER, args.author)

    # Folder for the current justification
    justification_name = id_str
    CURRENT_JUSTIFICATION_FOLDER = os.path.join(CURRENT_USER_FOLDER, justification_name)

    USER_REPORT_FILE = os.path.join(CURRENT_JUSTIFICATION_FOLDER, log_filename_impersonal)
    return CURRENT_USER_FOLDER, CURRENT_JUSTIFICATION_FOLDER, USER_REPORT_FILE, ADMIN_LOG_PATH, SUPERVISOR_LOG_PATH


def remove_folder(folder_path):
    """Remove the folder at the given path if it exists. Do nothing if it doesn't."""
    try:
        shutil.rmtree(folder_path)
    except FileNotFoundError:
        pass  # Do nothing if the folder does not exist
    except Exception as e:
        print(f"Error removing folder {folder_path}: {e}")


def ensure_file_structure(CURRENT_USER_FOLDER, CURRENT_JUSTIFICATION_FOLDER):
    os.makedirs(GENERAL_OUTPUT_FOLDER, exist_ok=True)
    ensure_output_gitignore()

    os.makedirs(ADMIN_LOG_FOLDER, exist_ok=True)
    os.makedirs(SUPERVISOR_LOG_FOLDER, exist_ok=True)
    os.makedirs(CURRENT_USER_FOLDER, exist_ok=True)

    os.makedirs(CURRENT_JUSTIFICATION_FOLDER, exist_ok=True)

    os.makedirs(os.path.join(CURRENT_JUSTIFICATION_FOLDER, SALARIES_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(CURRENT_JUSTIFICATION_FOLDER, PROOFS_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(CURRENT_JUSTIFICATION_FOLDER, CONTRACTS_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(CURRENT_JUSTIFICATION_FOLDER, RNTS_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(CURRENT_JUSTIFICATION_FOLDER, RLCS_OUTPUT_NAME), exist_ok=True)
    os.makedirs(os.path.join(CURRENT_JUSTIFICATION_FOLDER, SALARIES_AND_PROOFS_OUTPUT_NAME), exist_ok=True)

