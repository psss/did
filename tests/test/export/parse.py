#!/usr/bin/python3
""" A simple script to parse the output of 'tmt test export .' """

import sys

import ruamel.yaml


def verify(obj, obj_id, field, exp):
    got = obj[field]
    sys.stdout.write(f">>> Verify {obj_id}'s field '{field}' ......\n"
                     f"...\texp: {exp}\n"
                     f"...\tgot: {got}\n"
                     f"...\tres: ")
    assert got == exp
    sys.stdout.write("PASSED\n\n")


def main(argc, argv):
    yaml = ruamel.yaml.YAML()
    tests = yaml.load(sys.stdin)

    test01 = tests[0]
    verify(test01, 'test01', 'name', '/tests/enabled/default')
    verify(test01, 'test01', 'summary', 'This test is enabled by default')
    verify(test01, 'test01', 'description', None)
    verify(test01, 'test01', 'contact', [])
    verify(test01, 'test01', 'component', [])
    verify(test01, 'test01', 'test', 'true')
    verify(test01, 'test01', 'path', '/')
    verify(test01, 'test01', 'framework', 'shell')
    verify(test01, 'test01', 'manual', False)
    verify(test01, 'test01', 'require', [])
    verify(test01, 'test01', 'recommend', [])
    verify(test01, 'test01', 'environment', {})
    verify(test01, 'test01', 'duration', '5m')
    verify(test01, 'test01', 'enabled', True)
    verify(test01, 'test01', 'order', 50)
    verify(test01, 'test01', 'result', 'respect')
    verify(test01, 'test01', 'tag', [])
    verify(test01, 'test01', 'tier', None)
    verify(test01, 'test01', 'link', [])

    test02 = tests[1]
    verify(test02, 'test02', 'name', '/tests/enabled/disabled')
    verify(test02, 'test02', 'summary', 'This test is disabled')
    verify(test02, 'test02', 'description', None)
    verify(test02, 'test02', 'contact', [])
    verify(test02, 'test02', 'component', [])
    verify(test02, 'test02', 'test', 'true')
    verify(test02, 'test02', 'path', '/')
    verify(test02, 'test02', 'framework', 'shell')
    verify(test02, 'test02', 'manual', False)
    verify(test02, 'test02', 'require', [])
    verify(test02, 'test02', 'recommend', [])
    verify(test02, 'test02', 'environment', {})
    verify(test02, 'test02', 'duration', '5m')
    verify(test02, 'test02', 'enabled', False)
    verify(test02, 'test02', 'order', 50)
    verify(test02, 'test02', 'result', 'respect')
    verify(test02, 'test02', 'tag', [])
    verify(test02, 'test02', 'tier', None)
    verify(test02, 'test02', 'link', [])
    return 0


if __name__ == '__main__':
    sys.exit(main(len(sys.argv), sys.argv))
