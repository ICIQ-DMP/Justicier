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

import pytest

from NIF import NIF, parse_nif, NIFType
from custom_except import ArgumentNafInvalid


class TestDNIParsing:
    def test_plain_dni(self):
        dni = NIF("12345678K")
        assert dni.number == "12345678"
        assert dni.letter == "K"
        assert dni.dni_type == NIFType.DNI

    def test_dni_with_dash(self):
        dni = NIF("12345678-K")
        assert dni.number == "12345678"
        assert dni.letter == "K"

    def test_nie_x(self):
        dni = NIF("X1234567T")
        assert dni.dni_type == NIFType.NIE
        assert dni.initial == "X"
        assert dni.number == "1234567"
        assert dni.letter == "T"

    def test_nie_with_dashes(self):
        dni = NIF("X-1234567-T")
        assert dni.dni_type == NIFType.NIE
        assert dni.initial == "X"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            NIF("not-a-dni")


class TestDNIEquality:
    def test_same_dni_equal(self):
        assert NIF("12345678K") == NIF("12345678-K")

    def test_different_dni_not_equal(self):
        assert NIF("12345678K") != NIF("12345678Z")

    def test_not_equal_to_non_dni(self):
        assert NIF("12345678K") != "12345678K"


class TestDNIFormatting:
    def test_str_dni(self):
        assert str(NIF("12345678K")) == "12345678-K"

    def test_str_nie(self):
        assert str(NIF("X1234567T")) == "X-1234567-T"

    def test_no_dash_str_dni(self):
        assert NIF("12345678K").no_dash_str() == "12345678K"

    def test_no_dash_str_nie(self):
        assert NIF("X1234567T").no_dash_str() == "X1234567T"


class TestParseDni:
    def test_valid_returns_dni(self):
        result = parse_nif("12345678K")
        assert isinstance(result, NIF)

    def test_invalid_raises_argument_naf_invalid(self):
        with pytest.raises(ArgumentNafInvalid):
            parse_nif("bad")
