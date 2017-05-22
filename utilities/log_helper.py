import logging
import sys

stdout_logger = logging.StreamHandler(sys.stdout)
stdout_logger.setFormatter(logging.Formatter('%(message)s'))
stdout_logger.setLevel(logging.INFO)

file_logger = logging.FileHandler('log.txt')
file_logger.setLevel(logging.INFO)
file_logger.setFormatter(logging.Formatter('%(message)s'))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(stdout_logger)
logger.addHandler(file_logger)