import argparse
import pytest

from arguments import get_compact_init


@pytest.fixture
def empty_args():
    """Minimal argparse Namespace with all local args unset — simulates a bare parse."""
    args = argparse.Namespace(
        request=None,
        naf=None,
        name=None,
        target_email=None,
        dni=None,
        begin=None,
        end=None,
        author=None,
        merge_result=get_compact_init(),
        merge_salary=False,
        merge_rnt_rlc=False,
        location="sharepoint",
        input_location=None,
    )
    return args
