'''
Frontier
'''
import os
from datetime import datetime
from typing import Dict, List

import pytz

import logger
from defines import SalaryType


def get_rlc_monthly_result_structure(begin: datetime, end: datetime, result_structure=None) -> Dict[str, List[bool]]:

    tz = pytz.timezone("Europe/Madrid")
    current = datetime(begin.year, begin.month, 1)
    current = tz.localize(current)

    print(begin)
    print(current)

    result = {}
    while current <= end:
        key = datetime.strptime(str(current.year * 100 + current.month), "%Y%m")
        if result_structure is None:
            result[key] = [False, False, False]
        else:
            result[key] = result_structure  # Monthly salary found, RLC L00N found, RLC L00P found
        # Move to next month
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)

    return result




def parse_salary_type(salary_file_path):
    custom_logger = logger.build_process_logger(logger.get_logger_instance(), "Salaries and RLCs")
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

