import re
from enum import Enum

from custom_except import ArgumentNafInvalid


class DNIType(Enum):
    DNI = "DNI"
    NIE = "NIE"
    TEMPORAL_NIE = "temporal NIE"
    PASSPORT = "passport"


class DNI:
    def __init__(self, raw_dni: str):
        pattern = r"""
            ^(
                (?P<nie_initial>[XYZARxyzar])[-/]?
                (?P<nie_number>\d{7})[-/]?
                (?P<nie_letter>[A-Za-z])
            )|(
                (?P<dni_number>\d{8})[-/]?
                (?P<dni_letter>[A-Za-z])
            )|(
                (?P<nie_temporal_form1_letter>[A-Za-z])[-/]?
                (?P<nie_temporal_form1_number>\d{7})[-/]?
                (?P<nie_temporal_form1_letter_control>[A-Za-z])
            )|(
                (?P<nie_temporal_form2_letter>[A-Za-z])[-/]?
                (?P<nie_temporal_form2_letter_control>[A-Za-z])[-/]?
                (?P<nie_temporal_form2_number>\d{7})
            )$
        """

        match = re.match(pattern, raw_dni, re.VERBOSE)

        if not match:
            raise ValueError(
                f"Invalid DNI format: {raw_dni}. Must be DNI or NIE (e.g., 12345678-K or X-1234567-T)"
            )

        if match.group("dni_number") and match.group("dni_letter"):
            self.dni_type = DNIType.DNI
            self.number = match.group("dni_number")
            self.letter = match.group("dni_letter").upper()
        elif (
            match.group("nie_initial")
            and match.group("nie_number")
            and match.group("nie_number")
        ):
            self.dni_type = DNIType.NIE
            self.initial = match.group("nie_initial").upper()
            self.number = match.group("nie_number")
            self.letter = match.group("nie_letter").upper()
        elif (
            match.group("nie_temporal_form1_letter")
            and match.group("nie_temporal_form1_letter_control")
            and match.group("nie_temporal_form1_number")
        ):
            self.dni_type = DNIType.TEMPORAL_NIE
            self.initial = match.group("nie_temporal_form1_letter").upper()
            self.number = match.group("nie_temporal_form1_letter_control")
            self.letter = match.group("nie_temporal_form1_number").upper()
        elif (
            match.group("nie_temporal_form2_letter")
            and match.group("nie_temporal_form2_letter_control")
            and match.group("nie_temporal_form2_number")
        ):
            self.dni_type = DNIType.PASSPORT
            self.initial = match.group("nie_temporal_form2_letter").upper()
            self.number = match.group("nie_temporal_form2_letter_control")
            self.letter = match.group("nie_temporal_form2_number").upper()
        else:
            raise ValueError(f"DNI {raw_dni} could not be parsed")

    def __str__(self) -> str:
        if self.dni_type == DNIType.DNI:
            return f"{self.number}-{self.letter}"
        return f"{self.initial}-{self.number}-{self.letter}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DNI):
            return False
        if self.dni_type == DNIType.DNI:
            return self.number == other.number and self.letter == other.letter
        return (
            self.initial == other.initial
            and self.number == other.number
            and self.letter == other.letter
        )

    def __hash__(self) -> int:
        return hash(self.number)

    def no_dash_str(self) -> str:
        if self.dni_type == DNIType.DNI:
            return f"{self.number}{self.letter}"
        if self.dni_type in (DNIType.TEMPORAL_NIE, DNIType.PASSPORT):
            return f"{self.initial}{self.letter}{self.number}"
        return f"{self.initial}{self.number}{self.letter}"


def parse_dni(value: str) -> DNI:
    try:
        return DNI(value)
    except Exception as e:
        raise ArgumentNafInvalid(
            f"DNI {value} is not valid{e}"
        )  # TODO change exception
