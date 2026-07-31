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

"""NAF (Social Security number) parsing, validation and lookup utilities."""

import re
from pathlib import Path
from typing import Callable, Iterable, TypeVar

import pandas as pd

from .nif import NIF, parse_nif


from .name import Name, parse_name_a3, parse_email_a3
from .custom_except import ArgumentNafInvalidError
from .defines import NAFFileColumn
from .logger import get_logger

log = get_logger(__name__)


class NAF:
    """Represents a parsed Spanish Social Security number (NAF/NASS)."""

    def __init__(self, raw_naf: str) -> None:
        """Parse and validate a raw NAF string.

        Args:
            raw_naf: Raw NAF string in any supported format (e.g. ``43/12345678-20``).

        Raises:
            ValueError: If *raw_naf* does not match the expected NAF pattern.
        """
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
        """Return the compact NAF string with no separators."""
        return f"{self.province_code}{self.middle_number}{self.last_number}"

    def __eq__(self, other: object) -> bool:
        """Check equality by comparing province code, middle number and last number."""
        if not isinstance(other, NAF):
            return False
        return (
            self.province_code == other.province_code
            and self.middle_number == other.middle_number
            and self.last_number == other.last_number
        )

    def __hash__(self) -> int:
        """Return a hash based on the canonical NAF digits."""
        return hash(self.province_code + self.middle_number + self.last_number)

    def slash_dash_str(self) -> str:
        """Return the NAF formatted as ``PP/NNNNNNNN-LL``."""
        return f"{self.province_code}/{self.middle_number}-{self.last_number}"


def is_naf_format_correct(naf: str) -> bool:
    """Return True if *naf* can be parsed as a valid NAF string."""
    try:
        NAF(naf)  # Parse using constructor
    except ValueError:
        return False
    return True


def is_naf_present(value: NAF, valid_nafs: Iterable[NAF]) -> bool:
    """Return True if *value* is contained in *valid_nafs*."""
    return value in valid_nafs


def clean_naf(naf: str) -> str:
    """Return *naf* with all ``/`` and ``-`` separators removed."""
    return naf.replace("/", "").replace("-", "")


_K = TypeVar("_K")
_V = TypeVar("_V")


def parse_columns(
    df: pd.DataFrame,
    key: str,
    value: list[str],
    func_apply_key: Callable[[str], _K],
    func_apply_value: Callable[[str], _V],
) -> dict[_K, list[_V]]:
    """Build a typed dictionary by applying transform functions to two DataFrame columns.

    Args:
        df: Source DataFrame.
        key: Column name whose values become dictionary keys.
        value: Column name whose values become dictionary values.
        func_apply_key: Callable that converts each raw key string to type ``_K``.
        func_apply_value: Callable that converts each raw value string to type ``_V``.

    Returns:
        A dict mapping transformed keys to transformed values.

    Raises:
        Exception: Re-raises any exception from the transform callables after logging it.
    """
    try:
        keys: list[_K] = [func_apply_key(k) for k in df[key]]
    except Exception as e:
        log.error(f"func apply key failed with exception:  {e}")
        raise
    try:
        values: list[list[_V]] = [
            [func_apply_value(v) for v in row if not pd.isna(v)]
            for row in zip(*(df[col] for col in value))
        ]
    except Exception as e:
        log.error(f"func apply value failed with exception: {e}")
        raise
    return dict(zip(keys, values))


def read_dataframe(path: Path, skiprows: int, header: int | None) -> pd.DataFrame:
    """Read an Excel file into a DataFrame, forcing the NASS column to string type.

    Args:
        path: Path to the Excel file.
        skiprows: Number of leading rows to skip.
        header: Row index to use as column names, or ``None`` for no header.

    Returns:
        The parsed DataFrame with the NASS column read as strings.
    """
    # Read the Excel file, skipping the first 3 rows.
    # Column C (index 2) contains NAF/NASS ids which may start with 0 — force str
    # to prevent pandas from parsing them as int and dropping the leading zero.
    return pd.read_excel(
        path, skiprows=skiprows, header=header, dtype={NAFFileColumn.NASS: str}
    )


def build_naf_to_dni(path: Path) -> dict[NAF, list[NIF]]:
    """Build a NAF → NIF mapping from the employee Excel file.

    Args:
        path: Path to the NAF/DNI Excel file.

    Returns:
        Dictionary mapping each NAF to its corresponding NIF.
    """
    df = read_dataframe(path, 0, 0)
    return parse_columns(
        df,
        NAFFileColumn.NASS,
        [
            NAFFileColumn.NIF_CURRENT,
            NAFFileColumn.NIF_PREVIOUS,
            NAFFileColumn.NIF_BEFORE_PREVIOUS,
        ],
        parse_naf,
        parse_nif,
    )


def flatten_dict_list(d: dict[_K, list[_V]]) -> dict[_K, _V]:
    """Return a new dict mapping each key to the first element of its value list.

    Args:
        d: Source dictionary mapping keys to lists of values.

    Returns:
        Dictionary mapping each key to the first item of its original list.
    """
    return {key: values[0] for key, values in d.items()}


def build_naf_to_name(path: Path) -> dict[NAF, Name]:
    """Build a NAF → Name mapping from the employee Excel file.

    Args:
        path: Path to the NAF/name Excel file.

    Returns:
        Dictionary mapping each NAF to its corresponding Name.
    """
    df = read_dataframe(path, 0, 0)
    return flatten_dict_list(
        parse_columns(
            df, NAFFileColumn.NASS, [NAFFileColumn.NAME], parse_naf, parse_name_a3
        )
    )


def build_naf_to_email(path: Path) -> dict[NAF, str]:
    """Build a NAF → email mapping from the employee Excel file.

    Args:
        path: Path to the NAF/email Excel file.

    Returns:
        Dictionary mapping each NAF to its corresponding email address.
    """
    df = read_dataframe(path, 0, 0)
    return flatten_dict_list(
        parse_columns(
            df, NAFFileColumn.NASS, [NAFFileColumn.EMAIL], parse_naf, parse_email_a3
        )
    )


def parse_naf(value: str) -> NAF:
    """Parse a raw string into a NAF, raising a domain exception on failure.

    Args:
        value: Raw NAF string to parse.

    Returns:
        Parsed NAF instance.

    Raises:
        ArgumentNafInvalidError: If *value* is not a valid NAF.
    """
    try:
        log.trace(f"Parsing NAF: {value}")
        return NAF(value)
    except Exception as e:
        raise ArgumentNafInvalidError(f"NAF is not valid{e}")
