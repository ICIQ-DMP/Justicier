import os


def list_dir(input_folder):
    """Returns a list of all file names in the ./input/salaries directory."""
    # Ensure the input_folder is a valid directory
    if not os.path.isdir(input_folder):
        raise ValueError("input folder in list_files function is not a directory or can't be accessed" + input_folder)

    # List all files in the directory
    file_names = [os.path.basename(file) for file in os.listdir(input_folder)]

    return file_names
