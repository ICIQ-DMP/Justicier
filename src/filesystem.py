import os
from datetime import datetime

from NAF import NAF_TO_NAME
from defines import GENERAL_OUTPUT_FOLDER, ADMIN_LOG_FOLDER, SUPERVISOR_LOG_FOLDER, SALARIES_OUTPUT_NAME, \
    PROOFS_OUTPUT_NAME, CONTRACTS_OUTPUT_NAME, RNTS_OUTPUT_NAME, RLCS_OUTPUT_NAME


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


def compute_paths(args):
    NOW = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

    id_str = (NOW + "_" + args.author + "_" + args.naf.__str__() + "_" + NAF_TO_NAME[args.naf] + "_" +
              args.begin.strftime("%Y-%m") + "-" + args.end.strftime("%Y-%m") + ".log.txt")
    # Admin logs
    ADMIN_LOG_PATH = os.path.join(ADMIN_LOG_FOLDER, id_str)
    SUPERVISOR_LOG_PATH = os.path.join(SUPERVISOR_LOG_FOLDER, id_str)

    # Home folder of the user
    CURRENT_USER_FOLDER: str = os.path.join(GENERAL_OUTPUT_FOLDER, args.author)

    # Folder for the current justification
    justification_name = (NOW + " " + str(args.naf) + " " + NAF_TO_NAME[args.naf] + " from " +
                          str(args.begin.strftime("%Y-%m")) + " to " +
                          str(args.end.strftime("%Y-%m")))
    CURRENT_JUSTIFICATION_FOLDER = os.path.join(CURRENT_USER_FOLDER, justification_name)

    USER_REPORT_FILE = os.path.join(CURRENT_JUSTIFICATION_FOLDER, NOW + "_" +
                                    args.naf.__str__()
                                    + "_" + NAF_TO_NAME[args.naf] + "_" +
                                    args.begin.strftime("%Y-%m") + "-" + args.end.strftime("%Y-%m") + ".log.txt")
    return CURRENT_USER_FOLDER, CURRENT_JUSTIFICATION_FOLDER, USER_REPORT_FILE, ADMIN_LOG_PATH, SUPERVISOR_LOG_PATH


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

