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

"""Date/salary parsing helpers and result-structure factories."""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import logger
from defines import SalaryType

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
        key = datetime.strptime(str(current.year * 100 + current.month), "%Y%m")
        log.trace(f"Parsed key is: {key}")
        result[key] = (
            result_structure  # Monthly salary found, RLC L00N found, RLC L00P found
        )
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    log.trace(f"result structure:{result}")
    return result


def parse_salary_type(salary_file_path: Path) -> "SalaryType":
    """Extract the SalaryType from a salary filename's second underscore-delimited field.

    Args:
        salary_file_path: Path to the salary PDF file.

    Returns:
        The SalaryType encoded in the filename.
    """
    parsed = Path(salary_file_path).stem.split("_")[1]
    log.debug("Data parsed from filename is: " + parsed)
    t = SalaryType(parsed)
    log.debug(f"Type detected is: {t}")
    return t


def parse_year_salary_path(salary_file: str) -> datetime:
    """Parse the four-digit year from a salary file path.

    Args:
        salary_file: Relative salary file path, e.g. ``"24/2401_Nomines_...pdf"``.

    Returns:
        datetime with only the year component set.
    """
    return datetime.strptime("20" + salary_file.split("/")[1].split("_")[0][:2], "%Y")


def parse_month_salary_path(salary_file: str) -> datetime:
    """Parse the two-digit month from a salary file path.

    Args:
        salary_file: Relative salary file path.

    Returns:
        datetime with only the month component set.
    """
    return datetime.strptime(
        salary_file[::-1].split("/")[0][::-1].split("_")[0][2:], "%m"
    )


def parse_date_from_key(key: str) -> datetime:
    """Parse a ``YYYYMM`` key string into a datetime.

    Args:
        key: Six-digit year-month string, e.g. ``"202403"``.

    Returns:
        datetime representing the first moment of that month.
    """
    return datetime.strptime(key, "%Y%m")


def unparse_year(date_obj: datetime) -> str:
    """Return the four-digit year string from *date_obj*.

    Args:
        date_obj: Source datetime.

    Returns:
        Four-digit year as a string.
    """
    return date_obj.year.__str__()


def unparse_year_month_short(d: datetime) -> str:
    """Return the two-digit year concatenated with the two-digit month.

    Args:
        d: Source datetime.

    Returns:
        Four-character string, e.g. ``"2403"``.
    """
    return unparse_year_short(d) + unparse_month(d)


def unparse_year_month(d: datetime) -> str:
    """Return the four-digit year concatenated with the two-digit month.

    Args:
        d: Source datetime.

    Returns:
        Six-character string, e.g. ``"202403"``.
    """
    return unparse_year(d) + unparse_month(d)


def unparse_year_short(date_obj: datetime) -> str:
    """Return the last two digits of the year as a string.

    Args:
        date_obj: Source datetime.

    Returns:
        Two-digit year string, e.g. ``"24"`` for 2024.
    """
    rep = str(date_obj.year)
    if date_obj.year >= 1000:
        return rep[2:4]
    else:
        return rep


def unparse_month(date_obj: datetime) -> str:
    """Return the zero-padded two-digit month string from *date_obj*.

    Args:
        date_obj: Source datetime.

    Returns:
        Two-digit month string, e.g. ``"03"`` or ``"11"``.
    """
    if date_obj.month >= 10:
        return date_obj.month.__str__()
    else:
        return "0" + date_obj.month.__str__()


def unparse_day(date_obj: datetime) -> str:
    """Return the zero-padded two-digit day string from *date_obj*.

    Args:
        date_obj: Source datetime.

    Returns:
        Two-digit day string, e.g. ``"05"`` or ``"23"``.
    """
    if date_obj.day >= 10:
        return date_obj.day.__str__()
    else:
        return "0" + date_obj.day.__str__()


def unparse_date(d: datetime, separator: str = "-") -> str:
    """Return a ``MM<sep>YYYY`` string from *d*.

    Args:
        d: Source datetime.
        separator: Character placed between month and year. Defaults to ``"-"``.

    Returns:
        Formatted string, e.g. ``"03-2024"``.
    """
    return unparse_month(d) + separator + d.year.__str__()


def unparse_full_date(d: datetime, separator: str = "-") -> str:
    """Return a ``DD<sep>MM<sep>YYYY`` string from *d*.

    Args:
        d: Source datetime.
        separator: Character placed between components. Defaults to ``"-"``.

    Returns:
        Formatted string, e.g. ``"05-03-2024"``.
    """
    return unparse_day(d) + separator + unparse_month(d) + separator + d.year.__str__()


def parse_date_from_salary_filename(salary_path: str) -> datetime:
    """Parse the ``YYYYMM`` date encoded in a salary filename.

    Args:
        salary_path: Path string whose filename starts with a ``YYMM`` prefix.

    Returns:
        datetime representing the salary's year and month.
    """
    # todo Exception when can't parse
    return datetime.strptime(
        "20" + salary_path[::-1].split("/")[0][::-1].split(".")[0].split("_")[0], "%Y%m"
    )


def parse_salary_type_from_salary_filename(salary_file_name: str) -> str:
    """Extract the salary type token from the filename's second underscore field.

    Args:
        salary_file_name: Salary filename, e.g. ``"2403_Nomines_...pdf"``.

    Returns:
        Salary type string, e.g. ``"Nomines"``.
    """
    # todo Exception when can't parse

    return salary_file_name.split("_")[1]


def parse_salary_filename_from_salary_path(salary_path: Path) -> str:
    """Return just the filename (without directory) from *salary_path*.

    Args:
        salary_path: Full or relative path to a salary file.

    Returns:
        The filename component as a string.
    """
    return Path(salary_path).name
