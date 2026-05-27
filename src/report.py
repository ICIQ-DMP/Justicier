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
from dataclasses import dataclass
from datetime import datetime
from importlib.metadata import version, PackageNotFoundError

from pyfiglet import Figlet

from data import unparse_date, unparse_full_date
from defines import RLCType
from logger import get_logger

log = get_logger(__name__)


def format_line(content: str, width: int = 119) -> str:
    """Formats a line with '*' borders and padded content."""
    content = content[: width - 4]  # Trim content if too long
    return f"* {content.ljust(width - 4)} *\n"


def get_initial_user_report(args: argparse.Namespace) -> str:
    figlet = Figlet(font="slant")
    ascii_logo_normal = figlet.renderText("Justicier").strip("\n").rstrip(" ")
    ascii_logo = ""
    for line in ascii_logo_normal.split("\n"):
        # Ensure the line is at least 120 characters long before slicing
        if len(line) >= 120:
            line = f"=                                     {line[:77]}   ="  # Replace char at index 120
        else:
            line = f"=                                     {line.ljust(77)}   ="  # Pad to 120 and then add "="
        ascii_logo += line + "\n"

    compact_something = any(args.merge_result.values())
    if compact_something:
        compact_text = ",".join(str(key.value) for key in args.merge_result.keys())
    else:
        compact_text = "No document categories to merge"

    try:
        pkg_version = version("justicier")
    except PackageNotFoundError:
        pkg_version = "unknown"

    user_report = "\n"
    user_report += "=======================================================================================================================\n"
    user_report += ascii_logo
    user_report += "=======================================================================================================================\n"
    user_report += f"                                        :: Justicier ::   Version: {pkg_version}\n"
    user_report += "                          Copyright © 2025-2025 Institut Català d'Investigació Química (ICIQ)\n"
    user_report += (
        "                                            This program is free software\n"
    )
    user_report += "                                  Proudly distributed with ♥ under the GPLv3 license\n"
    user_report += "***********************************************************************************************************************\n"
    user_report += "* Solution Arquitect and Maintainer: Aleix Mariné Tena (AleixMT), ICIQ, Data Steward                                  *\n"
    user_report += "* Product Owner: Carles de la Cuadra, ICIQ, Assistant Financial Manager                                               *\n"
    user_report += "***********************************************************************************************************************\n"
    user_report += "\n"
    user_report += "\n"
    user_report += "***********************************************************************************************************************\n"
    user_report += "*                                                USER REQUEST DETAILS                                                 *\n"
    user_report += "***********************************************************************************************************************\n"
    user_report += "* PARAMETERS:                                                                                                         *\n"
    user_report += format_line(f"- NAF requested: {args.naf}")
    user_report += format_line(f"- Initial date: {unparse_full_date(args.begin)}")
    user_report += format_line(f"- End date: {unparse_full_date(args.end)}")
    user_report += "* OPTIONS:                                                                                                            *\n"
    user_report += format_line(
        f"- Merge salaries with corresponding bankproof: {args.merge_salary}"
    )
    user_report += format_line(
        f"- Merge RNTs and RLCs of each month: {args.merge_rnt_rlc}"
    )
    user_report += format_line("- Document categories to merge: " + compact_text)
    user_report += "* IDENTIFICATION:                                                                                                     *\n"
    user_report += format_line("- Email of the user doing the request: " + args.author)
    user_report += format_line(f"- Request id: {args.request}")
    user_report += "***********************************************************************************************************************\n"
    user_report += "\n"

    return user_report


@dataclass(frozen=True)
class SalaryRLCConfig:
    rlc_code: str  # e.g. "L00", "L03", "L13"
    salary_label: str  # singular label used in per-month messages
    count_label: str  # plural label used in summary and success messages
    report_found: bool  # emit a "found" line when salary is present
    report_missing: bool  # emit a "not found" line when salary is absent
    track_quality: bool  # use something_wrong flag and emit a success/failure summary


_RLC_TYPE_CONFIG: dict[RLCType, SalaryRLCConfig] = {
    RLCType.SETTLEMENT: SalaryRLCConfig(
        rlc_code="L13",
        salary_label="settlement salary",
        count_label="settlement salaries",
        report_found=True,
        report_missing=False,
        track_quality=False,
    ),
    RLCType.DELAY: SalaryRLCConfig(
        rlc_code="L03",
        salary_label="delay salary",
        count_label="delay salaries",
        report_found=True,
        report_missing=False,
        track_quality=False,
    ),
    RLCType.REGULAR: SalaryRLCConfig(
        rlc_code="L00",
        salary_label="regular monthly salary",
        count_label="regular monthly salaries",
        report_found=False,
        report_missing=True,
        track_quality=True,
    ),
}


def _unparse_salary_rlc_for_type(
    content: dict[datetime, list[bool]],
    config: SalaryRLCConfig,
    args: argparse.Namespace,
) -> str:
    msg = ""
    something_wrong = False
    salaries_found = 0
    for key, values in content.items():
        if values[0]:
            salaries_found += 1
            if config.report_found:
                msg += f"A {config.salary_label} for NAF {args.naf} was found for month {unparse_date(key, '-')}\n"
            if not values[1]:
                something_wrong = True
                msg += f"The corresponding RLC {config.rlc_code} N for the {config.salary_label} for NAF {args.naf} was not found during month {unparse_date(key, '-')}\n"
            if not values[2]:
                something_wrong = True
                msg += f"The corresponding RLC {config.rlc_code} P for the {config.salary_label} for NAF {args.naf} was not found during month {unparse_date(key, '-')}\n"
        elif config.report_missing:
            something_wrong = True
            msg += f"{config.salary_label.capitalize()} for NAF {args.naf} was not found during month {unparse_date(key, '-')}\n"

    total = len(content)
    if config.track_quality:
        if salaries_found != total:
            something_wrong = True
            msg += f"In the period from {unparse_date(args.begin, '-')} to {unparse_date(args.end, '-')} there are {total} months, but only {salaries_found} {config.count_label} were found.\n"
        if not something_wrong:
            msg += f"All {config.count_label} and their requested RLC {config.rlc_code} N and RLC {config.rlc_code} P have been found :D\n"
    else:
        msg += f"In the period from {unparse_date(args.begin, '-')} to {unparse_date(args.end, '-')} there are {salaries_found} {config.count_label}.\n"
    return msg


def unparse_salary_rlc_result(
    content: dict[RLCType, dict[datetime, list[bool]]], args: argparse.Namespace
) -> str:
    msg = ""
    for rlc_type, type_content in content.items():
        config = _RLC_TYPE_CONFIG[rlc_type]
        msg += f"**** Salaries and RLC {config.rlc_code} \n"
        msg += _unparse_salary_rlc_for_type(type_content, config, args)
    return msg


def unparse_salary_rnt_result(
    rnt: dict[datetime, bool],
    salary: dict[RLCType, dict[datetime, list[bool]]],
    args: argparse.Namespace,
) -> str:
    something_wrong = False
    rnt_results = rnt
    salaries_result = salary[RLCType.REGULAR]

    log.trace(
        f"results previous to building report: RNT results: {rnt_results} salaries: {salaries_result}"
    )

    msg = ""
    for key, values in salaries_result.items():
        if values[0]:  # Salary for that month has been found
            if not rnt_results[key]:
                something_wrong = True
                msg += f"In the month {unparse_date(key, '-')} there is a salary, but no RNT has been found.\n"

    if not something_wrong:
        msg += "All RNTs have been found for all the months requested where a regular monthly salary is found :D\n"
    return msg


def unparse_contract_result(content: bool, args: argparse.Namespace) -> str:
    msg = ""
    if content:
        msg += f"In the period from {unparse_date(args.begin, '-')} to {unparse_date(args.end, '-')} a contract has been found for naf {args.naf} :D\n"
    else:
        msg += f"In the period from {unparse_date(args.begin, '-')} to {unparse_date(args.end, '-')} a contract has not been found for naf {args.naf}\n"
    return msg


def unparse_proofs_result(report_content: None, args: argparse.Namespace) -> str:
    msg = "At the time, there are no implemented check for the bankproofs in the user report.\n"
    return msg


def get_end_user_report(
    salaries_with_rlcs_result: dict[RLCType, dict[datetime, list[bool]]],
    contracts_result: bool,
    rnts_result: dict[datetime, bool],
    args: argparse.Namespace,
) -> str:
    msg = ""
    msg += "****** Salaries and RLC ****** \n" + unparse_salary_rlc_result(
        salaries_with_rlcs_result, args
    )
    msg += "****** Bank proofs ****** \n" + unparse_proofs_result(None, args)
    msg += "****** RNT ****** \n" + unparse_salary_rnt_result(
        rnts_result, salaries_with_rlcs_result, args
    )
    msg += "****** CONTRACT ****** \n" + unparse_contract_result(contracts_result, args)
    return "\n" + msg
