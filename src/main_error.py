import argparse

from arguments import parse_id
from sharepoint import update_list_item_field


def main():
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-r", "--request", "--id", type=parse_id, required=True,
                        help='ID of the justification request in Microsoft List of Peticions Justificacions.')
    args = parser.parse_args()
    update_list_item_field(args.request, {"Estatworkflow": "Error"})


if __name__ == "__main__":
    main()