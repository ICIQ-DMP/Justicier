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

import argparse
import pytest

from arguments import get_compact_init


@pytest.fixture
def empty_args():
    """Minimal argparse Namespace with all local args unset — simulates a bare parse."""
    args = argparse.Namespace(
        request=None,
        naf=None,
        name=None,
        target_email=None,
        nif=None,
        begin=None,
        end=None,
        author=None,
        merge_result=get_compact_init(),
        merge_salary=False,
        merge_rnt_rlc=False,
        location="sharepoint",
        input_location=None,
    )
    return args
