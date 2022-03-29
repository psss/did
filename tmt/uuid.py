from typing import Any, Optional
from uuid import uuid4

import fmf

from .utils import log

ID_FMF_ITEM = "id"


class IDError(Exception):
    pass


class IDLeafError(IDError):
    pass


def locate_key(node: fmf.Tree, key: str) -> Optional[fmf.Tree]:
    """
    Return fmf location of key attribute inside tree or None if not defined anywhere
    """
    identifier = node.data.get(key)
    if identifier is None:
        return None
    current_node = node
    while True:
        parent = current_node.parent
        if parent:
            if current_node.get(key) == parent.get(key):
                current_node = parent
                continue
            else:
                return current_node
        else:
            if current_node.get(key):
                return current_node
            else:
                break
    return None


def is_key_defined_in_leaf(node: fmf.Tree, key: str) -> bool:
    """
    Is key defined inside this node
    """
    node_location = locate_key(node, key=key)
    if not node_location:
        return False
    location = node_location.name
    if node and node.name == location:
        return True
    return False


def get_id(node: fmf.Tree, is_leaf: bool = True) -> Any:
    """
    Get identifier if defined.
    """
    if is_leaf and not is_key_defined_in_leaf(node, ID_FMF_ITEM):
        raise IDLeafError(
            f"{ID_FMF_ITEM} not defined in leaf in {node.name}")
    return node.data[ID_FMF_ITEM]


def add_uuid_if_not_defined(node: fmf.Tree, dry: bool) -> Optional[str]:
    """
    Add UUID into node if not defined
    """
    if is_key_defined_in_leaf(node, key=ID_FMF_ITEM):
        log.debug(
            f"UUID already defined for {node.name} = {node.data[ID_FMF_ITEM]}")
        return None
    else:
        gen_uuid = str(uuid4())
        if not dry:
            with node as data:
                data[ID_FMF_ITEM] = gen_uuid
                log.debug(f"Generating UUID for {node.name} = {gen_uuid}")
        return gen_uuid


def add_uuid_cmd(node: fmf.Tree, item_str: str, dry: bool) -> None:
    """
    command line interfacing with output to terminal, when doing adding of UUIDs to nodes
    """
    generated = add_uuid_if_not_defined(node, dry=dry)
    if generated:
        print(f"Add new ID to {item_str} node {node.name} = {generated}")
    else:
        print(
            f"{node.name} {item_str} has ID already defined {node.data[ID_FMF_ITEM]}")


def lint_key(node_list: list[fmf.Tree],
             key: str = ID_FMF_ITEM) -> list[fmf.Tree]:
    """
    Check if all items contains key, return list of items missing key
    """
    missing_uuid_nodes = []
    for node in node_list:
        if is_key_defined_in_leaf(node, key=key):
            log.debug(f"{node} has defined UUID item")
        else:
            missing_uuid_nodes.append(node)
            log.error(
                f"{node} does not contain {key}, add key {key}")
    return missing_uuid_nodes
