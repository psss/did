import yaml

with open('tests.fmf') as tests:
    print(yaml.safe_load(tests)['summary'])
