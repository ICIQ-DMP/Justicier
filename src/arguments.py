import argparse
import datetime
import sys
from functools import partial

from NAF import is_naf_present, NAF, build_naf_to_dni
from custom_except import *
from defines import NAF_DATA_PATH, DocType, from_string


def get_compact_init():
    return {DocType.SALARY: False, DocType.PROOFS: False, DocType.CONTRACT: False, DocType.RNT: False, DocType.RLC: False}


# Parser functions that validate the format and type of the data


def parse_date(value, formatting="%Y-%m-%d"):
    """Validate date format"""
    try:
        return datetime.datetime.strptime(value, formatting)
    except Exception as e:
        raise ArgumentDateError("The value " + value + " could not be formatted with "
                         + formatting + ". Datetime exception was " + e.__str__())


def parse_author(author):
    return author


def parse_naf(value):
    try:
        return NAF(value)
    except ValueError as e:
        raise ArgumentNafInvalid("NAF is not valid" + e.__str__())


def parse_compact_options(value):
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


def parse_input_type(value):
    if value == "sharepoint":
        return value
    elif value == "local":
        return value
    else:
        raise UndefinedInputType("The type supplied for input type \"" + value + "\" is not defined.")


def parse_arguments():
    """Parse and validate command-line arguments"""
    parser = argparse.ArgumentParser(description="Process NAF and date range.")

    parser.add_argument("-n", "--naf", type=parse_naf, required=True,
                        help="NAF (SS security number)")
    parser.add_argument("-b", "--begin", type=parse_date, required=True, help="Begin date (YYYY-MM)")
    parser.add_argument("-e", "--end", type=parse_date, required=True, help="End date (YYYY-MM)")
    parser.add_argument("-a", "--author", type=parse_author, required=True, help="author's email doing request")

    parser.add_argument("-c", "--compact", type=parse_compact_options, required=False, default=get_compact_init(),
                        help="Comma separated list of values that indicate which documents need to be merged in one "
                             "single PDF in the output. Possible values are: " +
                             ",".join([dt.value.__str__() for dt in DocType]))

    parser.add_argument("-i", "--input", type=parse_input_type, required=False, default="sharepoint",
                        help="Location of the input data. Possible values are: \"sharepoint\" to download from "
                             "sharepoint location and \"local\" to use the local file system storage adn read the input"
                             " folder in the repository root folder.")
    args = parser.parse_args()

    return args


def process_parse_arguments():
    common = ("Error parsing arguments. Program aborting. The arguments are: "
              + str(sys.argv) + "The program is in a uninitialized state and cannot proceed. This error will be "
                                "notified to the admin via log file. We can't create log file in user author folder "
                                "because user author could not be parsed.")
    try:
        args = parse_arguments()

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


# Validations functions that check if the data from the request is valid regarding business rules


def validate_naf(naf, valid_nafs):
    if not is_naf_present(naf, valid_nafs):
        raise ArgumentNafNotPresent


def is_author_present(author, valid_authors):
    return author in valid_authors


def validate_author(author, valid_authors):
    if not is_author_present(author, valid_authors):
        raise ArgumentAuthorError("Author \"" + str(author) + " is not valid. ")  # more specific exception


def validate_arguments(args, valid_nafs, valid_authors):
    validate_author(args.author, valid_authors)
    validate_naf(args.naf, valid_nafs)


def process_validate_arguments(args, naf_data_path, user_list_data_path):
    common = ("Error validating arguments. Program aborting. The arguments are: "
              + str(sys.argv) + "The program is in a uninitialized state and cannot proceed. This error will be "
                                "notified to the admin via log file. We can't create log file in user author folder "
                                "because the process that validates user author could not finish.")

    nafs = build_naf_to_dni(naf_data_path).keys()

    authors = []
    with open(user_list_data_path, newline="", encoding="utf-8") as f:
        for line in f.readlines():
            authors.append(line)

    try:
        validate_arguments(args, nafs, authors)

    except ArgumentNafNotPresent as e:
        print("The NAF provided is valid but is not present in " + naf_data_path + ". Internal error is " + e.__str__())
        print(common)
        exit(1)
    except ArgumentAuthorError as e:
        print("The author is not present in the accepted user list. Internal error is " + e.__str__())
        print(common)
        exit(4)
