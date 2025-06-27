import re

import pandas as pd

from defines import NAF_DATA_PATH
from custom_except import ArgumentNafInvalid, ArgumentNafNotPresent


class DNI:
    def __init__(self, raw_dni):
        pattern = r"""
            ^(
                (?P<nie_initial>[XYZARxyzar])[-/]?
                (?P<nie_number>\d{7})[-/]?
                (?P<nie_letter>[A-Za-z])
            )|(
                (?P<dni_number>\d{8})[-/]?
                (?P<dni_letter>[A-Za-z])
            )$
        """

        match = re.match(pattern, raw_dni, re.VERBOSE)

        if not match:
            raise ValueError(f"Invalid DNI format: {raw_dni}. Must be DNI or NIE (e.g., 12345678-K or X-1234567-T)")

        if match.group("dni_number"):
            self.is_nie = False
            self.number = match.group("dni_number")
            self.letter = match.group("dni_letter").upper()
        else:
            self.is_nie = True
            self.initial = match.group("nie_initial").upper()
            self.number = match.group("nie_number")
            self.letter = match.group("nie_letter").upper()

    def __str__(self):
        if self.is_nie:
            return f"{self.initial}-{self.number}-{self.letter}"
        else:
            return f"{self.number}-{self.letter}"

    def __eq__(self, other):
        if not isinstance(other, DNI):
            return False
        if self.is_nie:
            return (
                    self.initial == other.initial and self.number == other.number and self.letter == other.letter
            )
        else:
            return (
                    self.number == other.number and self.letter == other.letter
            )

    def __hash__(self):
        return hash(self.number)

    def no_dash_str(self):
        if self.is_nie:
            return f"{self.initial}{self.number}{self.letter}"
        else:
            return f"{self.number}{self.letter}"


def parse_dni(value):
    try:
        return DNI(value)
    except ValueError as e:
        raise ArgumentNafInvalid("DNI is not valid" + e.__str__())  # TODO change exception