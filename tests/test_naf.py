import pytest

from NAF import NAF, is_naf_format_correct, parse_naf
from custom_except import ArgumentNafInvalid


class TestNAFParsing:
    def test_plain_digits(self):
        naf = NAF("431234567820")
        assert naf.province_code == "43"
        assert naf.middle_number == "12345678"
        assert naf.last_number == "20"

    def test_slash_dash_format(self):
        naf = NAF("43/12345678-20")
        assert naf.province_code == "43"
        assert naf.middle_number == "12345678"
        assert naf.last_number == "20"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            NAF("not-a-naf")

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            NAF("4312345678")  # missing last two digits


class TestNAFEquality:
    def test_equal_regardless_of_separator(self):
        assert NAF("43/12345678-20") == NAF("431234567820")

    def test_different_nafs_not_equal(self):
        assert NAF("431234567820") != NAF("431234567821")

    def test_hash_equal_for_same_naf(self):
        assert hash(NAF("431234567820")) == hash(NAF("43/12345678-20"))


class TestNAFFormatting:
    def test_str_strips_separators(self):
        assert str(NAF("43/12345678-20")) == "431234567820"

    def test_slash_dash_str(self):
        assert NAF("431234567820").slash_dash_str() == "43/12345678-20"


class TestNAFHelpers:
    def test_is_naf_format_correct_valid(self):
        assert is_naf_format_correct("431234567820") is True

    def test_is_naf_format_correct_invalid(self):
        assert is_naf_format_correct("bad") is False

    def test_parse_naf_raises_argument_naf_invalid(self):
        with pytest.raises(ArgumentNafInvalid):
            parse_naf("not-a-naf")
