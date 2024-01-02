import os
import json
from functools import lru_cache

import cpk

_SCHEMAS_DIR = os.path.join(os.path.dirname(cpk.__file__), 'schemas')


@lru_cache
def _get_schema(schema_fpath: str) -> dict:
    if not os.path.isfile(schema_fpath):
        raise FileNotFoundError(schema_fpath)
    with open(schema_fpath, 'r') as fin:
        return json.load(fin)


def have_schemas_for_layer(layer: str) -> bool:
    schemas_dpath = os.path.join(_SCHEMAS_DIR, "layers", f"{layer}.yaml")
    return os.path.isdir(schemas_dpath)


def get_layer_schema(layer: str, version: str) -> dict:
    schema_fpath = os.path.join(_SCHEMAS_DIR, "layers", f"{layer}.yaml", f"{version}.json")
    return _get_schema(schema_fpath)


def get_machine_schema(schema: str) -> dict:
    schema_fpath = os.path.join(_SCHEMAS_DIR, "machine", f"{schema}.json")
    return _get_schema(schema_fpath)
