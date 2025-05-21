import os
from enum import Enum

# Get absolute path to the root of the project
ROOT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The directory where the output folder for each user will be
GENERAL_OUTPUT_FOLDER: str = os.path.join(ROOT_FOLDER, "output")

# Obtain absolute path to the input directory
INPUT_FOLDER = os.path.join(ROOT_FOLDER, "input")

# Admin logs
ADMIN_LOG_FOLDER = os.path.join(GENERAL_OUTPUT_FOLDER, "_admin_logs")
SUPERVISOR_LOG_FOLDER = os.path.join(GENERAL_OUTPUT_FOLDER, "_supervisor_logs")

# Obtain absolute paths for each input directory
SALARIES_FOLDER = os.path.join(INPUT_FOLDER, "_salaries")
PROOFS_FOLDER = os.path.join(INPUT_FOLDER, "_proofs")
CONTRACTS_FOLDER = os.path.join(INPUT_FOLDER, "_contracts")
RNTS_FOLDER = os.path.join(INPUT_FOLDER, "_RNT")
RLCS_FOLDER = os.path.join(INPUT_FOLDER, "_RLC")

SALARIES_OUTPUT_NAME = "Nòmines"
PROOFS_OUTPUT_NAME = "Justificants"
CONTRACTS_OUTPUT_NAME = "Contractes"
RNTS_OUTPUT_NAME = "RNTs"
RLCS_OUTPUT_NAME = "RLCs"

NAF_DATA_PATH = os.path.join(INPUT_FOLDER, "NAF_DNI.xlsx")


class DocType(Enum):
    SALARY = "salary"
    CONTRACT = "contract"
    RLC = "RLC"
    RNT = "RNT"
    PROOFS = "proofs"


def from_string(value: str):
    _aliases = {
        DocType.SALARY: {"salary", "salaries", "SALARY", "Salary", "payslip"},
        DocType.CONTRACT: {"contract", "CONTRACT", "Contract", "agreement"},
        DocType.RLC: {"RLC", "rlc", "R.L.C."},
        DocType.RNT: {"RNT", "rnt", "R.N.T."},
    }
    for doctype in _aliases:
        print("value is " + value.__str__())

        if value.strip() in _aliases[doctype]:
            return doctype
    raise ValueError(f"Unknown document type: {value}")


class RLCType(Enum):
    REGULAR = "regular"
    DELAY = "delay"
    SETTLEMENT = "settlement"


class SalaryType(Enum):
    REGULAR = "Nomines"
    DELAY = "Atrasos"
    EXTRA = "Extres"


class RegularSalaryType(Enum):
    SETTLEMENT = "Settlement"
    MONTHLY = "Monthly"


