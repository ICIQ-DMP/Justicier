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
      1. Docker secrets   (/run/secrets/<name>)
      2. Local file       (<project_root>/secrets/<name>)
      3. Environment variable
      4. HashiCorp Vault  (https://{VAULT_ADDR}, policy justicier-runtime)
    """
    sources: list[Callable[[], str]] = [
        lambda: read_file_content(Path("/run/secrets") / secret_name),
        lambda: read_file_content(_PROJECT_ROOT / "secrets" / secret_name),
        lambda: read_env_var(secret_name),
        lambda: read_vault_secret(secret_name),
    ]

    for source in sources:
        try:
            return source()
        except Exception:
            continue

    log.error(f"Could not read {secret_name} from any source")
    sys.exit(1)
