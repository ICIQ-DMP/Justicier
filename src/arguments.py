import argparse
import datetime
import sys

from NAF import is_naf_present, build_naf_to_dni, parse_naf
from custom_except import *
from defines import DocType, from_string
from secret import read_secret
from sharepoint import get_parameters_from_list
from DNI import parse_dni
from Name import parse_name_sharepoint, parse_name_a3


def get_compact_init():
    return {DocType.SALARY: False, DocType.PROOFS: False, DocType.CONTRACT: False, DocType.RNT: False,
            DocType.RLC: False}


# Parser functions that validate the format and type of the data
def parse_id(value):
    return value


def parse_date(value, formatting="%Y-%m-%d"):
    """Validate date format"""
    try:
        return datetime.datetime.strptime(value, formatting)
    except Exception as e:
        raise ArgumentDateError("The value " + value + " could not be formatted with "
                                + formatting + ". Datetime exception was " + e.__str__())


def parse_author(author):
    return author


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


def parse_boolean(value):
    if value is True:
        return value
    elif value is False:
        return value
    print("the value " + str(value))
    if value is bool:
        return value
    if value == "True":
        return True
    elif value == "False":
        return False
    raise ValueError("The value " + str(value) + " can not be parsed into a boolean. It should be 'True' or 'False'")


def parse_input_type(value):
    if value == "sharepoint":
        return value
    elif value == "local":
        return value
    else:
        raise UndefinedInputType("The type supplied for input type \"" + value + "\" is not defined.")


def expand_job_id(job_id):
    sharepoint_domain = read_secret("SHAREPOINT_DOMAIN")
    site_name = read_secret("SITE_NAME")
    list_name = read_secret("SHAREPOINT_LIST_NAME")

    return get_parameters_from_list(sharepoint_domain, site_name, list_name, job_id)


def parse_arguments_helper(arg_text: str):
    print(f"The {arg_text} has been provided via argument but it is used in conjunction with argument to "
          f"select request ID. The provided {arg_text} via argument will ge ignored and the {arg_text} from "
          f"the corresponding row of the provided Microsoft List will be used.")


def parse_arguments():
    """Parse and validate command-line arguments"""
    parser = argparse.ArgumentParser(description="")

    parser.add_argument("-r", "--request", type=parse_id, required=False,
                        help='ID of the justification request in Microsoft List of Peticions Justificacions. If you use'
                             ' this argument you can\'t use any other argument to submit data to the algorithm except '
                             ' for -l / --location ')

    parser.add_argument("-l", "--location", type=parse_input_type, required=False, default="sharepoint",
                        help="Location of the input data. Possible values are: \"sharepoint\" to download from "
                             "sharepoint location and \"local\" to use the local file system storage and read the input"
                             " folder in the repository root folder.")

    parser.add_argument("-n", "--naf", "--NAF", type=parse_naf, required=False,
                        help="NAF (SS security number) of the employee to justify")
    parser.add_argument("-N", "--name", type=parse_name_a3, required=False,
                        help="Name of the employee to ")
    parser.add_argument("-d", "--dni", "--DNI", type=parse_dni, required=False,
                        help="Name of the employee to justify")

    parser.add_argument("-b", "--begin", type=parse_date, required=False, help="Begin date (YYYY-MM-DD)")
    parser.add_argument("-e", "--end", type=parse_date, required=False, help="End date (YYYY-MM-DD)")
    parser.add_argument("-a", "--author", type=parse_author, required=False, help="author's email doing"
                                                                                  " request")

    parser.add_argument("-s", "--merge-salary", type=parse_boolean, required=False, default=False,
                        help="Merge each salary with the corresponding bank proof")
    parser.add_argument("-m", "--merge-result", type=parse_boolean, required=False,
                        default=get_compact_init(),
                        help="Merge each salary with the corresponding bank proof")
    parser.add_argument("-R", "--merge-rlc", type=parse_boolean, required=False, default=False,
                        help="Comma separated list of values that indicate which documents need to be merged in one "
                             "single PDF in the output. Possible values are: " +
                             ",".join([dt.value.__str__() for dt in DocType]))

    args = parser.parse_args()
    return args


def parse_sharepoint_arguments(args, common):
    if args.naf:
        parse_arguments_helper("NAF")
    if args.name:
        parse_arguments_helper("name")
    if args.dni:
        parse_arguments_helper("DNI")
    if args.begin:
        parse_arguments_helper("begin date")
    if args.end:
        parse_arguments_helper("end date")
    if args.author:
        parse_arguments_helper("author")
    if args.merge_result != get_compact_init():
        parse_arguments_helper("merge result")
    if args.merge_salary:
        parse_arguments_helper("merge salary")
    if args.merge_rlc:
        parse_arguments_helper("merge rlc")
    config = expand_job_id(args.request)
    try:
        if config['NAF']:
            args.naf = parse_naf(config['NAF'])
        if config['name']:
            args.name = parse_name_sharepoint(config['name'])
        if config['DNI']:
            args.dni = parse_dni(config['DNI'])
        args.begin = parse_date(config['begin'], "%Y-%m-%dT%H:%M:%SZ")
        args.end = parse_date(config['end'], "%Y-%m-%dT%H:%M:%SZ")
        args.author = parse_author(config['author'])
        args.merge_salary = parse_boolean(config['merge_salary_bankproof'])
        if parse_boolean(config['merge_results']):
            compact_default = get_compact_init()
            for key in compact_default.keys():
                compact_default[key] = True
            args.merge_results = compact_default
        args.merge_rlc = parse_boolean(config['merge_RLC_RNT'])
    except ArgumentNafInvalid as e:
        print("The NAF provided is invalid. Internal error is " + e.__str__())
        print(common)
        exit(2)
    except ArgumentDateError as e:
        print("The dates provided are invalid. Internal error is " + e.__str__())
        print(common)
        exit(3)
    except argparse.ArgumentTypeError as e:
        print("Arguments could not have been parsed. Internal error is " + e.__str__())
        print(common)
        exit(5)


def process_parse_arguments():
    common = ("Error parsing arguments. Program aborting. The arguments are: "
              + str(sys.argv) + "The program is in a uninitialized state and cannot proceed. This error will be "
                                "notified to the admin via log file. We can't create log file in user author folder "
                                "because user author could not be parsed.")
    try:
        args = parse_arguments()

    except ArgumentNafInvalid as e:
        print("The NAF provided is invalid. Internal error is " + e.__str__())
        print(common)
        exit(2)
    except ArgumentDateError as e:
        print("The dates provided are invalid. Internal error is " + e.__str__())
        print(common)
        exit(3)
    except argparse.ArgumentTypeError as e:
        print("Arguments could not have been parsed. Internal error is " + e.__str__())
        print(common)
        exit(5)

    # Manual validation of inputs from sharepoint list
    if args.request:
        parse_sharepoint_arguments(args, common)

    # TODO merge checks
    if args.begin >= args.end:
        raise ValueError("Begin date " + str(args.begin) + " can not be after " + str(args.end))
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
