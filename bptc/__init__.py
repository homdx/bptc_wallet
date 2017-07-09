import logging
import sys

stdout_logger = None
file_logger = None
logger = None


# Logging
def init_logger(logfile, be_quiet=False):
    global stdout_logger, file_logger, logger

    stdout_logger = logging.StreamHandler(sys.stdout)
    stdout_logger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    stdout_logger.setLevel(logging.INFO if be_quiet else logging.DEBUG)

    file_logger = logging.FileHandler(logfile)
    file_logger.setLevel(logging.DEBUG)
    file_logger.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_logger)
    logger.addHandler(file_logger)
