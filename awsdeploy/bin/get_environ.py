import json
import os
import sys

json_path = sys.argv[1]

with open(json_path, 'r') as f:
    tags = json.load(f)['Tags'][0]

print tags[0]['Value']
