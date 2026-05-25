import re
from pathlib import Path
from typing import Callable, Iterable, TypeVar

import pandas as pd

from DNI import DNI, parse_dni


from Name import Name, parse_name_a3, parse_email_a3
from custom_except import ArgumentNafInvalid
from defines import NAFFileColumn
from logger import get_logger

log = get_logger(__name__)


class NAF:
    def __init__(self, raw_naf: str) -> None:
        # For some random reason, a whitespace appear between province code and middle number...
        pattern = r"(\d{2})([/\-]?)(\d{8})([/\-]?)(\d{2})"
        match = re.fullmatch(pattern, str(raw_naf))

        if not match:
            raise ValueError(
                f"Invalid NAF format: {str(raw_naf)} NAF must be in NAF format. Example: 43/12345678-20"
            )

        self.province_code = match.group(1)
        self.sep1 = match.group(2)
        self.middle_number = match.group(3)
        self.sep2 = match.group(4)
        self.last_number = match.group(5)

    def __str__(self) -> str:
        return f"{self.province_code}{self.middle_number}{self.last_number}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NAF):
            return False
        return (
            self.province_code == other.province_code
            and self.middle_number == other.middle_number
            and self.last_number == other.last_number
        )

    def __hash__(self) -> int:
        return hash(self.province_code + self.middle_number + self.last_number)

    def slash_dash_str(self) -> str:
        return f"{self.province_code}/{self.middle_number}-{self.last_number}"


def is_naf_format_correct(naf: str) -> bool:
    """Validate that NAF has NAF format"""
    try:
        NAF(naf)  # Parse using constructor
    except ValueError:
        return False
    return True


def is_naf_present(value: NAF, valid_nafs: Iterable[NAF]) -> bool:
    return value in valid_nafs


def clean_naf(naf: str) -> str:
    """Removes symbols that are not numbers in a SS number"""
    return naf.replace("/", "").replace("-", "")


_K = TypeVar("_K")
_V = TypeVar("_V")


def parse_two_columns(
    df: pd.DataFrame,
    key: str,
    value: str,
    func_apply_key: Callable[[str], _K] | None = None,
    func_apply_value: Callable[[str], _V] | None = None,
) -> dict[_K, _V]:
    val_col = df[value]
    key_col = df[key]
    try:
        if func_apply_value is not None:
            val_col = val_col.apply(func_apply_value)
    except Exception as e:
        log.error("func apply value failed with exception: " + str(e))
    try:
        if func_apply_key is not None:
            key_col = key_col.apply(func_apply_key)
    except Exception as e:
        log.error("func apply key failed with exception:  " + str(e))

    return dict(zip(key_col, val_col))


def read_dataframe(path: Path, skiprows: int, header: int | None) -> pd.DataFrame:
    # Read the Excel file, skipping the first 3 rows.
    # Column C (index 2) contains NAF/NASS ids which may start with 0 — force str
    # to prevent pandas from parsing them as int and dropping the leading zero.
    return pd.read_excel(
        path, skiprows=skiprows, header=header, dtype={NAFFileColumn.NASS: str}
    )


def build_naf_to_dni(path: Path) -> dict[NAF, DNI]:
    df = read_dataframe(path, 0, 0)
    return parse_two_columns(
        df, NAFFileColumn.NASS, NAFFileColumn.NIF, parse_naf, parse_dni
    )


def build_naf_to_name(path: Path) -> dict[NAF, Name]:
    df = read_dataframe(path, 0, 0)
    return parse_two_columns(
        df, NAFFileColumn.NASS, NAFFileColumn.NAME, parse_naf, parse_name_a3
    )


def build_naf_to_email(path: Path) -> dict[NAF, str]:
    df = read_dataframe(path, 0, 0)
    return parse_two_columns(
        df, NAFFileColumn.NASS, NAFFileColumn.EMAIL, parse_naf, parse_email_a3
    )


def parse_naf(value: str) -> NAF:
    try:
        log.trace(f"Parsing NAF: {value}")
        return NAF(value)
    except Exception as e:
        raise ArgumentNafInvalid("NAF is not valid" + e.__str__())
