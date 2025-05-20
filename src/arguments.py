import argparse
import datetime
from functools import partial

from NAF import NAF_TO_DNI, validate_naf
from custom_except import *


def parse_date(value, formatting="%Y_%m"):
    """Validate date format"""
    try:
        return datetime.datetime.strptime(value, formatting)
    except Exception as e:
        raise ArgumentDateError("The value " + value + " could not be formatted with "
                         + formatting + ". Datetime exception was " + e.__str__())


def parse_author(author):
    with open("input/users.txt", newline="", encoding="utf-8") as f:
        for line in f.readlines():
            if line.__eq__(author):
                return author
        raise ArgumentAuthorError("Author " + author + " is not in the accepted user list (input/users.txt).")


def parse_naf(value):
    try:
        return validate_naf(value, NAF_TO_DNI.keys())
    except ValueError as e:
        raise ArgumentNafError("NAF is not valid" + e.__str__())


def parse_arguments(valid_nafs):
    """Parse and validate command-line arguments"""
    parser = argparse.ArgumentParser(description="Process NAF and date range.")

    parser.add_argument("-n", "--naf", type=parse_naf, required=True,
                        help="NAF (SS security number)")
    parser.add_argument("-b", "--begin", type=parse_date, required=True, help="Begin date (YYYY-MM)")
    parser.add_argument("-e", "--end", type=parse_date, required=True, help="End date (YYYY-MM)")
    parser.add_argument("-a", "--author", type=parse_author, required=True, help="author's email doing request")

    args = parser.parse_args()

    return args
