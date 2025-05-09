import re


class NAF:
    def __init__(self, raw_naf):
        pattern = r"(\d{2})([/\-]?)(\d{8})([/\-]?)(\d{2})"
        match = re.fullmatch(pattern, raw_naf)
        if not match:
            raise ValueError(f"Invalid NAF format: {raw_naf} NAF must be in NAF format. Example: 43/12345678-20")

        self.province_code = match.group(1)
        self.sep1 = match.group(2)
        self.middle_number = match.group(3)
        self.sep2 = match.group(4)
        self.last_number = match.group(5)

    def __str__(self):
        return f"{self.province_code}{self.middle_number}{self.last_number}"

    def __eq__(self, other):
        if not isinstance(other, NAF):
            return False
        return (
            self.province_code == other.province_code and
            self.middle_number == other.middle_number and
            self.last_number == other.last_number
        )

    def __hash__(self):
        return hash(self.province_code + self.middle_number + self.last_number)

    def slash_dash_str(self):
        return f"{self.province_code}/{self.middle_number}-{self.last_number}"



def is_naf_correct(naf):
    """Validate that NAF has NAF format"""
    try:
        NAF(naf)  # Parse using constructor
    except ValueError:
        return False
    return True


def validate_naf(value):
    if not is_naf_correct(value):
        raise ValueError("Naf " + value + " is not valid.")
    else:
        return NAF(value)
