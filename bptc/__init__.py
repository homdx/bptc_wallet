import logging
import os
import sys

stdout_logger = None
file_logger = None
logger = None


# Logging
def init_logger(output_dir, be_quiet=False):
    global stdout_logger, file_logger, logger

    stdout_logger = logging.StreamHandler(sys.stdout)
    stdout_logger.setFormatter(logging.Formatter('%(message)s'))
    stdout_logger.setLevel(logging.INFO if be_quiet else logging.DEBUG)

    logfile = os.path.join(output_dir, 'log.txt')
    file_logger = logging.FileHandler(logfile)
    file_logger.setLevel(logging.DEBUG)
    file_logger.setFormatter(logging.Formatter('%(message)s'))

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_logger)
    logger.addHandler(file_logger)
