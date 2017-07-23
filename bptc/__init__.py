import logging
import sys

# PARAMETER
C = 6  # How often a coin round occurs, e.g. 6 for every sixth round
push_waiting_time_mu, push_waiting_time_sigma = 1, 0.02  # mean and standard deviation of push rate
new_member_stake = 0  # the stake a new member gets
new_member_account_balance = 10  # the initial balance of a new member

# listening interface information
ip = None
port = None

# Logging
stdout_logger = None
file_logger = None
logger = None


def init_logger(logfile, verbose=False):
    """Initialize the logger."""
    global stdout_logger, file_logger, logger
    stdout_logger_lvl = logging.DEBUG if verbose else logging.INFO

    stdout_logger = logging.StreamHandler(sys.stdout)
    stdout_logger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    stdout_logger.setLevel(stdout_logger_lvl)

    file_logger = logging.FileHandler(logfile)
    file_logger.setLevel(logging.DEBUG)
    file_logger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_logger)
    logger.addHandler(file_logger)


# Toggle output level for stdout logger (stdout_logger_lvl or logging.WARN)
def toggle_stdout_log_level():
    """Toggle the log level."""
    if stdout_logger.level == logging.INFO:
        stdout_logger.setLevel(logging.DEBUG)
    else:
        stdout_logger.setLevel(logging.INFO)


def get_stdout_levelname():
    """Return the log levelname."""
    return logging._levelToName[stdout_logger.level]
