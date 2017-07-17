python3 -m cProfile -o db_analyzer.cprof db_analyzer.py
pyprof2calltree -k -i db_analyzer.cprof