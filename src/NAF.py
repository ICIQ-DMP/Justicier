import re

import pandas as pd

from DNI import parse_dni
from Name import parse_name_a3
from custom_except import ArgumentNafInvalid


class NAF:
    def __init__(self, raw_naf):
        pattern = r"(\d{2})([/\-]?)(\d{8})([/\-]?)(\d{2})"
        match = re.fullmatch(pattern, raw_naf)
        if not match:
            raise ValueError(f"Invalid NAF format: {raw_naf} NAF must be in NAF format. Example: 43/12345678-20")

        self.province_code = match.group(1)
        self.sep1 = match.group(2)
        self.middle_number = match.group(3)
        self.sep2 = match.group(4)
        self.last_number = match.group(5)

    def __str__(self):
        return f"{self.province_code}{self.middle_number}{self.last_number}"

    def __eq__(self, other):
        if not isinstance(other, NAF):
            return False
        return (
            self.province_code == other.province_code and
            self.middle_number == other.middle_number and
            self.last_number == other.last_number
        )

    def __hash__(self):
        return hash(self.province_code + self.middle_number + self.last_number)

    def slash_dash_str(self):
        return f"{self.province_code}/{self.middle_number}-{self.last_number}"


def is_naf_format_correct(naf):
    """Validate that NAF has NAF format"""
    try:
        NAF(naf)  # Parse using constructor
    except ValueError:
        return False
    return True


def is_naf_present(value, valid_nafs):
    return NAF(value) in valid_nafs


def clean_naf(naf):
    "Removes symbols that are not numbers in a SS number"
    return naf.replace("/", "").replace("-", "")


def parse_two_columns(df, key: int, value: int, func_apply_key=None, func_apply_value=None):
    # Column C = index 2 (DNI), Column D = index 3 (NAF)
    val_col = df[value]
    key_col = df[key]

    if func_apply_value is not None:
        val_col = val_col.apply(func_apply_value)
    if func_apply_key is not None:
        key_col = key_col.apply(func_apply_key)

    return dict(zip(key_col, val_col))


def read_dataframe(path, skiprows, header):
    # Read the Excel file, skipping the first 3 rows
    return pd.read_excel(path, skiprows=skiprows, header=header)


def build_naf_to_dni(path):
    df = read_dataframe(path, 3, None)
    return parse_two_columns(df, 3, 2, parse_naf, parse_dni)


def build_naf_to_name(path):
    df = read_dataframe(path, 3, None)
    return parse_two_columns(df, 3, 4, parse_naf, parse_name_a3)


def parse_naf(value):
    try:
        return NAF(value)
    except ValueError as e:
        raise ArgumentNafInvalid("NAF is not valid" + e.__str__())