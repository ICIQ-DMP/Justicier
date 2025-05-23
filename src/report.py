from pyfiglet import Figlet

from data import unparse_date
from defines import DocType, RLCType


def format_line(content: str, width: int = 119) -> str:
    """Formats a line with '*' borders and padded content."""
    content = content[:width - 4]  # Trim content if too long
    return f"* {content.ljust(width - 4)} *\n"


def get_initial_user_report(args):
    figlet = Figlet(font='slant')
    ascii_logo_normal = figlet.renderText('El Justicier').strip("\n").rstrip(" ")
    ascii_logo = ""
    for line in ascii_logo_normal.split("\n"):
        # Ensure the line is at least 120 characters long before slicing
        if len(line) >= 120:
            line = "=                              " + line[:84] + "   ="  # Replace char at index 120
        else:
            line = "=                              " + line.ljust(84) + "   ="  # Pad to 120 and then add "="
        ascii_logo += line + "\n"

    compact_something = any(args.compact.values())
    if compact_something:
        compact_text = ",".join(str(key.value) for key in args.compact.keys())
    else:
        compact_text = "No document categories to merge"

    version = "".join(open("version.txt").readlines())

    user_report = "\n"
    user_report += "=======================================================================================================================\n"
    user_report += "" + ascii_logo
    user_report += "=======================================================================================================================\n"
    user_report += "                                  :: El Justicier ::   Version: " + version + "\n"
    user_report += "                        Copyright © 2025-2025 Institut Català d'Investigació Química (ICIQ)\n"
    user_report += "                                            This program is free software\n"
    user_report += "                                   Proudly distributed with ♥ under the GPLv3 license\n"
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
    user_report += format_line("- Email of the user doing the request: " + args.author)
    user_report += format_line("- NAF requested: " + args.naf.__str__())
    user_report += format_line("- Initial date: " + unparse_date(args.begin))
    user_report += format_line("- End date: " + unparse_date(args.end))
    user_report += format_line("OPTIONS:")
    user_report += format_line("- Document categories of the document type to merge: " + compact_text)
    user_report += "***********************************************************************************************************************\n"
    user_report += "\n"

    return user_report


def unparse_salary_rlc_result_settlement(content, args):
    msg = ""
    salaries_found = 0
    for key in content.keys():
        if content[key][0]:
            salaries_found += 1
            msg += ("A settlement for NAF " + str(args.naf) + " was found for month "
                    + unparse_date(key, "-") + "\n")
            if not content[key][1]:
                msg += ("The corresponding RLC L13 N for the settlement salary for NAF "
                        + str(args.naf) + " was not found during month " + unparse_date(key, "-") + "\n")
            if not content[key][2]:
                msg += ("The corresponding RLC L13 P for the settlement salary for NAF " + str(args.naf)
                        + " was not found during month " + unparse_date(key, "-") + "\n")

    msg += ("In the period from " + unparse_date(args.begin, "-") + " to " +
            unparse_date(args.end, "-") + " there are " + str(salaries_found) +
            " settlement salaries.\n")
    return msg


def unparse_salary_rlc_result_delay(content, args):
    """
    Número de nómines d´endarreriments trobades i de quin mes.
    """
    msg = ""
    salaries_found = 0
    for key in content.keys():
        if content[key][0]:
            salaries_found += 1
            msg += ("A delay salary for NAF " + str(args.naf) + " was found for month "
                    + unparse_date(key, "-") + "\n")
            if not content[key][1]:
                msg += ("The corresponding RLC L03 N for the delay salary for NAF "
                        + str(args.naf) + " was not found during month " + unparse_date(key, "-") + "\n")
            if not content[key][2]:
                msg += ("The corresponding RLC L03 P for the delay salary for NAF " + str(args.naf)
                        + " was not found during month " + unparse_date(key, "-") + "\n")

    msg += ("In the period from " + unparse_date(args.begin, "-") + " to " +
            unparse_date(args.end, "-") + " there are " + str(salaries_found) +
            " delay salaries.\n")
    return msg


def unparse_salary_rlc_result_regular(content, args):
    """
    Numero de Nomines totals que hi ha en el periode, és a dir, si fem una busqueda de gener de 2024 a desembre de 2024
    hi ha d´haver 12 nómines una per cada mes, les d´endarreriments no compten. Aleshores hi ha d´haver comparativa de
    número de nomines trobades en el periode  i número de nomines no trobades (de les no trobades el mes que no ha
    trobat)
    """
    msg = ""
    something_wrong = False
    salaries_found = 0
    for key in content.keys():
        if content[key][0]:
            salaries_found += 1
            if not content[key][1]:
                something_wrong = True
                msg += ("The corresponding RLC L00 N for the regular monthly salary for NAF "
                        + str(args.naf) + " was not found during month " + unparse_date(key, "-") + "\n")
            if not content[key][2]:
                something_wrong = True
                msg += ("The corresponding RLC L00 P for the regular monthly salary for NAF " + str(args.naf)
                        + " was not found during month " + unparse_date(key, "-") + "\n")
        if not content[key][0]:
            something_wrong = True
            msg += ("Regular monthly salary for NAF " + str(args.naf) + " was not found during month "
                    + unparse_date(key, "-") + "\n")

    if salaries_found != len(content.keys()):
        something_wrong = True
        msg += ("In the period from " + unparse_date(args.begin, "-") + " to " +
                unparse_date(args.end, "-") + " there are " + str(len(content.keys())) +
                " months, but only " + str(salaries_found) + " regular salaries were found.\n")

    if not something_wrong:
        msg += "All regular monthly salaries and their requested RLC L00 N and RLC L00 P have been found :D\n"
    return msg


def unparse_salary_rlc_result(content, args):
    msg = ""

    for key in content.keys():
        if key == RLCType.REGULAR:
            msg += "**** Salaries and RLC L00 \n" + unparse_salary_rlc_result_regular(content[key], args)
        elif key == RLCType.DELAY:
            msg += "**** Salaries and RLC L03 \n" + unparse_salary_rlc_result_delay(content[key], args)
        elif key == RLCType.SETTLEMENT:
            msg += "**** Salaries and RLC L13 \n" + unparse_salary_rlc_result_settlement(content[key], args)
    return msg


def unparse_salary_rnt_result(content, args):
    something_wrong = False
    rnt_results = content[0]
    salaries_result = content[1][RLCType.REGULAR]
    msg = ""
    for key in salaries_result.keys():
        if salaries_result[key][0]:  # Salary for that month has been found
            if not rnt_results[key]:
                something_wrong = True
                msg += "In the month " + unparse_date(key, "-") + " there is a salary, but no RNT has been found.\n"

    if not something_wrong:
        msg += "All RNTs have been found for all the months requested where a regular monthly salary is found :D\n"
    return msg


def unparse_contract_result(content, args):
    msg = ""
    if content:
        msg += ("In the period from " + unparse_date(args.begin, "-") + " to " +
                unparse_date(args.end, "-") + " a contract has been found for naf " + str(args.naf) + " :D\n")
    else:
        msg += ("In the period from " + unparse_date(args.begin, "-") + " to " +
                unparse_date(args.end, "-") + " a contract has not been found for naf " + str(args.naf) + "\n")
    return msg


def unparse_proofs_result(report_content, args):
    msg = "At the time, there are no implemented check for the bankproofs in the user report.\n"
    return msg


def get_end_user_report(reports, args):
    msg = ""
    for report_type in reports.keys():
        report_content = reports[report_type]
        if report_type == DocType.SALARY:
            msg += "****** Salaries and RLC ****** \n" + unparse_salary_rlc_result(report_content, args)
        elif report_type == DocType.PROOFS:
            msg += "****** Bank proofs ****** \n" + unparse_proofs_result(report_content, args)
        elif report_type == DocType.RNT:
            msg += "****** RNT ****** \n" + unparse_salary_rnt_result((report_content, reports[DocType.SALARY]), args)
        elif report_type == DocType.CONTRACT:
            msg += "****** CONTRACT ****** \n" + unparse_contract_result(report_content, args)
    return "\n" + msg