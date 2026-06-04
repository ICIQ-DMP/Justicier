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

"""NIF (Spanish tax identification number) parsing and representation."""

import re
from enum import Enum

from custom_except import ArgumentNafInvalid


class NIFType(Enum):
    """Enumeration of the supported Spanish personal identifier types."""

    DNI = "DNI"
    NIE = "NIE"
    TEMPORAL_NIE = "temporal NIE"
    PASSPORT = "passport"


class NIF:
    """Parsed Spanish personal identifier (DNI, NIE, or passport)."""

    def __init__(self, raw_dni: str) -> None:
        """Parse and validate a raw NIF/DNI string.

        Args:
            raw_dni: Raw identifier string in any supported format.

        Raises:
            ValueError: If *raw_dni* does not match any known identifier format.
        """
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
            self.dni_type = NIFType.DNI
            self.number = match.group("dni_number")
            self.letter = match.group("dni_letter").upper()
        elif (
            match.group("nie_initial")
            and match.group("nie_number")
            and match.group("nie_number")
        ):
            self.dni_type = NIFType.NIE
            self.initial = match.group("nie_initial").upper()
            self.number = match.group("nie_number")
            self.letter = match.group("nie_letter").upper()
        elif (
            match.group("nie_temporal_form1_letter")
            and match.group("nie_temporal_form1_letter_control")
            and match.group("nie_temporal_form1_number")
        ):
            self.dni_type = NIFType.TEMPORAL_NIE
            self.initial = match.group("nie_temporal_form1_letter").upper()
            self.number = match.group("nie_temporal_form1_letter_control")
            self.letter = match.group("nie_temporal_form1_number").upper()
        elif (
            match.group("nie_temporal_form2_letter")
            and match.group("nie_temporal_form2_letter_control")
            and match.group("nie_temporal_form2_number")
        ):
            self.dni_type = NIFType.PASSPORT
            self.initial = match.group("nie_temporal_form2_letter").upper()
            self.number = match.group("nie_temporal_form2_letter_control")
            self.letter = match.group("nie_temporal_form2_number").upper()
        else:
            raise ValueError(f"DNI {raw_dni} could not be parsed")

    def __str__(self) -> str:
        """Return the canonical dash-separated identifier string."""
        if self.dni_type == NIFType.DNI:
            return f"{self.number}-{self.letter}"
        return f"{self.initial}-{self.number}-{self.letter}"

    def __eq__(self, other: object) -> bool:
        """Check equality against another NIF by comparing its numeric components."""
        if not isinstance(other, NIF):
            return False
        if self.dni_type == NIFType.DNI:
            return self.number == other.number and self.letter == other.letter
        return (
            self.initial == other.initial
            and self.number == other.number
            and self.letter == other.letter
        )

    def __hash__(self) -> int:
        """Return a hash derived from the identifier number."""
        return hash(self.number)

    def no_dash_str(self) -> str:
        """Return the identifier as a single string with no dashes or separators."""
        if self.dni_type == NIFType.DNI:
            return f"{self.number}{self.letter}"
        if self.dni_type in (NIFType.TEMPORAL_NIE, NIFType.PASSPORT):
            return f"{self.initial}{self.letter}{self.number}"
        return f"{self.initial}{self.number}{self.letter}"


def parse_nif(value: str) -> NIF:
    """Parse a raw string into a NIF, raising a domain exception on failure.

    Args:
        value: Raw identifier string to parse.

    Returns:
        Parsed NIF instance.

    Raises:
        ArgumentNafInvalid: If *value* is not a valid NIF/DNI.
    """
    try:
        return NIF(value)
    except Exception as e:
        raise ArgumentNafInvalid(
            f"DNI {value} is not valid{e}"
        )  # TODO change exception
