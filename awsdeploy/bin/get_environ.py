import json
import os
import sys

json_path = sys.arvg[1]

with open(json_path, 'r') as f:
    user = json.load(f)['Tags'][0]

print tags[0]['Value']
