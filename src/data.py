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

"""
Frontier
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

import logger
from defines import SalaryType

log = logger.get_logger(__name__)


def get_rlc_monthly_result_structure(
    begin: datetime, end: datetime
) -> Dict[datetime, List[bool]]:
    return get_monthly_result_structure(begin, end, [False, False, False])


def get_rnt_monthly_result_structure(
    begin: datetime, end: datetime
) -> Dict[datetime, bool]:
    return get_monthly_result_structure(begin, end, False)


def get_monthly_result_structure(
    begin: datetime, end: datetime, result_structure: Any
) -> Dict[datetime, Any]:
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
    parsed = Path(salary_file_path).stem.split("_")[1]
    log.debug("Data parsed from filename is: " + parsed)
    t = SalaryType(parsed)
    log.debug(f"Type detected is: {t}")
    return t


def parse_year_salary_path(salary_file: str) -> datetime:
    return datetime.strptime("20" + salary_file.split("/")[1].split("_")[0][:2], "%Y")


def parse_month_salary_path(salary_file: str) -> datetime:
    return datetime.strptime(
        salary_file[::-1].split("/")[0][::-1].split("_")[0][2:], "%m"
    )


def parse_date_from_key(key: str) -> datetime:
    return datetime.strptime(key, "%Y%m")


def unparse_year(date_obj: datetime) -> str:
    return date_obj.year.__str__()


def unparse_year_month_short(d: datetime) -> str:
    return unparse_year_short(d) + unparse_month(d)


def unparse_year_month(d: datetime) -> str:
    return unparse_year(d) + unparse_month(d)


def unparse_year_short(date_obj: datetime) -> str:
    rep = str(date_obj.year)
    if date_obj.year >= 1000:
        return rep[2:4]
    else:
        return rep


def unparse_month(date_obj: datetime) -> str:
    if date_obj.month >= 10:
        return date_obj.month.__str__()
    else:
        return "0" + date_obj.month.__str__()


def unparse_day(date_obj: datetime) -> str:
    if date_obj.day >= 10:
        return date_obj.day.__str__()
    else:
        return "0" + date_obj.day.__str__()


def unparse_date(d: datetime, separator: str = "-") -> str:
    return unparse_month(d) + separator + d.year.__str__()


def unparse_full_date(d: datetime, separator: str = "-") -> str:
    return unparse_day(d) + separator + unparse_month(d) + separator + d.year.__str__()


def parse_date_from_salary_filename(salary_path: str) -> datetime:
    return datetime.strptime(
        "20" + salary_path[::-1].split("/")[0][::-1].split(".")[0].split("_")[0], "%Y%m"
    )


def parse_salary_type_from_salary_filename(salary_file_name: str) -> str:
    return salary_file_name.split("_")[1]


def parse_salary_filename_from_salary_path(salary_path: Path) -> str:
    return Path(salary_path).name
