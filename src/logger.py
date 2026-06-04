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

"""Logging setup, secret-redacting filter, and helper utilities."""

import logging
from pathlib import Path
from typing import Optional, Any, cast
from rich.logging import RichHandler

from defines import DATE_FORMAT, LogLevel, get_default_log_path

# ---- extend the logging module with TRACE
TRACE_LEVEL_NUM = 1
logging.addLevelName(TRACE_LEVEL_NUM, "TRACE")
MESSAGE_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


class ExtendedLogger(logging.Logger):
    """Logger subclass that adds a ``trace`` method below DEBUG level."""

    def trace(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
        """Log *message* at the custom TRACE level (below DEBUG).

        Args:
            message: The message to log.
            *args: Positional arguments forwarded to ``_log``.
            **kwargs: Keyword arguments forwarded to ``_log``.
        """
        self._log(TRACE_LEVEL_NUM, message, args, **kwargs)


# Tell the logging system to use your new class
logging.setLoggerClass(ExtendedLogger)


class SecretsFilter(logging.Filter):
    """Logging filter that redacts known secret strings from log records."""

    def __init__(self, secrets: list[str] | None) -> None:
        """Initialise the filter with a list of secret strings to redact.

        Args:
            secrets: Strings to replace with ``*****`` in log messages. Pass ``None`` or
                an empty list to disable redaction.
        """
        super().__init__()
        self.secrets: list[str] = secrets or []

    def filter(self, record: logging.LogRecord) -> bool:
        """Redact secrets from *record* and always allow the record through.

        Args:
            record: The log record to inspect and potentially modify.

        Returns:
            Always ``True`` — every record is allowed, but its message may be modified.
        """
        if not self.secrets:
            return True

        if isinstance(record.msg, str):
            for secret in self.secrets:
                if secret and secret in record.msg:
                    record.msg = record.msg.replace(secret, "*****")

        return True


def setup_logging(
    level: Optional[int | None] = None,
    user_report_file: Optional[str | Path] = None,
    admin_log_file: Optional[str | Path] = None,
    supervisor_log_file: Optional[str | Path] = None,
    secrets: list[str] | None = None,
) -> None:
    """Configure the root logger with a Rich console handler and optional file handlers.

    Args:
        level: Logging level integer. Defaults to the configured default log level.
        user_report_file: Path for the user-facing log file (uses *level*).
        admin_log_file: Path for the admin log file (ERROR and above).
        supervisor_log_file: Path for the supervisor log file (WARNING and above).
        secrets: Secret strings to redact from all log output.
    """
    # Default level is DEBUG
    if level is None:
        level = LogLevel.get_default_log_level().to_logging_level()

    handlers: list[logging.Handler] = []
    secrets_filter = SecretsFilter(secrets)

    # ---- console (Rich)
    console = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=False,
        show_level=True,
        show_path=False,
    )
    common_formatter = logging.Formatter(MESSAGE_FORMAT, DATE_FORMAT)
    console.setLevel(level)
    console.setFormatter(common_formatter)
    console.addFilter(secrets_filter)
    handlers.append(console)

    log_files = [
        (user_report_file, level),
        (admin_log_file, logging.ERROR),
        (supervisor_log_file, logging.WARNING),
    ]

    for log_file_i in log_files:
        if log_file_i[0]:
            path = Path(log_file_i[0])
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(path, encoding="utf-8")
            file_handler.setFormatter(common_formatter)
            file_handler.addFilter(secrets_filter)
            file_handler.setLevel(log_file_i[1])
            handlers.append(file_handler)

    logging.basicConfig(
        level=level,  # root captures everything
        handlers=handlers,
        format=MESSAGE_FORMAT,
        force=True,
    )


def obfuscate_text(text: str | None) -> str:
    """Return ``*****`` for any non-None value, or the string ``"None"`` for None.

    Args:
        text: The value to obfuscate.

    Returns:
        ``"*****"`` when *text* is not ``None``, otherwise ``"None"``.
    """
    if text is None:
        return str(text)
    else:
        return "*****"


def get_logger(name: str) -> ExtendedLogger:
    """Return a logger with trace() method available."""
    return cast(ExtendedLogger, logging.getLogger(name))


def process_log_flags(
    very_verbose: bool, verbose: bool, quiet: bool, very_quiet: bool
) -> tuple[LogLevel | None, bool]:
    """Translate CLI verbosity flags to a LogLevel and a conflict indicator.

    Args:
        very_verbose: If True, select TRACE level.
        verbose: If True, select DEBUG level.
        quiet: If True, select WARNING level.
        very_quiet: If True, select QUIET level.

    Returns:
        A tuple of ``(LogLevel | None, bool)`` where the first element is the
        selected level (or ``None`` if no flag was set) and the second is ``True``
        when more than one flag was supplied simultaneously.
    """
    more_than_one_flag = False
    flag_counter = 0
    for flag in (very_verbose, verbose, quiet, very_quiet):
        if flag:
            flag_counter += 1
    if flag_counter > 1:
        more_than_one_flag = True

    if very_verbose:
        return LogLevel.TRACE, more_than_one_flag
    elif verbose:
        return LogLevel.DEBUG, more_than_one_flag
    elif quiet:
        return LogLevel.WARNING, more_than_one_flag
    elif very_quiet:
        return LogLevel.QUIET, more_than_one_flag
    else:
        return None, more_than_one_flag


def configure_logging_from_settings(
    level: Optional[LogLevel] = None,
    user_report_file: Optional[str | Path] = None,
    admin_log_file: Optional[str | Path] = None,
    supervisor_log_file: Optional[str | Path] = None,
    secrets: Optional[list[str]] = None,
) -> None:
    """Configure logging using domain-level LogLevel values and default paths.

    Resolves ``None`` arguments to their configured defaults before delegating
    to :func:`setup_logging`.

    Args:
        level: Desired log level. Defaults to the configured default.
        user_report_file: Path for the user-facing log. Defaults to the admin log path.
        admin_log_file: Path for the admin log. Defaults to the admin log path.
        supervisor_log_file: Path for the supervisor log. Defaults to the admin log path.
        secrets: Secret strings to redact from all log output.
    """
    if user_report_file is None:
        user_report_file = get_default_log_path()
    if admin_log_file is None:
        admin_log_file = get_default_log_path()
    if supervisor_log_file is None:
        supervisor_log_file = get_default_log_path()

    if level is None:
        level = LogLevel.get_default_log_level()

    setup_logging(
        level=level.to_logging_level(),
        user_report_file=user_report_file,
        admin_log_file=admin_log_file,
        supervisor_log_file=supervisor_log_file,
        secrets=secrets,
    )  # Preventive creation of log for logging the loading of settings
