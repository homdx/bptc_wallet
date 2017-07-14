:: start .\tools\scripts\registry
start .\tools\scripts\client 8100 "-sp -bp localhost:8102"
start .\tools\scripts\client 8102 "-sp -bp localhost:8100"
start .\tools\scripts\client 8104 "-sp -bp localhost:8100"
start .\tools\scripts\client 8106 "-sp -bp localhost:8100"
:: start .\tools\scripts\client 8108
:: start .\tools\scripts\client 8110
:: start .\tools\scripts\client 8112
:: start .\tools\scripts\client 8114
:: start .\tools\scripts\client 8116
:: start .\tools\scripts\client 8118
:: start .\tools\scripts\viz
