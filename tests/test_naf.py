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

"""Tests for NAF parsing, equality, formatting, and helper functions."""

import pytest

from justicier.naf import NAF, is_naf_format_correct, parse_naf
from justicier.custom_except import ArgumentNafInvalidError


class TestNAFParsing:
    """Tests for the NAF constructor with various input formats."""

    def test_plain_digits(self):
        """A 12-digit NAF string should be split into its three components."""
        naf = NAF("431234567820")
        assert naf.province_code == "43"
        assert naf.middle_number == "12345678"
        assert naf.last_number == "20"

    def test_slash_dash_format(self):
        """NAF in PP/NNNNNNNN-LL format should parse to the same components."""
        naf = NAF("43/12345678-20")
        assert naf.province_code == "43"
        assert naf.middle_number == "12345678"
        assert naf.last_number == "20"

    def test_invalid_format_raises(self):
        """A non-NAF string should raise ValueError."""
        with pytest.raises(ValueError):
            NAF("not-a-naf")

    def test_too_short_raises(self):
        """A string that is too short should raise ValueError."""
        with pytest.raises(ValueError):
            NAF("4312345678")  # missing last two digits


class TestNAFEquality:
    """Tests for NAF equality and hashing."""

    def test_equal_regardless_of_separator(self):
        """NAFs with and without separators should be equal."""
        assert NAF("43/12345678-20") == NAF("431234567820")

    def test_different_nafs_not_equal(self):
        """NAFs with different last numbers should not be equal."""
        assert NAF("431234567820") != NAF("431234567821")

    def test_hash_equal_for_same_naf(self):
        """Equivalent NAFs should produce the same hash."""
        assert hash(NAF("431234567820")) == hash(NAF("43/12345678-20"))


class TestNAFFormatting:
    """Tests for NAF string output methods."""

    def test_str_strips_separators(self):
        """str() should return the compact 12-digit representation."""
        assert str(NAF("43/12345678-20")) == "431234567820"

    def test_slash_dash_str(self):
        """slash_dash_str() should return the PP/NNNNNNNN-LL format."""
        assert NAF("431234567820").slash_dash_str() == "43/12345678-20"


class TestNAFHelpers:
    """Tests for NAF helper/utility functions."""

    def test_is_naf_format_correct_valid(self):
        """A valid NAF string should return True."""
        assert is_naf_format_correct("431234567820") is True

    def test_is_naf_format_correct_invalid(self):
        """An invalid string should return False."""
        assert is_naf_format_correct("bad") is False

    def test_parse_naf_raises_argument_naf_invalid(self):
        """An invalid string should raise ArgumentNafInvalidError."""
        with pytest.raises(ArgumentNafInvalidError):
            parse_naf("not-a-naf")
