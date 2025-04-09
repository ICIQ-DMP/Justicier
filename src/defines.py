import os

# Get absolute path to the root of the project
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Obtain absolute path to the input directory
INPUT_PATH = os.path.join(ROOT_PATH, "input")

# Obtain absolute paths for each input directory
SALARIES_PATH = os.path.join(INPUT_PATH, "_salaries")
PROOFS_PATH = os.path.join(INPUT_PATH, "_proofs")
CONTRACTS_PATH = os.path.join(INPUT_PATH, "_contracts")


