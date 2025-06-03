import logging
import sys

# ANSI escape codes for colors
COLOR_CODES = {
    'DEBUG': '\033[90m',  # Gray
    'INFO': '\033[92m',  # Green
    'WARNING': '\033[93m',  # Yellow
    'ERROR': '\033[91m',  # Red
    'CRITICAL': '\033[1;91m'  # Bold Red
}
RESET_CODE = '\033[0m'


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = COLOR_CODES.get(record.levelname, '')
        message = super().format(record)
        return f"{color}{message}{RESET_CODE}"


def unformatted_logger(logger):
    for h in logger.handlers:
        h.setFormatter(None)
    return logger


def get_logger_instance():
    return base_logger


def build_process_logger(logger_instance, process_name):
    return logging.LoggerAdapter(logger_instance, {'process_name': process_name})


def get_logger(user_report_file, admin_log_file, supervisor_log_file, name="justicier", debug_mode=False):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # Prevent re-adding handlers

    # Formatters
    plain_formatter = logging.Formatter('%(asctime)s - %(process_name)s - %(levelname)s - %(message)s')
    color_formatter = ColorFormatter('%(asctime)s - %(process_name)s - %(levelname)s - %(message)s')

    # User log (INFO+)
    user_handler = logging.FileHandler(user_report_file)
    user_handler.setLevel(logging.INFO)
    user_handler.setFormatter(plain_formatter)

    # Admin/system log (DEBUG+ if debug_mode, else ERROR+)
    admin_handler = logging.FileHandler(admin_log_file)
    admin_handler.setLevel(logging.DEBUG if debug_mode else logging.ERROR)
    admin_handler.setFormatter(plain_formatter)

    # Console log (DEBUG+ if debug_mode, else WARNING+), with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.WARNING)
    console_handler.setFormatter(color_formatter)

    # Supervisor log
    supervisor_handler = logging.FileHandler(supervisor_log_file)
    supervisor_handler.setLevel(logging.INFO)
    supervisor_handler.setFormatter(color_formatter)

    for handler in [user_handler, admin_handler, console_handler, supervisor_handler]:
        logger.addHandler(handler)

    return logger


def set_logger(logger_instance):
    global base_logger
    base_logger = logger_instance


base_logger = None  # will be set later by main
