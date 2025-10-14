import os
from enum import Enum

# Get absolute path to the root of the project
ROOT_FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The directory where the output folder for each user will be
GENERAL_OUTPUT_FOLDER: str = os.path.join(ROOT_FOLDER, "output")

# Admin logs
ADMIN_LOG_FOLDER = os.path.join(GENERAL_OUTPUT_FOLDER, "_admin_logs")
SUPERVISOR_LOG_FOLDER = os.path.join(GENERAL_OUTPUT_FOLDER, "_supervisor_logs")

SALARIES_OUTPUT_NAME = "Nòmines"
PROOFS_OUTPUT_NAME = "Justificants"
SALARIES_AND_PROOFS_OUTPUT_NAME = "Nòmines i Justificants"
CONTRACTS_OUTPUT_NAME = "Contractes"
RNTS_OUTPUT_NAME = "RNTs"
RLCS_OUTPUT_NAME = "RLCs"
RNTS_AND_RLCS_OUTPUT_NAME = "RNTs i RLCs"


class DocType(Enum):
    SALARY = "salary"
    CONTRACT = "contract"
    RLC = "RLC"
    RNT = "RNT"
    PROOFS = "proofs"
    SALARIES_AND_PROOFS = "salaries with proofs"


def from_string(value: str):
    _aliases = {
        DocType.SALARY: {"salary", "salaries", "SALARY", "Salary", "payslip"},
        DocType.CONTRACT: {"contract", "CONTRACT", "Contract", "agreement"},
        DocType.RLC: {"RLC", "rlc", "R.L.C."},
        DocType.RNT: {"RNT", "rnt", "R.N.T."},
        DocType.PROOFS: {"proof", "bankproof", "proofs", "bankproofs"}
    }
    for doctype in _aliases:
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



