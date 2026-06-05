# justicier - Automated employee justifications
# Copyright (C) 2026  Aleix Mariné Tena (AleixMT), Carles de la Cuadra
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""Secret resolution from Docker secrets, local files, environment, and Vault."""

from pathlib import Path
from typing import Callable

from custom_except import SecretCouldNotBeReadFromAnySourceError
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
    raise SecretCouldNotBeReadFromAnySourceError
