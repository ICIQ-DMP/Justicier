from custom_except import ArgumentNafInvalid


class Name:
    def __init__(self, name, surname):
        self.name = name
        self.surname = surname

    def __str__(self):
        return f"{self.name} {self.surname}"

    def __eq__(self, other):
        if not isinstance(other, Name):
            return False
        return (
            self.name == other.name and
            self.surname == other.surname
        )

    def __hash__(self):
        return hash(self.name + self.surname)


def parse_name_a3(value):
    # Coupled with NAF_DNI.xlsx format
    parts = value.split(",")
    name = parts[1].strip(" ")
    if " " in name:
        name = name.split(" ")[0]
    surname = parts[0]
    if " " in surname:
        surname = surname.split(" ")[0]
    try:
        return Name(name, surname)
    except ValueError as e:
        raise ArgumentNafInvalid("Name is not valid" + e.__str__())  # TODO: change exceptions


def parse_name_sharepoint(value: str):
    print("parse name says: " + str(value))
    input()
    value = value.replace("à", "a")
    value = value.replace("â", "a")
    value = value.replace("á", "a")
    value = value.replace("è", "e")
    value = value.replace("ê", "e")
    value = value.replace("é", "e")
    value = value.replace("ì", "i")
    value = value.replace("î", "i")
    value = value.replace("í", "i")
    value = value.replace("ò", "o")
    value = value.replace("ô", "o")
    value = value.replace("ó", "o")
    value = value.replace("ù", "u")
    value = value.replace("û", "u")
    value = value.replace("ú", "u")
    value = value.upper()
    name = value.split(" ")[0]
    surname = " ".join(value.split(" ")[1:])

    # Coupled with Sharepoint name format
    try:
        return Name(name, surname)
    except ValueError as e:
        raise ArgumentNafInvalid("Name is not valid" + e.__str__())  # TODO: change exceptions
