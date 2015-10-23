import json
import os
import sys

json_path = sys.argv[1]

with open(json_path, 'r') as f:
    tag = json.load(f)['Tags'][0]

print tag['Value']
