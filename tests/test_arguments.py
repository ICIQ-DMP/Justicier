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

import datetime
import pytest

from arguments import parse_boolean, parse_date, _ID_OVERRIDES, get_compact_init
from custom_except import ArgumentDateError


class TestParseBoolean:
    def test_true_string(self):
        assert parse_boolean("True") is True

    def test_false_string(self):
        assert parse_boolean("False") is False

    def test_true_literal(self):
        assert parse_boolean(True) is True

    def test_false_literal(self):
        assert parse_boolean(False) is False

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_boolean("yes")


class TestParseDate:
    def test_date_only(self):
        result = parse_date("2024-08-31")
        assert isinstance(result, datetime.datetime)
        assert result.year == 2024
        assert result.month == 8
        assert result.day == 31

    def test_iso_datetime_with_z(self):
        result = parse_date(
            "2024-08-31T22:00:00Z", formatting="%Y-%m-%dT%H:%M:%SZ", return_naive=False
        )
        assert isinstance(result, datetime.datetime)
        assert result.year == 2024

    def test_invalid_raises(self):
        with pytest.raises(ArgumentDateError):
            parse_date("not-a-date")


class TestIDOverrides:
    """Smoke tests for the _ID_OVERRIDES contract — ensures all expected keys exist."""

    EXPECTED_KEYS = {
        "naf",
        "name",
        "target_email",
        "nif",
        "begin",
        "end",
        "author",
        "merge_result",
        "merge_salary",
        "merge_rnt_rlc",
    }

    def test_all_expected_keys_present(self):
        assert self.EXPECTED_KEYS == set(_ID_OVERRIDES.keys())

    def test_unset_args_all_falsy(self, empty_args):
        """An empty Namespace should produce no warnings (all checks falsy)."""
        triggered = [
            name for name, was_set in _ID_OVERRIDES.items() if was_set(empty_args)
        ]
        assert triggered == []

    def test_set_naf_is_detected(self, empty_args):
        from NAF import NAF

        empty_args.naf = NAF("431234567820")
        triggered = [
            name for name, was_set in _ID_OVERRIDES.items() if was_set(empty_args)
        ]
        assert "naf" in triggered

    def test_nondefault_merge_result_is_detected(self, empty_args):
        compact = get_compact_init()
        compact[list(compact.keys())[0]] = True
        empty_args.merge_result = compact
        triggered = [
            name for name, was_set in _ID_OVERRIDES.items() if was_set(empty_args)
        ]
        assert "merge_result" in triggered
