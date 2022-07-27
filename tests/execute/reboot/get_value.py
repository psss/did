#!/usr/bin/python3
import click
from ruamel.yaml import YAML


@click.command()
@click.argument("KEY")
@click.argument("YAML_FILE")
def main(key, yaml_file):
    """
    Find 'key' somewhere in the yaml_file and print its value

    If it returns list then prints first item
    """

    with open(yaml_file) as f:
        data = YAML(typ="safe").load(f)

    value = find_value(data, key)
    if not isinstance(value, (str, int)):
        if value:
            print(value[0])
    else:
        print(value)


def find_value(data, key):
    if not isinstance(data, dict):
        raise ValueError()
    try:
        return data[key]
    except KeyError:
        for value in data.values():
            try:
                return find_value(value, key)
            except ValueError:
                pass
    return


if __name__ == "__main__":
    main()
