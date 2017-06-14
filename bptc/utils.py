# coding=utf-8
# -*- coding: utf-8 -*-

import logging
import sys
import os
from random import random
from collections import deque

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


# Algorithms
def bfs(s, succ):
    s = tuple(s)
    seen = set(s)
    q = deque(s)
    while q:
        u = q.popleft()
        yield u
        for v in succ(u):
            if v not in seen:
                seen.add(v)
                q.append(v)


def dfs(s, succ):
    seen = set()
    q = [s]
    while q:
        u = q.pop()
        yield u
        seen.add(u)
        for v in succ(u):
            if v not in seen:
                q.append(v)


def randrange(n):
    a = (n.bit_length() + 7) // 8  # number of bytes to store n
    b = 8 * a - n.bit_length()     # number of shifts to have good bit number
    r = int.from_bytes(random(a), byteorder='big') >> b
    while r >= n:
        r = int.from_bytes(random(a), byteorder='big') >> b
    return r
