import re

import pandas as pd

from defines import NAF_DATA_PATH
from custom_except import ArgumentNafInvalid, ArgumentNafNotPresent


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


def build_naf_to_dni(path):
    # Read the Excel file, skipping the first 3 rows
    df = pd.read_excel(path, skiprows=3, header=None)

    # Column C = index 2 (DNI), Column D = index 3 (NAF)
    dni_col = df[2]
    naf_col = df[3]

    # Replace the 11th character in each NAF
    def parse_naf(naf):
        return NAF(naf)

    naf_fixed = naf_col.apply(parse_naf)

    return dict(zip(naf_fixed, dni_col))


def build_naf_to_name_and_surname(path):
    # Read the Excel file, skipping the first 3 rows
    df = pd.read_excel(path, skiprows=3, header=None)

    # Column C = index 2 (DNI), Column D = index 3 (NAF)
    name_col = df[1]
    naf_col = df[3]

    # Replace the 11th character in each NAF
    def parse_naf(naf):
        return NAF(naf)

    naf_fixed = naf_col.apply(parse_naf)

    return dict(zip(naf_fixed, name_col))



