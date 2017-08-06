git checkout -- demo_setup
start .\tools\scripts\stakeholder 8000 "-o demo_setup\stakeholders\1\data -bp localhost:8002"
start .\tools\scripts\stakeholder 8002 "-o demo_setup\stakeholders\2\data -bp localhost:8004"
start .\tools\scripts\stakeholder 8004 "-o demo_setup\stakeholders\3\data -bp localhost:8006"
start .\tools\scripts\stakeholder 8006 "-o demo_setup\stakeholders\4\data -bp localhost:8000"
