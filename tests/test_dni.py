# Copyright (C) AleixMT
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from DNI import DNI, parse_dni, DNIType
from custom_except import ArgumentNafInvalid


class TestDNIParsing:
    def test_plain_dni(self):
        dni = DNI("12345678K")
        assert dni.number == "12345678"
        assert dni.letter == "K"
        assert dni.dni_type == DNIType.DNI

    def test_dni_with_dash(self):
        dni = DNI("12345678-K")
        assert dni.number == "12345678"
        assert dni.letter == "K"

    def test_nie_x(self):
        dni = DNI("X1234567T")
        assert dni.dni_type == DNIType.NIE
        assert dni.initial == "X"
        assert dni.number == "1234567"
        assert dni.letter == "T"

    def test_nie_with_dashes(self):
        dni = DNI("X-1234567-T")
        assert dni.dni_type == DNIType.NIE
        assert dni.initial == "X"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            DNI("not-a-dni")


class TestDNIEquality:
    def test_same_dni_equal(self):
        assert DNI("12345678K") == DNI("12345678-K")

    def test_different_dni_not_equal(self):
        assert DNI("12345678K") != DNI("12345678Z")

    def test_not_equal_to_non_dni(self):
        assert DNI("12345678K") != "12345678K"


class TestDNIFormatting:
    def test_str_dni(self):
        assert str(DNI("12345678K")) == "12345678-K"

    def test_str_nie(self):
        assert str(DNI("X1234567T")) == "X-1234567-T"

    def test_no_dash_str_dni(self):
        assert DNI("12345678K").no_dash_str() == "12345678K"

    def test_no_dash_str_nie(self):
        assert DNI("X1234567T").no_dash_str() == "X1234567T"


class TestParseDni:
    def test_valid_returns_dni(self):
        result = parse_dni("12345678K")
        assert isinstance(result, DNI)

    def test_invalid_raises_argument_naf_invalid(self):
        with pytest.raises(ArgumentNafInvalid):
            parse_dni("bad")
