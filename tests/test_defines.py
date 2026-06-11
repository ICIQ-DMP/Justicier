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

"""Tests for defines.py: DocType enum and from_string alias resolution."""

import pytest

from justicier.defines import DocType, from_string


class TestFromString:
    """Tests for the from_string DocType resolver."""

    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("salary", DocType.SALARY),
            ("salaries", DocType.SALARY),
            ("SALARY", DocType.SALARY),
            ("payslip", DocType.SALARY),
            ("contract", DocType.CONTRACT),
            ("CONTRACT", DocType.CONTRACT),
            ("RLC", DocType.RLC),
            ("rlc", DocType.RLC),
            ("RNT", DocType.RNT),
            ("rnt", DocType.RNT),
            ("proof", DocType.PROOFS),
            ("proofs", DocType.PROOFS),
            ("bankproof", DocType.PROOFS),
        ],
    )
    def test_known_aliases(self, alias, expected):
        """Each alias should resolve to the expected DocType."""
        assert from_string(alias) == expected

    def test_unknown_raises(self):
        """An unrecognised string should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown document type"):
            from_string("unknown_type")

    def test_strips_whitespace(self):
        """Leading/trailing whitespace should be ignored when resolving aliases."""
        assert from_string("  salary  ") == DocType.SALARY


class TestDocType:
    """Tests for DocType enum values."""

    def test_enum_values(self):
        """All DocType members should have the expected string values."""
        assert DocType.SALARY.value == "salary"
        assert DocType.CONTRACT.value == "contract"
        assert DocType.RLC.value == "RLC"
        assert DocType.RNT.value == "RNT"
        assert DocType.PROOFS.value == "proofs"
        assert DocType.SALARIES_AND_PROOFS.value == "salaries with proofs"
