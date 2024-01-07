import os
import json
from functools import lru_cache
from typing import Dict

from referencing import Resource
from referencing.jsonschema import DRAFT202012

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


def get_standard_schema(schema: str) -> dict:
    schema_fpath = os.path.join(_SCHEMAS_DIR, "standard", f"{schema}.json")
    return _get_schema(schema_fpath)


def get_machine_schema(schema: str) -> dict:
    schema_fpath = os.path.join(_SCHEMAS_DIR, "machine", f"{schema}.json")
    return _get_schema(schema_fpath)


def load_standard_schemas() -> Dict[str, Resource]:
    schemas = {}
    for schema in os.listdir(os.path.join(_SCHEMAS_DIR, "standard")):
        if schema.endswith(".json"):
            schema_name = schema[:-5]
            schemas[schema_name] = DRAFT202012.create_resource(get_standard_schema(schema_name))
    return schemas
