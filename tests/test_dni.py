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

"""Tests for NIF/DNI parsing, equality, and formatting."""

import pytest

from justicier.nif import NIF, parse_nif, NIFType
from justicier.custom_except import ArgumentNafInvalidError


class TestDNIParsing:
    """Tests for NIF constructor parsing of various identifier formats."""

    def test_plain_dni(self):
        """A plain 8-digit + letter DNI should parse correctly."""
        dni = NIF("12345678K")
        assert dni.number == "12345678"
        assert dni.letter == "K"
        assert dni.dni_type == NIFType.DNI

    def test_dni_with_dash(self):
        """A DNI with a dash separator should parse correctly."""
        dni = NIF("12345678-K")
        assert dni.number == "12345678"
        assert dni.letter == "K"

    def test_nie_x(self):
        """An NIE starting with X should be parsed as NIE type."""
        dni = NIF("X1234567T")
        assert dni.dni_type == NIFType.NIE
        assert dni.initial == "X"
        assert dni.number == "1234567"
        assert dni.letter == "T"

    def test_nie_with_dashes(self):
        """An NIE with dashes should be parsed as NIE type."""
        dni = NIF("X-1234567-T")
        assert dni.dni_type == NIFType.NIE
        assert dni.initial == "X"

    def test_invalid_format_raises(self):
        """An unrecognised string should raise ValueError."""
        with pytest.raises(ValueError):
            NIF("not-a-dni")


class TestDNIEquality:
    """Tests for NIF equality comparison."""

    def test_same_dni_equal(self):
        """The same DNI with and without dashes should be equal."""
        assert NIF("12345678K") == NIF("12345678-K")

    def test_different_dni_not_equal(self):
        """Two DNIs with different check letters should not be equal."""
        assert NIF("12345678K") != NIF("12345678Z")

    def test_not_equal_to_non_dni(self):
        """A NIF should not be equal to a plain string."""
        assert NIF("12345678K") != "12345678K"


class TestDNIFormatting:
    """Tests for NIF string formatting methods."""

    def test_str_dni(self):
        """str() on a DNI should return the number-dash-letter format."""
        assert str(NIF("12345678K")) == "12345678-K"

    def test_str_nie(self):
        """str() on an NIE should return initial-number-letter with dashes."""
        assert str(NIF("X1234567T")) == "X-1234567-T"

    def test_no_dash_str_dni(self):
        """no_dash_str() on a DNI should return digits and letter with no separators."""
        assert NIF("12345678K").no_dash_str() == "12345678K"

    def test_no_dash_str_nie(self):
        """no_dash_str() on an NIE should return all components with no separators."""
        assert NIF("X1234567T").no_dash_str() == "X1234567T"


class TestParseDni:
    """Tests for the parse_nif domain-exception wrapper."""

    def test_valid_returns_dni(self):
        """A valid string should return a NIF instance."""
        result = parse_nif("12345678K")
        assert isinstance(result, NIF)

    def test_invalid_raises_argument_naf_invalid(self):
        """An invalid string should raise ArgumentNafInvalidError."""
        with pytest.raises(ArgumentNafInvalidError):
            parse_nif("bad")
