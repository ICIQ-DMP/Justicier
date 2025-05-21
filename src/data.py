'''
Frontier
'''
import os
from datetime import datetime
from typing import Dict, Tuple

from defines import SalaryType
import logger


def get_monthly_result_structure(begin: datetime, end: datetime) -> Dict[str, Tuple[bool, bool, bool]]:
    result = {}
    current = datetime(begin.year, begin.month, 1)

    while current <= end:
        key = datetime.strptime(str(current.year * 100 + current.month), "%Y%m")
        result[key] = [False, False, False]  # Monthly salary found, RLC L00N found, RLC L00P found
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return result


def parse_salary_type(salary_file_path):
    custom_logger = logger.get_process_logger(logger.base_logger, "Salaries and RLCs")
    parsed = salary_file_path[::-1].split("/")[0][::-1].split(".")[0].split("_")[1]
    custom_logger.debug("Data parsed from filename is: " + parsed)
    t = SalaryType(parsed)
    custom_logger.debug("Type detected is: " + t.__str__())
    return t


def parse_year_salary_path(salary_file):
    return datetime.strptime("20" + salary_file.split("/")[1].split("_")[0][:2], "%Y")


def parse_month_salary_path(salary_file):
    return datetime.strptime(salary_file[::-1].split("/")[0][::-1].split("_")[0][2:], "%m")


def parse_date_from_key(key: str):
    return datetime.strptime(key, "%Y%m")


def unparse_month(date_obj):
    if date_obj.month >= 10:
        return date_obj.month.__str__()
    else:
        return "0" + date_obj.month.__str__()


def unparse_date(d, separator="-"):
    return unparse_month(d) + separator + d.year.__str__()


def parse_date_from_salary_filename(salary_path):
    return datetime.strptime("20" + salary_path[::-1].split("/")[0][::-1].split(".")[0].split("_")[0], "%Y%m")


def parse_salary_filename_from_salary_path(salary_path):
    return os.path.basename(salary_path)

