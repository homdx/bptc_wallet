from random import random
from collections import deque

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
