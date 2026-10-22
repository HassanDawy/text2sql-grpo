import json

with open('../../dev/dev_20240627/dev.json') as f:
    data = json.load(f)

print(len(data))
print(json.dumps(data[0], indent=2))