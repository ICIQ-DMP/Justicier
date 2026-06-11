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

"""Result-structure factories."""

from datetime import datetime
from typing import Dict, List, Any, TypeVar

from . import logger

log = logger.get_logger(__name__)


def get_rlc_monthly_result_structure(
    begin: datetime, end: datetime
) -> Dict[datetime, List[bool]]:
    """Return a per-month tracking structure for RLC documents (salary, N, P flags).

    Args:
        begin: Start of the period.
        end: End of the period.

    Returns:
        Dict mapping each month to a three-element bool list ``[salary, rlc_n, rlc_p]``.
    """
    return get_monthly_result_structure(begin, end, [False, False, False])


def get_rnt_monthly_result_structure(
    begin: datetime, end: datetime
) -> Dict[datetime, bool]:
    """Return a per-month tracking structure for RNT documents.

    Args:
        begin: Start of the period.
        end: End of the period.

    Returns:
        Dict mapping each month to a bool indicating whether the RNT was found.
    """
    return get_monthly_result_structure(begin, end, False)


def get_monthly_result_structure(
    begin: datetime, end: datetime, result_structure: Any
) -> Dict[datetime, Any]:
    """Build an ordered dict covering every month in the ``[begin, end]`` range.

    Args:
        begin: Start of the period.
        end: End of the period.
        result_structure: Default value assigned to each month key.

    Returns:
        Dict mapping ``datetime`` month keys to copies of *result_structure*.
    """
    log.trace(f"get_rlc_monthly_result_structure params: begin: {begin} end: {end}")
    current = datetime(begin.year, begin.month, 1)

    result = {}
    while current <= end:
        log.trace(f"Current datetime is: {current}")
        result[current] = (
            result_structure  # Monthly salary found, RLC L00N found, RLC L00P found
        )
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    log.trace(f"result structure:{result}")
    return result


_K = TypeVar("_K")
_V = TypeVar("_V")


def reverse_dict(d: dict[_K, _V]) -> dict[_V, _K]:
    """Return a new dict with keys and values swapped.

    Args:
        d: Source dictionary to invert.

    Returns:
        Inverted dictionary mapping original values to original keys.
    """
    r = {}
    for key, value in d.items():
        r[value] = key
    return r
