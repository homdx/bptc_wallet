import logging
import sys
import os

from .algorithms import *


stdout_logger = None
file_logger = None
logger = None


# Logging
def init_logger(output_dir):
    global stdout_logger, file_logger, logger

    stdout_logger = logging.StreamHandler(sys.stdout)
    stdout_logger.setFormatter(logging.Formatter('%(message)s'))
    stdout_logger.setLevel(logging.INFO)

    logfile = os.path.join(output_dir, 'log.txt')
    file_logger = logging.FileHandler(logfile)
    file_logger.setLevel(logging.INFO)
    file_logger.setFormatter(logging.Formatter('%(message)s'))

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(stdout_logger)
    logger.addHandler(file_logger)
