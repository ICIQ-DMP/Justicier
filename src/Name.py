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

"""Employee name parsing and representation."""

from custom_except import ArgumentNafInvalid


class Name:
    """Represents an employee's first name and surname."""

    def __init__(self, name: str, surname: str) -> None:
        """Initialise a Name from its components.

        Args:
            name: First (given) name of the employee.
            surname: Surname (family name) of the employee.
        """
        self.name = name
        self.surname = surname

    def __str__(self) -> str:
        """Return the full name as ``<name> <surname>``."""
        return f"{self.name} {self.surname}"

    def __eq__(self, other: object) -> bool:
        """Check equality by comparing both name and surname."""
        if not isinstance(other, Name):
            return False
        return self.name == other.name and self.surname == other.surname

    def __hash__(self) -> int:
        """Return a hash derived from the concatenated full name."""
        return hash(self.name + self.surname)


def parse_name_a3(value: str) -> Name:
    """Parse an A3 payroll name string (``SURNAME, NAME``) into a Name.

    Args:
        value: Raw name string in A3 format, e.g. ``"GARCIA LOPEZ, MARIA"``.

    Returns:
        Parsed Name instance.

    Raises:
        ArgumentNafInvalid: If *value* cannot be parsed into a Name.
    """
    # Coupled with NAF_DNI.xlsx format
    parts = value.split(",")
    name = parts[1].strip(" ")
    if " " in name:
        name = name.split(" ")[0]
    surname = parts[0]
    if " " in surname:
        surname = surname.split(" ")[0]
    try:
        return Name(name, surname)
    except ValueError as e:
        raise ArgumentNafInvalid(f"Name is not valid{e}")  # TODO: change exceptions


def parse_email_a3(value: str) -> str:
    """Return *value* normalised to lowercase for use as an email address."""
    return value.lower()


def parse_name_sharepoint(value: str) -> Name:
    """Parse a SharePoint display name into a Name, stripping accents and uppercasing.

    Args:
        value: Raw display name from SharePoint, e.g. ``"María García"``.

    Returns:
        Parsed Name instance with ASCII-normalised, uppercased components.

    Raises:
        ArgumentNafInvalid: If *value* cannot be parsed into a Name.
    """
    value = value.replace("à", "a")
    value = value.replace("â", "a")
    value = value.replace("á", "a")
    value = value.replace("è", "e")
    value = value.replace("ê", "e")
    value = value.replace("é", "e")
    value = value.replace("ì", "i")
    value = value.replace("î", "i")
    value = value.replace("í", "i")
    value = value.replace("ò", "o")
    value = value.replace("ô", "o")
    value = value.replace("ó", "o")
    value = value.replace("ù", "u")
    value = value.replace("û", "u")
    value = value.replace("ú", "u")
    value = value.upper()
    name = value.split(" ")[0]
    surname = " ".join(value.split(" ")[1:])

    # Coupled with Sharepoint name format
    try:
        return Name(name, surname)
    except ValueError as e:
        raise ArgumentNafInvalid(f"Name is not valid{e}")  # TODO: change exceptions
