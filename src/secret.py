import sys
from pathlib import Path
from typing import Callable

from filesystem import read_file_content, read_env_var
from logger import get_logger
from vault import read_vault_secret

_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

log = get_logger(__name__)


def read_secret(secret_name: str) -> str:
    """Retrieve a secret from predefined sources in order of priority.

    Sources tried in order:
      1. HashiCorp Vault  (https://10.42.1.2:8200, policy justicier-runtime)
      2. Docker secrets   (/run/secrets/<name>)
      3. Local file       (<project_root>/secrets/<name>)
      4. Environment variable
    """
    sources: list[Callable[[], str]] = [
        lambda: read_vault_secret(secret_name),
        lambda: read_file_content(Path("/run/secrets") / secret_name),
        lambda: read_file_content(_PROJECT_ROOT / "secrets" / secret_name),
        lambda: read_env_var(secret_name),
    ]

    for source in sources:
        try:
            return source()
        except Exception as e:
            print(e)
            continue

    log.error(f"Could not read {secret_name} from any source")
    sys.exit(1)
