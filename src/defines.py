import logging
import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

ROOT_FOLDER: Path = Path(__file__).resolve().parent.parent
PROJECT_DIR: Path = ROOT_FOLDER  # alias kept for compatibility

GENERAL_OUTPUT_FOLDER: Path = ROOT_FOLDER / "output"

ADMIN_LOG_FOLDER: Path = GENERAL_OUTPUT_FOLDER / "_admin_logs"
SUPERVISOR_LOG_FOLDER: Path = GENERAL_OUTPUT_FOLDER / "_supervisor_logs"

SALARIES_OUTPUT_NAME = "Nòmines"
PROOFS_OUTPUT_NAME = "Justificants"
SALARIES_AND_PROOFS_OUTPUT_NAME = "Nòmines i Justificants"
CONTRACTS_OUTPUT_NAME = "Contractes"
RNTS_OUTPUT_NAME = "RNTs"
RLCS_OUTPUT_NAME = "RLCs"
RNTS_AND_RLCS_OUTPUT_NAME = "RNTs i RLCs"

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
NOW_DATA = datetime.datetime.now()
NOW = NOW_DATA.strftime(DATETIME_FORMAT)

DATE_FORMAT = "%d/%m/%Y"


class DocType(Enum):
    SALARY = "salary"
    CONTRACT = "contract"
    RLC = "RLC"
    RNT = "RNT"
    PROOFS = "proofs"
    SALARIES_AND_PROOFS = "salaries with proofs"


def from_string(value: str) -> "DocType":
    _aliases = {
        DocType.SALARY: {"salary", "salaries", "SALARY", "Salary", "payslip"},
        DocType.CONTRACT: {"contract", "CONTRACT", "Contract", "agreement"},
        DocType.RLC: {"RLC", "rlc", "R.L.C."},
        DocType.RNT: {"RNT", "rnt", "R.N.T."},
        DocType.PROOFS: {"proof", "bankproof", "proofs", "bankproofs"},
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


class LogLevel(str, Enum):
    """
    Logical log levels for the CLI.

    Includes a custom TRACE (more verbose than DEBUG) and QUIET
    (suppresses all output beyond CRITICAL).
    """

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    QUIET = "quiet"

    @classmethod
    def parse(cls, value: Optional[str]) -> Optional["LogLevel"]:
        """Parse case-insensitively; returns None if value is falsy."""
        print("Executing function parse from LogLevel")
        if not value:
            return None
        norm = value.strip().lower()
        try:
            return cls(norm)
        except ValueError as exc:
            valid = ", ".join(v.value for v in cls)
            raise ValueError(f"Unknown log level '{value}'. Valid: {valid}") from exc

    @classmethod
    def get_default_log_level(cls) -> "LogLevel":
        return LogLevel.TRACE

    def to_logging_level(self) -> int:
        if self is LogLevel.TRACE:
            return 0
        if self is LogLevel.DEBUG:
            return logging.DEBUG
        if self is LogLevel.INFO:
            return logging.INFO
        if self is LogLevel.WARNING:
            return logging.WARNING
        if self is LogLevel.ERROR:
            return logging.ERROR
        if self is LogLevel.QUIET:
            return logging.CRITICAL + 10
        return LogLevel.get_default_log_level().to_logging_level()


def get_default_log_path() -> Path:
    return ADMIN_LOG_FOLDER / (NOW + ".log")


def get_supervisor_log_path() -> Path:
    return get_default_log_path()


def get_user_log_path() -> Path:
    return get_default_log_path()
