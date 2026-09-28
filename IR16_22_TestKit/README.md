# KnowGap AI ? IR-16 to IR-22 Test Kit

Student 4: Information Retrieval and Security Assessment.

This package contains seven additional case specifications,
synthetic fixture descriptions and an evidence-preparation tool.

The case specifications are new. They are not recorded test results.

## Installation

Extract IR16_22_TestKit.zip into your IRWA-Project folder.

## Start an evidence record

From the IRWA-Project folder:

    .\.venv\Scripts\python.exe .\IR16_22_TestKit\start_case.py --case IR-16

Replace IR-16 with any case through IR-22.

The starter records original source hashes and creates a separate
audit/evidence/IR-XX/run-TIMESTAMP folder.

IMPORTANT: start_case.py prepares evidence only. It does NOT execute
the HTTP tests, insert fixtures, modify the application or determine
PASS/FAIL. Execute each documented scenario only after checking its
preconditions and adapting it to your exact current project code.

Use isolated synthetic databases and accounts. Never test real user
records, public infrastructure or unrestricted request loads.
