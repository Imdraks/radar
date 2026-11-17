"""Export declared HTTP contracts; security declarations do not replace access tests.
Run: PYTHONPATH=backend python scripts/api_inventory.py OUTPUT.csv
"""
import csv
import sys
from app.main import app

with open(sys.argv[1], 'w', newline='') as output:
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(['method','path','bearer_declared','operation_id'])
    for path, operations in sorted(app.openapi()['paths'].items()):
        for method, operation in sorted(operations.items()):
            if method in {'get','post','put','patch','delete','head','options'}:
                writer.writerow([method.upper(),path,bool(operation.get('security')),operation['operationId']])
