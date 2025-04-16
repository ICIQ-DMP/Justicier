import os

# Get absolute path to the root of the project
ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Obtain absolute path to the input directory
INPUT_PATH = os.path.join(ROOT_PATH, "input")

# Obtain absolute paths for each input directory
SALARIES_PATH = os.path.join(INPUT_PATH, "_salaries")
PROOFS_PATH = os.path.join(INPUT_PATH, "_proofs")
CONTRACTS_PATH = os.path.join(INPUT_PATH, "_contracts")
RNTS_PATH = os.path.join(INPUT_PATH, "_RNT")
RLCS_PATH = os.path.join(INPUT_PATH, "_RLC")

SALARIES_OUTPUT_NAME = "Nòmines"
PROOFS_OUTPUT_NAME = "Justificants"
CONTRACTS_OUTPUT_NAME = "Contractes"
RNTS_OUTPUT_NAME = "RNTs"
RLCS_OUTPUT_NAME = "RLCs"

NAF_TO_DNI_PATH = os.path.join(INPUT_PATH, "NAF_DNI.xlsx")

