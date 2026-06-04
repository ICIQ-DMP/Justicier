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

"""Project-wide constants, enumerations, and path helpers."""

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


class InputElementsNames(str, Enum):
    """Input folder names."""

    SALARIES = "_salaries"
    BANKPROOFS = "_proofs"
    CONTRACTS = "_contracts"
    RNTS = "_RNT"
    RLCS = "_RLC"
    NAF_DNI = "NAF_DNI.xlsx"


class NAFFileColumn(str, Enum):
    """Column header names in the NAF/DNI Excel file."""

    NAME = "Nombre Completo"
    NASS = "NASS"
    NIF = "NIF"
    EMAIL = "E-mail profesional"


class SharepointListFieldWorkflowState(Enum):
    """Maps semantic Python names to the SharePoint field values SharepointListFields.WORKFLOW_STATE.

    Only values used in the algorithm are included, even though there are more.
    """

    IN_EXECUTION = "En execució"
    COMPLETED = "Completat"
    ERROR = "Error"


class SharepointListFields(Enum):
    """Maps semantic Python names to the internal SharePoint field names used by the Graph API."""

    ID = "id"
    REQUEST_TITLE = "Title"
    NAF = "NAF"
    TARGET_NAME = "Nomdelapersona"
    TARGET_EMAIL = "PersonaEmail"
    NIF = "DNI"
    BEGIN = "DataInici"
    END = "Datafinal"
    AUTHOR_NAME = "Sol_x00b7_licitant"
    AUTHOR_EMAIL = "SolicitantEmail"
    MERGE_SALARY_BANKPROOF = "Fusi_x00f3_NominaiJustificantBan"
    MERGE_RESULTS = "juntarpdfs"
    MERGE_RLC_RNT = "Fusi_x00f3_RLCRNT"
    WORKFLOW_STATE = "Estatworkflow"
    RESULT = "Resultat"
    ERROR_MESSAGE = "Missatge_x0020_error"


class DocType(Enum):
    """Document categories produced by the justification process."""

    SALARY = "salary"
    CONTRACT = "contract"
    RLC = "RLC"
    RNT = "RNT"
    PROOFS = "proofs"
    SALARIES_AND_PROOFS = "salaries with proofs"


def from_string(value: str) -> "DocType":
    """Return the DocType matching *value*, accepting common aliases.

    Args:
        value: Human-readable document type string (e.g. ``"salary"``, ``"RLC"``).

    Returns:
        The matching DocType member.

    Raises:
        ValueError: If *value* does not match any known type or alias.
    """
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
    """Sub-types of RLC (payroll tax settlement) documents."""

    REGULAR = "regular"
    DELAY = "delay"
    SETTLEMENT = "settlement"


class SalaryType(Enum):
    """Salary file types as encoded in their filenames."""

    REGULAR = "Nomines"
    DELAY = "Atrasos"
    EXTRA = "Extres"


class RegularSalaryType(Enum):
    """Sub-types of regular salary slips."""

    SETTLEMENT = "Settlement"
    MONTHLY = "Monthly"


class LogLevel(str, Enum):
    """Logical log levels for the CLI.

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
        """Return the default LogLevel used when no level is explicitly configured."""
        return LogLevel.TRACE

    def to_logging_level(self) -> int:
        """Convert this LogLevel to the corresponding ``logging`` module integer."""
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
    """Return the default admin log file path for the current run."""
    return ADMIN_LOG_FOLDER / (NOW + ".log")


def get_supervisor_log_path() -> Path:
    """Return the supervisor log file path for the current run."""
    return get_default_log_path()


def get_user_log_path() -> Path:
    """Return the user-facing log file path for the current run."""
    return get_default_log_path()
