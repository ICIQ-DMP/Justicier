import pytest

from defines import DocType, from_string


class TestFromString:
    @pytest.mark.parametrize(
        "alias,expected",
        [
            ("salary", DocType.SALARY),
            ("salaries", DocType.SALARY),
            ("SALARY", DocType.SALARY),
            ("payslip", DocType.SALARY),
            ("contract", DocType.CONTRACT),
            ("CONTRACT", DocType.CONTRACT),
            ("RLC", DocType.RLC),
            ("rlc", DocType.RLC),
            ("RNT", DocType.RNT),
            ("rnt", DocType.RNT),
            ("proof", DocType.PROOFS),
            ("proofs", DocType.PROOFS),
            ("bankproof", DocType.PROOFS),
        ],
    )
    def test_known_aliases(self, alias, expected):
        assert from_string(alias) == expected

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown document type"):
            from_string("unknown_type")

    def test_strips_whitespace(self):
        assert from_string("  salary  ") == DocType.SALARY


class TestDocType:
    def test_enum_values(self):
        assert DocType.SALARY.value == "salary"
        assert DocType.CONTRACT.value == "contract"
        assert DocType.RLC.value == "RLC"
        assert DocType.RNT.value == "RNT"
        assert DocType.PROOFS.value == "proofs"
        assert DocType.SALARIES_AND_PROOFS.value == "salaries with proofs"
