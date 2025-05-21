import argparse
import datetime
import sys
from functools import partial

from NAF import NAF_TO_DNI, validate_parse_naf
from custom_except import *
from defines import NAF_DATA_PATH, DocType, from_string


def get_compact_init():
    return {DocType.SALARY: False, DocType.PROOFS: False, DocType.CONTRACT: False, DocType.RNT: False}


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
        return validate_parse_naf(value, NAF_TO_DNI.keys())
    except ValueError as e:
        raise ArgumentNafNotPresent("NAF is not valid" + e.__str__())


def parse_compact(value):
    to_compact = get_compact_init()
    try:
        if "," in value:
            for s in value.split(","):
                doc_type = from_string(s)
                to_compact[doc_type] = True
        else:
            doc_type = from_string(value)
            to_compact[doc_type] = True
        return to_compact
    except ValueError as e:
        print(f"Error: {e}")
        exit(1)


def parse_arguments(valid_nafs):
    """Parse and validate command-line arguments"""
    parser = argparse.ArgumentParser(description="Process NAF and date range.")

    parser.add_argument("-n", "--naf", type=parse_naf, required=True,
                        help="NAF (SS security number)")
    parser.add_argument("-b", "--begin", type=parse_date, required=True, help="Begin date (YYYY-MM)")
    parser.add_argument("-e", "--end", type=parse_date, required=True, help="End date (YYYY-MM)")
    parser.add_argument("-a", "--author", type=parse_author, required=True, help="author's email doing request")

    parser.add_argument("-c", "--compact", type=parse_compact, required=False, default=get_compact_init(), help="Comma separated list of values "
                                                                          "that indicate "
                        "which documents need to be merged in one signle PDF in the output. Possible values are: " + ",".join([dt.value.__str__() for dt in DocType]))

    args = parser.parse_args()

    return args


def process_arguments():
    common = ("Error parsing arguments. Program aborting. The arguments are: "
              + str(sys.argv) + "The program is in a uninitialized state and cannot proceed. This error will be "
                                "notified to the admin via log file. We can't create log file in user author folder "
                                "because user author could not be parsed.")
    try:
        args = parse_arguments(NAF_TO_DNI.keys())

    except ArgumentNafNotPresent as e:
        print("The NAF provided is valid but is not present in " + NAF_DATA_PATH + ". Internal error is " + e.__str__())
        print(common)
        exit(1)
    except ArgumentNafInvalid as e:
        print("The NAF provided is invalid. Internal error is " + e.__str__())
        print(common)
        exit(2)
    except ArgumentDateError as e:
        print("The dates provided are invalid. Internal error is " + e.__str__())
        print(common)
        exit(3)
    except ArgumentAuthorError as e:
        print("The author is not present in the accepted user list. Internal error is " + e.__str__())
        print(common)
        exit(4)
    except argparse.ArgumentTypeError as e:
        print("Arguments could not have been parsed. Internal error is " + e.__str__())
        print(common)
        exit(5)
    return args


